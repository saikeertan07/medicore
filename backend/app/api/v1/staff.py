from datetime import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user, require_roles, get_password_hash
from app.models.models import User, UserRole, Doctor, DoctorSchedule, Department, StaffProfile
from app.schemas.schemas import StaffCreate, StaffUpdate, StaffStatusUpdate, StaffOut
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/staff", tags=["Staff Management"])

def staff_to_out(user: User) -> StaffOut:
    department_id = None
    department_name = None
    job_title = None
    shift = None
    qualifications = None
    employee_id = None
    doctor_id = None

    if user.role == UserRole.DOCTOR and user.doctor_profile:
        doctor_id = user.doctor_profile.id
        department_id = user.doctor_profile.department_id
        department_name = user.doctor_profile.department.name if user.doctor_profile.department else None
        job_title = f"Physician ({user.doctor_profile.specialization})"
        qualifications = user.doctor_profile.qualification
    elif user.staff_profile:
        department_id = user.staff_profile.department_id
        department_name = user.staff_profile.department.name if user.staff_profile.department else None
        job_title = user.staff_profile.job_title
        shift = user.staff_profile.shift
        qualifications = user.staff_profile.qualifications
        employee_id = user.staff_profile.employee_id

    return StaffOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        department_id=department_id,
        department_name=department_name,
        job_title=job_title,
        shift=shift,
        qualifications=qualifications,
        employee_id=employee_id,
        doctor_id=doctor_id,
        created_at=user.created_at
    )

@router.get("", response_model=List[StaffOut])
def list_staff(
    role: Optional[UserRole] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]))
):
    query = db.query(User).filter(
        User.role.in_([UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.ADMIN, UserRole.STAFF])
    )
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        p = f"%{search}%"
        query = query.filter(or_(User.full_name.ilike(p), User.email.ilike(p), User.phone.ilike(p)))

    staff_users = query.order_by(User.id.desc()).all()
    results = [staff_to_out(u) for u in staff_users]

    if department_id:
        results = [s for s in results if s.department_id == department_id]

    return results

@router.post("", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff_member(
    staff_in: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    existing = db.query(User).filter(User.email == staff_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email address already exists.")

    if staff_in.department_id:
        dept = db.query(Department).filter(Department.id == staff_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    user = User(
        email=staff_in.email,
        hashed_password=get_password_hash(staff_in.password),
        full_name=staff_in.full_name,
        role=staff_in.role,
        phone=staff_in.phone,
        is_active=True
    )
    db.add(user)
    db.flush()

    if staff_in.role == UserRole.DOCTOR:
        if not staff_in.department_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="department_id is required for doctor staff.")
        doctor = Doctor(
            user_id=user.id,
            department_id=staff_in.department_id,
            specialization=staff_in.specialization or "General Medicine",
            qualification=staff_in.qualifications or "MBBS, MD",
            experience_years=staff_in.experience_years or 5,
            consultation_fee=staff_in.consultation_fee or 150.00,
            room_number=staff_in.room_number or "Room 101",
            bio=staff_in.bio
        )
        db.add(doctor)
        db.flush()

        # Seed standard 7-day schedules so newly created doctor is immediately schedulable
        for day in range(7):
            sched = DoctorSchedule(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(17, 0),
                slot_duration_minutes=30,
                is_available=True
            )
            db.add(sched)
    else:
        profile = StaffProfile(
            user_id=user.id,
            department_id=staff_in.department_id,
            job_title=staff_in.job_title or (
                "Registered Nurse" if staff_in.role == UserRole.NURSE else
                "Front Desk Receptionist" if staff_in.role == UserRole.RECEPTIONIST else
                "Staff Member"
            ),
            shift=staff_in.shift or "Morning",
            qualifications=staff_in.qualifications or "Certified Professional",
            employee_id=f"EMP-{user.id:04d}"
        )
        db.add(profile)

    db.commit()
    db.refresh(user)

    record_audit_log(
        db=db,
        action="STAFF_CREATE",
        resource_type="User",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"role": user.role.value, "email": user.email, "full_name": user.full_name}
    )

    return staff_to_out(user)

@router.get("/{user_id}", response_model=StaffOut)
def get_staff_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role not in [UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")
    return staff_to_out(user)

@router.put("/{user_id}", response_model=StaffOut)
def update_staff_member(
    user_id: int,
    staff_in: StaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    if staff_in.full_name is not None:
        user.full_name = staff_in.full_name
    if staff_in.phone is not None:
        user.phone = staff_in.phone
    if staff_in.is_active is not None:
        user.is_active = staff_in.is_active

    if user.role == UserRole.DOCTOR and user.doctor_profile:
        if staff_in.department_id is not None:
            user.doctor_profile.department_id = staff_in.department_id
        if staff_in.specialization is not None:
            user.doctor_profile.specialization = staff_in.specialization
        if staff_in.qualifications is not None:
            user.doctor_profile.qualification = staff_in.qualifications
        if staff_in.consultation_fee is not None:
            user.doctor_profile.consultation_fee = staff_in.consultation_fee
        if staff_in.room_number is not None:
            user.doctor_profile.room_number = staff_in.room_number
    elif user.staff_profile:
        if staff_in.department_id is not None:
            user.staff_profile.department_id = staff_in.department_id
        if staff_in.job_title is not None:
            user.staff_profile.job_title = staff_in.job_title
        if staff_in.shift is not None:
            user.staff_profile.shift = staff_in.shift
        if staff_in.qualifications is not None:
            user.staff_profile.qualifications = staff_in.qualifications

    db.commit()
    db.refresh(user)

    record_audit_log(
        db=db,
        action="STAFF_UPDATE",
        resource_type="User",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"updated_by": current_user.id}
    )

    return staff_to_out(user)

@router.patch("/{user_id}/status", response_model=StaffOut)
def toggle_staff_status(
    user_id: int,
    status_in: StaffStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    user.is_active = status_in.is_active
    db.commit()
    db.refresh(user)

    record_audit_log(
        db=db,
        action="STAFF_STATUS_UPDATE",
        resource_type="User",
        resource_id=str(user.id),
        user_id=current_user.id,
        details={"is_active": user.is_active}
    )

    return staff_to_out(user)
