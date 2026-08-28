import uuid
from datetime import datetime
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, validate_password_strength, 
    create_access_token, create_refresh_token, revoke_token, is_token_revoked,
    check_login_rate_limit, record_failed_login, reset_failed_logins,
    get_current_user, require_roles
)
from app.models.models import User, Patient, UserRole
from app.schemas.schemas import UserCreate, UserLogin, Token, UserOut, RefreshTokenRequest, LogoutResponse
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting trusted reverse proxy headers."""
    if request:
        x_forwarded = request.headers.get("X-Forwarded-For")
        if x_forwarded:
            ip = x_forwarded.split(",")[0].strip()
            if ip:
                return ip
        x_real = request.headers.get("X-Real-IP")
        if x_real:
            return x_real.strip()
        if request.client and request.client.host:
            return request.client.host
    return "127.0.0.1"


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Validate password strength
    validate_password_strength(user_data.password)

    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Create user
    user = User(
        email=user_data.email.lower(),
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role if user_data.role in [UserRole.PATIENT] else UserRole.PATIENT,  # Public register is always PATIENT
        phone=user_data.phone,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create associated Patient profile
    patient = Patient(user_id=user.id)
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # Generate token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)

    # Record audit log
    client_ip = request.client.host if request.client else None
    record_audit_log(
        db=db,
        action="USER_REGISTER",
        resource_type="User",
        resource_id=str(user.id),
        user_id=user.id,
        details={"email": user.email, "role": user.role.value},
        ip_address=client_ip
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        patient_id=patient.id
    )

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = get_client_ip(request)
    check_login_rate_limit(client_ip, login_data.email)

    user = db.query(User).filter(User.email == login_data.email.lower()).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        record_failed_login(client_ip, login_data.email)
        record_audit_log(
            db=db,
            action="USER_LOGIN_FAILED",
            resource_type="User",
            resource_id=str(user.id) if user else "UNKNOWN",
            user_id=user.id if user else None,
            details={"attempted_email": login_data.email, "reason": "invalid_credentials"},
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled."
        )

    reset_failed_logins(client_ip, login_data.email)

    patient_id = user.patient_profile.id if user.patient_profile else None
    doctor_id = user.doctor_profile.id if user.doctor_profile else None

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set secure HttpOnly cookies for browser clients
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    csrf_token = uuid.uuid4().hex
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax"
    )

    record_audit_log(
        db=db,
        action="USER_LOGIN",
        resource_type="User",
        resource_id=str(user.id),
        user_id=user.id,
        details={"email": user.email, "role": user.role.value},
        ip_address=client_ip
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        patient_id=patient_id,
        doctor_id=doctor_id
    )

@router.post("/refresh", response_model=Token)
def refresh_session(refresh_req: RefreshTokenRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or revoked refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_req.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type: str = payload.get("token_type")
        if user_id is None or token_type != "refresh":
            raise credentials_exception
        if jti and is_token_revoked(db, jti):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive or deleted.")

    # Refresh token rotation: revoke old refresh token
    if jti:
        revoke_token(db, jti, user.id)

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    patient_id = user.patient_profile.id if user.patient_profile else None
    doctor_id = user.doctor_profile.id if user.doctor_profile else None

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        patient_id=patient_id,
        doctor_id=doctor_id
    )

@router.post("/logout", response_model=LogoutResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif request.cookies.get("access_token"):
        token = request.cookies.get("access_token")

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            jti = payload.get("jti")
            if jti:
                revoke_token(db, jti, current_user.id)
        except JWTError:
            pass

    response.delete_cookie(key="access_token")
    response.delete_cookie(key="csrf_token")

    record_audit_log(
        db=db,
        action="USER_LOGOUT",
        resource_type="User",
        resource_id=str(current_user.id),
        user_id=current_user.id,
        details={"email": current_user.email},
        ip_address=request.client.host if request.client else None
    )

    return LogoutResponse()

@router.get("/me", response_model=UserOut)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    patient_id = current_user.patient_profile.id if current_user.patient_profile else None
    doctor_id = current_user.doctor_profile.id if current_user.doctor_profile else None
    
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        phone=current_user.phone,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        patient_id=patient_id,
        doctor_id=doctor_id
    )

@router.get("/users", response_model=list[UserOut])
def list_users(
    role: UserRole | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if q:
        search = f"%{q}%"
        query = query.filter((User.full_name.ilike(search)) | (User.email.ilike(search)))
    users = query.order_by(User.id.desc()).all()
    results = []
    for u in users:
        results.append(UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            phone=u.phone,
            is_active=u.is_active,
            created_at=u.created_at,
            patient_id=u.patient_profile.id if u.patient_profile else None,
            doctor_id=u.doctor_profile.id if u.doctor_profile else None
        ))
    return results

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    validate_password_strength(user_data.password)
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    user = User(
        email=user_data.email.lower(),
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        phone=user_data.phone,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if user.role == UserRole.PATIENT:
        p = Patient(user_id=user.id)
        db.add(p)
        db.commit()

    record_audit_log(
        db=db,
        action="ADMIN_CREATE_USER",
        resource_type="User",
        resource_id=str(user.id),
        user_id=current_admin.id,
        details={"created_email": user.email, "role": user.role.value},
        ip_address=request.client.host if request.client else None
    )

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        is_active=user.is_active,
        created_at=user.created_at,
        patient_id=user.patient_profile.id if user.patient_profile else None,
        doctor_id=user.doctor_profile.id if user.doctor_profile else None
    )

@router.patch("/users/{user_id}/status", response_model=UserOut)
def toggle_user_status(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own admin account")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)

    record_audit_log(
        db=db,
        action="TOGGLE_USER_STATUS",
        resource_type="User",
        resource_id=str(user.id),
        user_id=current_admin.id,
        details={"email": user.email, "new_active_status": user.is_active},
        ip_address=request.client.host if request.client else None
    )

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone,
        is_active=user.is_active,
        created_at=user.created_at,
        patient_id=user.patient_profile.id if user.patient_profile else None,
        doctor_id=user.doctor_profile.id if user.doctor_profile else None
    )

