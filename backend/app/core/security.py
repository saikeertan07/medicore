import os
import re
import uuid
import time
import logging
import bcrypt
from datetime import datetime, timedelta
from app.core.datetime_utils import utc_now
from typing import Optional, List, Dict, Tuple
from collections import defaultdict
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User, UserRole, RevokedToken

logger = logging.getLogger("medicore.security")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

# Rate Limiter & Brute-Force Defense
MAX_LOGIN_ATTEMPTS = 5
MAX_IP_LOGIN_ATTEMPTS = 25
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes
MAX_PASSWORD_BYTES = 72


class LoginRateLimiter:
    """
    Production rate-limiter supporting distributed Redis backends with bounded in-memory fallback.
    Prevents both brute-force attacks and denial-of-service account lockouts.
    """
    def __init__(self):
        self._memory_attempts: Dict[str, List[float]] = defaultdict(list)
        self._max_entries = 10000
        self._redis_client = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                self._redis_client = redis.Redis.from_url(redis_url, socket_timeout=1.0)
                self._redis_client.ping()
                logger.info("Distributed Redis rate-limiting backend connected.")
            except Exception as e:
                logger.warning(f"Redis connection failed ({e}). Using bounded in-memory rate limiter.")
                self._redis_client = None

    def check_rate_limit(self, ip: str, email: str) -> None:
        email_clean = email.lower().strip()
        key_composite = f"login_attempt:{ip}:{email_clean}"
        key_ip = f"login_ip:{ip}"
        now = time.time()

        if self._redis_client:
            try:
                attempts_comp = int(self._redis_client.get(key_composite) or 0)
                attempts_ip = int(self._redis_client.get(key_ip) or 0)
                if attempts_comp >= MAX_LOGIN_ATTEMPTS or attempts_ip >= MAX_IP_LOGIN_ATTEMPTS:
                    logger.warning(f"Security Alert: Rate limit exceeded for IP={ip}, account={email_clean}")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many failed login attempts. Account access throttled for security. Please try again later."
                    )
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.debug(f"Redis rate check error ({e}), falling back to in-memory.")

        self._cleanup_expired(now)
        attempts = [t for t in self._memory_attempts[key_composite] if now - t < LOCKOUT_DURATION_SECONDS]
        self._memory_attempts[key_composite] = attempts

        ip_attempts = [t for t in self._memory_attempts[key_ip] if now - t < LOCKOUT_DURATION_SECONDS]
        self._memory_attempts[key_ip] = ip_attempts

        if len(attempts) >= MAX_LOGIN_ATTEMPTS or len(ip_attempts) >= MAX_IP_LOGIN_ATTEMPTS:
            remaining_secs = int(LOCKOUT_DURATION_SECONDS - (now - attempts[0])) if attempts else LOCKOUT_DURATION_SECONDS
            logger.warning(f"Security Alert: Rate limit triggered for IP={ip}, account={email_clean}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Account access throttled for security. Please try again in {remaining_secs} seconds."
            )

    def record_failure(self, ip: str, email: str) -> None:
        email_clean = email.lower().strip()
        key_composite = f"login_attempt:{ip}:{email_clean}"
        key_ip = f"login_ip:{ip}"

        if self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.incr(key_composite)
                pipe.expire(key_composite, LOCKOUT_DURATION_SECONDS)
                pipe.incr(key_ip)
                pipe.expire(key_ip, LOCKOUT_DURATION_SECONDS)
                pipe.execute()
                return
            except Exception as e:
                logger.debug(f"Redis record failure error ({e}), logging to in-memory.")

        self._memory_attempts[key_composite].append(time.time())
        self._memory_attempts[key_ip].append(time.time())

    def reset_attempts(self, ip: str, email: str) -> None:
        email_clean = email.lower().strip()
        key_composite = f"login_attempt:{ip}:{email_clean}"

        if self._redis_client:
            try:
                self._redis_client.delete(key_composite)
                return
            except Exception as e:
                logger.debug(f"Redis reset error: {e}")

        self._memory_attempts.pop(key_composite, None)

    def _cleanup_expired(self, now: float) -> None:
        if len(self._memory_attempts) > self._max_entries:
            keys_to_delete = [
                k for k, timestamps in self._memory_attempts.items()
                if not timestamps or now - timestamps[-1] >= LOCKOUT_DURATION_SECONDS
            ]
            for k in keys_to_delete:
                self._memory_attempts.pop(k, None)


login_rate_limiter = LoginRateLimiter()


def check_login_rate_limit(ip: str, email: str) -> None:
    login_rate_limiter.check_rate_limit(ip=ip, email=email)


def record_failed_login(ip: str, email: str) -> None:
    login_rate_limiter.record_failure(ip=ip, email=email)


def reset_failed_logins(ip: str, email: str) -> None:
    login_rate_limiter.reset_attempts(ip=ip, email=email)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        encoded = plain_password.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            return False
        return bcrypt.checkpw(
            encoded, 
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must not exceed {MAX_PASSWORD_BYTES} bytes (UTF-8 encoded). Received {len(pwd_bytes)} bytes.")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def validate_password_strength(password: str) -> None:
    encoded = password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must not exceed {MAX_PASSWORD_BYTES} bytes (UTF-8 encoded). Received {len(encoded)} bytes."
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter."
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter."
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number."
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = utc_now()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "token_type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = utc_now()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=7)  # 7 days refresh validity
    
    to_encode["jti"] = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "token_type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def is_token_revoked(db: Session, jti: str) -> bool:
    if not jti:
        return False
    revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    return revoked is not None


def revoke_token(db: Session, jti: str, user_id: int, expires_at: Optional[datetime] = None) -> None:
    if not jti:
        return
    existing = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if not existing:
        revoked = RevokedToken(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at or (utc_now() + timedelta(days=7))
        )
        db.add(revoked)
        db.commit()


def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = bearer_token
    # If not in Authorization header, check secure HttpOnly cookie
    if not token and request.cookies.get("access_token"):
        token = request.cookies.get("access_token")
        # Enforce CSRF protection for cookie-based mutating requests
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")
            if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF validation failed for cookie-authenticated session."
                )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        token_type: str = payload.get("token_type", "access")
        if user_id is None or token_type != "access":
            raise credentials_exception
        
        # Check revocation blacklist
        if jti and is_token_revoked(db, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been terminated or logged out. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled"
        )
    return user


def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

