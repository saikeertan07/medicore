from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import Appointment, User, UserRole, AppointmentStatus
from app.schemas.schemas import (
    AppointmentOut, AppointmentCreate, AvailableSlotsOut, 
    AppointmentReschedule, AppointmentCancel, AppointmentCheckIn, AppointmentStatusUpdate
)
from app.services.appointment_service import (
    get_available_slots, create_appointment, reschedule_appointment, 
    cancel_appointment, check_in_appointment, update_appointment_status, get_hospital_now
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])

def appointment_to_out(app: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=app.id,
        appointment_number=app.appointment_number,
        patient_id=app.patient_id,
        patient_name=app.patient.display_name if app.patient else "Unknown Patient",
        doctor_id=app.doctor_id,
        doctor_name=app.doctor.user.full_name if app.doctor and app.doctor.user else "Unknown Doctor",
        doctor_specialization=app.doctor.specialization if app.doctor else "",
        department_id=app.department_id,
        department_name=app.department.name if app.department else "",
        date=app.date,
        start_time=app.start_time,
        end_time=app.end_time,
        type=app.type,
        status=app.status,
        check_in_time=app.check_in_time,
        reason=app.reason,
        notes=app.notes,
        created_at=app.created_at,
        updated_at=app.updated_at
    )

@router.get("/available-slots", response_model=AvailableSlotsOut)
def fetch_available_slots(
    doctor_id: int = Query(..., description="Doctor ID"),
    date_val: date = Query(..., alias="date", description="Date to check (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    return get_available_slots(db=db, doctor_id=doctor_id, target_date=date_val)

@router.get("/today", response_model=List[AppointmentOut])
def list_today_appointments(
    department_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    status_filter: Optional[AppointmentStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_date = get_hospital_now().date()
    query = db.query(Appointment).filter(Appointment.date == today_date)

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            return []
        query = query.filter(Appointment.patient_id == current_user.patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            return []
        query = query.filter(Appointment.doctor_id == current_user.doctor_profile.id)
    else:
        if department_id:
            query = query.filter(Appointment.department_id == department_id)
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    appointments = query.order_by(Appointment.start_time.asc()).all()
    return [appointment_to_out(app) for app in appointments]

@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def book_appointment(
    booking_in: AppointmentCreate,
    request: Request,
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Determine target patient_id based on role and payload/query
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User profile is not a patient.")
        target_patient_id = current_user.patient_profile.id
    elif current_user.role in [UserRole.ADMIN, UserRole.STAFF, UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.NURSE]:
        target_patient_id = booking_in.patient_id or patient_id
        if not target_patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required when booking on behalf of a patient.")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to book appointments.")

    client_ip = request.client.host if request.client else None

    # Idempotency check: if client retries with an Idempotency-Key, safely return existing booking
    idempotency_key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
    if idempotency_key:
        existing = db.query(Appointment).filter(
            Appointment.patient_id == target_patient_id,
            Appointment.doctor_id == booking_in.doctor_id,
            Appointment.date == booking_in.date,
            Appointment.start_time == booking_in.start_time,
            Appointment.status != AppointmentStatus.CANCELLED
        ).first()
        if existing:
            return appointment_to_out(existing)

    appointment = create_appointment(
        db=db,
        patient_id=target_patient_id,
        booking_data=booking_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return appointment_to_out(appointment)

@router.get("", response_model=List[AppointmentOut])
def list_appointments(
    status_filter: Optional[AppointmentStatus] = None,
    doctor_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    date_val: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Appointment)

    # Strict Role-Based Filtering
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            return []
        query = query.filter(Appointment.patient_id == current_user.patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            return []
        query = query.filter(Appointment.doctor_id == current_user.doctor_profile.id)
    else:
        # Staff, Nurse, Receptionist, Admin can view queue with filters
        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)
        if patient_id:
            query = query.filter(Appointment.patient_id == patient_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    if date_val:
        query = query.filter(Appointment.date == date_val)

    appointments = query.order_by(Appointment.date.desc(), Appointment.start_time.asc()).all()
    return [appointment_to_out(app) for app in appointments]

@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment_detail(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Strict Object-Level Authorization Check
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or appointment.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this appointment.")
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or appointment.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Not your consultation.")

    return appointment_to_out(appointment)

@router.post("/{appointment_id}/check-in", response_model=AppointmentOut)
def check_in(
    appointment_id: int,
    check_in_data: Optional[AppointmentCheckIn] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]))
):
    client_ip = request.client.host if request and request.client else None
    notes = check_in_data.notes if check_in_data else None
    updated = check_in_appointment(
        db=db,
        appointment_id=appointment_id,
        current_user=current_user,
        notes=notes,
        ip_address=client_ip
    )
    return appointment_to_out(updated)

@router.post("/{appointment_id}/status", response_model=AppointmentOut)
def update_status(
    appointment_id: int,
    status_data: AppointmentStatusUpdate,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST, UserRole.STAFF]))
):
    client_ip = request.client.host if request and request.client else None
    updated = update_appointment_status(
        db=db,
        appointment_id=appointment_id,
        new_status=status_data.status,
        current_user=current_user,
        notes=status_data.notes,
        ip_address=client_ip
    )
    return appointment_to_out(updated)

@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule(
    appointment_id: int,
    reschedule_in: AppointmentReschedule,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Authorization check
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or appointment.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or appointment.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    client_ip = request.client.host if request.client else None
    updated = reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        reschedule_data=reschedule_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return appointment_to_out(updated)

@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel(
    appointment_id: int,
    cancel_in: AppointmentCancel,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Authorization check
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or appointment.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or appointment.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    client_ip = request.client.host if request.client else None
    cancelled = cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        cancellation_reason=cancel_in.cancellation_reason,
        current_user=current_user,
        ip_address=client_ip
    )
    return appointment_to_out(cancelled)
