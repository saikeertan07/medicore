import uuid
from datetime import datetime, date, time, timedelta
from app.core.datetime_utils import utc_now
from zoneinfo import ZoneInfo
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.models import (
    Appointment, AppointmentStatus, AppointmentType, Doctor, DoctorSchedule, Patient, User
)
from app.schemas.schemas import TimeSlot, AvailableSlotsOut, AppointmentCreate, AppointmentReschedule
from app.services.audit_service import record_audit_log
from app.services.notification_service import create_notification

def get_hospital_now() -> datetime:
    """Returns the current timezone-aware timestamp for the hospital."""
    try:
        tz = ZoneInfo(settings.HOSPITAL_TIMEZONE)
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz)

def generate_appointment_number() -> str:
    now_str = get_hospital_now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"MED-{now_str}-{random_part}"

def is_slot_in_past(target_date: date, slot_time: time) -> bool:
    """Timezone-aware check determining if a specific slot date and time has already passed."""
    now = get_hospital_now()
    today = now.date()
    if target_date < today:
        return True
    if target_date == today and slot_time <= now.time():
        return True
    return False

def validate_doctor_and_schedule(
    db: Session,
    doctor_id: int,
    target_date: date,
    department_id: Optional[int] = None
) -> Tuple[Doctor, DoctorSchedule]:
    """
    Validates doctor existence, active status, department alignment, and weekday schedule.
    Shared identically by availability lookups and booking/rescheduling operations.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found."
        )
    if not doctor.user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dr. {doctor.user.full_name} is currently inactive or not taking appointments."
        )

    if department_id is not None and doctor.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor {doctor.user.full_name} belongs to department ID {doctor.department_id}, not requested department ID {department_id}."
        )

    weekday = target_date.weekday()
    sched = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.day_of_week == weekday,
        DoctorSchedule.is_available == True
    ).first()

    if not sched:
        weekday_name = target_date.strftime("%A")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dr. {doctor.user.full_name} has no scheduled clinical hours on {weekday_name}s."
        )

    return doctor, sched

def validate_slot_timing(sched: DoctorSchedule, target_date: date, start_time: time, end_time: time) -> None:
    """
    Validates time slot boundaries, past-time rules, duration, and grid alignment.
    Shared identically across create_appointment, reschedule_appointment, and get_available_slots.
    """
    # Past date/time validation using hospital timezone
    if is_slot_in_past(target_date, start_time):
        now = get_hospital_now()
        if target_date < now.date():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book appointments for past dates."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book an appointment slot that has already passed today."
            )

    # Operating hours
    if start_time < sched.start_time or end_time > sched.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested time {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} is outside working hours ({sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')})."
        )

    # Duration check
    start_dt = datetime.combine(target_date, start_time)
    end_dt = datetime.combine(target_date, end_time)
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    if duration_minutes != sched.slot_duration_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slot duration must be exactly {sched.slot_duration_minutes} minutes (received {duration_minutes} minutes)."
        )

    # Grid alignment check
    sched_start_dt = datetime.combine(target_date, sched.start_time)
    offset_minutes = int((start_dt - sched_start_dt).total_seconds() / 60)
    if offset_minutes % sched.slot_duration_minutes != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested start time {start_time.strftime('%H:%M')} is not aligned to the {sched.slot_duration_minutes}-minute schedule grid."
        )

def validate_slot_and_schedule(
    db: Session,
    doctor_id: int,
    department_id: Optional[int],
    target_date: date,
    start_time: Optional[time] = None,
    end_time: Optional[time] = None,
    patient_id: Optional[int] = None,
    doctor: Optional[Doctor] = None,
    sched: Optional[DoctorSchedule] = None
) -> Tuple[Doctor, DoctorSchedule, Optional[Patient]]:
    """
    Authoritative single scheduling validation rule engine.
    Used identically by create_appointment, reschedule_appointment, and get_available_slots.
    """
    if doctor is None or sched is None:
        doctor, sched = validate_doctor_and_schedule(
            db=db,
            doctor_id=doctor_id,
            target_date=target_date,
            department_id=department_id
        )
    elif department_id is not None and doctor.department_id != department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor {doctor.user.full_name} belongs to department ID {doctor.department_id}, not requested department ID {department_id}."
        )

    patient = None
    if patient_id is not None:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} not found."
            )

    if start_time is not None and end_time is not None:
        validate_slot_timing(
            sched=sched,
            target_date=target_date,
            start_time=start_time,
            end_time=end_time
        )

    return doctor, sched, patient

def get_available_slots(db: Session, doctor_id: int, target_date: date) -> AvailableSlotsOut:
    """
    Generates and returns available time slots for a doctor on a given date.
    Strictly and genuinely uses validate_slot_and_schedule() as the authoritative
    scheduling validation engine for doctor, schedule, and candidate slot rules.
    """
    # 1. Authoritatively validate doctor and schedule
    try:
        doctor, sched, _ = validate_slot_and_schedule(
            db=db,
            doctor_id=doctor_id,
            department_id=None,
            target_date=target_date,
            start_time=None,
            end_time=None,
            patient_id=None
        )
    except HTTPException as he:
        # If doctor not found (404), bubble up
        if he.status_code == status.HTTP_404_NOT_FOUND:
            raise he
        # If doctor is inactive or has no schedule on that day (400), return empty slots
        return AvailableSlotsOut(doctor_id=doctor_id, date=target_date, slots=[])

    # 2. Fetch active appointments excluding CANCELLED
    booked_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == target_date,
        Appointment.status != AppointmentStatus.CANCELLED
    ).all()
    booked_times = {app.start_time for app in booked_appointments}

    # 3. Generate candidate slots and authoritatively validate each candidate
    slots: List[TimeSlot] = []
    current_dt = datetime.combine(target_date, sched.start_time)
    end_dt = datetime.combine(target_date, sched.end_time)
    slot_delta = timedelta(minutes=sched.slot_duration_minutes)

    while current_dt + slot_delta <= end_dt:
        cand_start = current_dt.time()
        cand_end = (current_dt + slot_delta).time()

        # Validate candidate slot through validate_slot_and_schedule
        try:
            validate_slot_and_schedule(
                db=db,
                doctor_id=doctor_id,
                department_id=None,
                target_date=target_date,
                start_time=cand_start,
                end_time=cand_end,
                patient_id=None,
                doctor=doctor,
                sched=sched
            )
            # Passed authoritative doctor + schedule + timing rules!
            is_available = cand_start not in booked_times
        except HTTPException:
            # Failed timing/schedule rules (e.g. past slot, outside hours, invalid grid)
            is_available = False

        slots.append(TimeSlot(start_time=cand_start, end_time=cand_end, is_available=is_available))
        current_dt += slot_delta

    return AvailableSlotsOut(doctor_id=doctor_id, date=target_date, slots=slots)

def create_appointment(
    db: Session,
    patient_id: int,
    booking_data: AppointmentCreate,
    current_user: User,
    ip_address: Optional[str] = None
) -> Appointment:
    # 1. Shared rigorous schedule, doctor, department, and past-time validation
    doctor, sched, patient = validate_slot_and_schedule(
        db=db,
        doctor_id=booking_data.doctor_id,
        department_id=booking_data.department_id,
        target_date=booking_data.date,
        start_time=booking_data.start_time,
        end_time=booking_data.end_time,
        patient_id=patient_id
    )

    # 2. Friendly application-level conflict check
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == booking_data.doctor_id,
        Appointment.date == booking_data.date,
        Appointment.start_time == booking_data.start_time,
        Appointment.status != AppointmentStatus.CANCELLED
    ).first()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The selected time slot ({booking_data.start_time.strftime('%H:%M')} on {booking_data.date}) is already booked for Dr. {doctor.user.full_name}."
        )

    # 3. Database-enforced atomic insertion (protected by uq_doctor_active_slot)
    appointment = Appointment(
        appointment_number=generate_appointment_number(),
        patient_id=patient_id,
        doctor_id=booking_data.doctor_id,
        department_id=booking_data.department_id,
        date=booking_data.date,
        start_time=booking_data.start_time,
        end_time=booking_data.end_time,
        type=booking_data.type,
        status=AppointmentStatus.CONFIRMED,
        reason=booking_data.reason,
        notes=booking_data.notes
    )

    try:
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
    except IntegrityError as exc:
        db.rollback()
        # Database partial unique index triggered on concurrent race condition
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot conflict: Another patient reserved this time slot simultaneously. Please select another slot."
        ) from exc
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while confirming your appointment."
        ) from e

    # 4. Notifications & Audit
    try:
        if patient.user_id:
            create_notification(
                db=db,
                user_id=patient.user_id,
                title="Appointment Confirmed",
                message=f"Your appointment with Dr. {doctor.user.full_name} is confirmed for {appointment.date} at {appointment.start_time.strftime('%H:%M')}.",
                notification_type="APPOINTMENT",
                link="/patient/appointments"
            )
        create_notification(
            db=db,
            user_id=doctor.user_id,
            title="New Appointment Scheduled",
            message=f"New consultation scheduled with {patient.display_name} on {appointment.date} at {appointment.start_time.strftime('%H:%M')}.",
            notification_type="APPOINTMENT",
            link="/doctor/appointments"
        )
        record_audit_log(
            db=db,
            action="APPOINTMENT_CREATE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            user_id=current_user.id,
            details={
                "appointment_number": appointment.appointment_number,
                "doctor_id": doctor.id,
                "patient_id": patient.id,
                "date": str(appointment.date),
                "start_time": str(appointment.start_time),
                "type": appointment.type.value
            },
            ip_address=ip_address
        )
    except Exception:
        pass

    return appointment

def reschedule_appointment(
    db: Session,
    appointment_id: int,
    reschedule_data: AppointmentReschedule,
    current_user: User,
    ip_address: Optional[str] = None
) -> Appointment:
    # 1. Fetch existing appointment
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reschedule a cancelled appointment.")

    # 2. Validate new requested slot using the same authoritative schedule validation
    doctor, sched, _ = validate_slot_and_schedule(
        db=db,
        doctor_id=appointment.doctor_id,
        department_id=appointment.department_id,
        target_date=reschedule_data.new_date,
        start_time=reschedule_data.new_start_time,
        end_time=reschedule_data.new_end_time,
        patient_id=appointment.patient_id
    )

    # 3. Check target slot availability (excluding this appointment itself)
    conflict = db.query(Appointment).filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.date == reschedule_data.new_date,
        Appointment.start_time == reschedule_data.new_start_time,
        Appointment.id != appointment.id,
        Appointment.status != AppointmentStatus.CANCELLED
    ).first()

    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested new time slot is already booked. Please choose another slot."
        )

    # 4. Atomic transaction update: Old slot is NOT released until new slot commits!
    old_date = appointment.date
    old_time = appointment.start_time
    
    appointment.date = reschedule_data.new_date
    appointment.start_time = reschedule_data.new_start_time
    appointment.end_time = reschedule_data.new_end_time
    appointment.status = AppointmentStatus.CONFIRMED
    if reschedule_data.reason:
        appointment.notes = f"{appointment.notes or ''}\nRescheduled: {reschedule_data.reason}".strip()

    try:
        db.commit()
        db.refresh(appointment)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Concurrent booking conflict. The requested slot was just claimed by another patient."
        ) from exc
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reschedule appointment."
        ) from e

    # 5. Notifications & Audit
    try:
        if appointment.patient.user_id:
            create_notification(
                db=db,
                user_id=appointment.patient.user_id,
                title="Appointment Rescheduled",
                message=f"Your appointment has been moved to {appointment.date} at {appointment.start_time.strftime('%H:%M')}.",
                notification_type="APPOINTMENT",
                link="/patient/appointments"
            )
        create_notification(
            db=db,
            user_id=appointment.doctor.user_id,
            title="Appointment Rescheduled",
            message=f"Appointment with {appointment.patient.display_name} moved to {appointment.date} at {appointment.start_time.strftime('%H:%M')}.",
            notification_type="APPOINTMENT",
            link="/doctor/appointments"
        )
        record_audit_log(
            db=db,
            action="APPOINTMENT_RESCHEDULE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            user_id=current_user.id,
            details={
                "appointment_number": appointment.appointment_number,
                "old_date": str(old_date),
                "old_time": str(old_time),
                "new_date": str(appointment.date),
                "new_time": str(appointment.start_time)
            },
            ip_address=ip_address
        )
    except Exception:
        pass

    return appointment

def cancel_appointment(
    db: Session,
    appointment_id: int,
    cancellation_reason: Optional[str],
    current_user: User,
    ip_address: Optional[str] = None
) -> Appointment:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment is already cancelled.")

    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel an appointment that has already been completed.")

    appointment.status = AppointmentStatus.CANCELLED
    if cancellation_reason:
        appointment.notes = f"{appointment.notes or ''}\nCancelled: {cancellation_reason}".strip()

    db.commit()
    db.refresh(appointment)

    # Notifications & Audit
    try:
        if appointment.patient.user_id:
            create_notification(
                db=db,
                user_id=appointment.patient.user_id,
                title="Appointment Cancelled",
                message=f"Appointment with Dr. {appointment.doctor.user.full_name} on {appointment.date} was cancelled.",
                notification_type="APPOINTMENT",
                link="/patient/appointments"
            )
        create_notification(
            db=db,
            user_id=appointment.doctor.user_id,
            title="Appointment Cancelled",
            message=f"Appointment with {appointment.patient.display_name} on {appointment.date} was cancelled.",
            notification_type="APPOINTMENT",
            link="/doctor/appointments"
        )
        record_audit_log(
            db=db,
            action="APPOINTMENT_CANCEL",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            user_id=current_user.id,
            details={
                "appointment_number": appointment.appointment_number,
                "cancellation_reason": cancellation_reason
            },
            ip_address=ip_address
        )
    except Exception:
        pass

    return appointment

# Authoritative Appointment State Machine
ALLOWED_TRANSITIONS = {
    AppointmentStatus.CONFIRMED: [
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ],
    AppointmentStatus.SCHEDULED: [
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ],
    AppointmentStatus.CHECKED_IN: [
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ],
    AppointmentStatus.IN_PROGRESS: [
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    ],
    AppointmentStatus.COMPLETED: [],
    AppointmentStatus.CANCELLED: [],
    AppointmentStatus.NO_SHOW: [],
}

def check_in_appointment(
    db: Session,
    appointment_id: int,
    current_user: User,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Appointment:
    """Check in a patient upon arrival at hospital reception/triage."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in an appointment that is already {appointment.status.value}."
        )

    if appointment.status == AppointmentStatus.CHECKED_IN:
        # Idempotent: already checked in
        return appointment

    if appointment.status not in [AppointmentStatus.CONFIRMED, AppointmentStatus.SCHEDULED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in appointment with status {appointment.status.value}."
        )

    appointment.status = AppointmentStatus.CHECKED_IN
    appointment.check_in_time = utc_now()
    if notes:
        appointment.notes = f"{appointment.notes or ''}\nCheck-in Note: {notes}".strip()

    db.commit()
    db.refresh(appointment)

    try:
        record_audit_log(
            db=db,
            action="APPOINTMENT_CHECK_IN",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            user_id=current_user.id,
            details={
                "appointment_number": appointment.appointment_number,
                "check_in_time": str(appointment.check_in_time)
            },
            ip_address=ip_address
        )
        create_notification(
            db=db,
            user_id=appointment.doctor.user_id,
            title="Patient Checked In",
            message=f"{appointment.patient.display_name} has arrived and checked in for their consultation.",
            notification_type="QUEUE_ALERT",
            link="/doctor/appointments"
        )
    except Exception:
        pass

    return appointment

def update_appointment_status(
    db: Session,
    appointment_id: int,
    new_status: AppointmentStatus,
    current_user: User,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None
) -> Appointment:
    """Transition appointment status following authoritative hospital state machine."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    if appointment.status == new_status:
        return appointment  # No-op

    valid_targets = ALLOWED_TRANSITIONS.get(appointment.status, [])
    if new_status not in valid_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid appointment status transition from {appointment.status.value} to {new_status.value}."
        )

    old_status = appointment.status
    appointment.status = new_status
    if new_status == AppointmentStatus.CHECKED_IN and not appointment.check_in_time:
        appointment.check_in_time = utc_now()

    if notes:
        appointment.notes = f"{appointment.notes or ''}\nStatus update ({new_status.value}): {notes}".strip()

    db.commit()
    db.refresh(appointment)

    try:
        record_audit_log(
            db=db,
            action="APPOINTMENT_STATUS_UPDATE",
            resource_type="Appointment",
            resource_id=str(appointment.id),
            user_id=current_user.id,
            details={
                "appointment_number": appointment.appointment_number,
                "old_status": old_status.value,
                "new_status": new_status.value
            },
            ip_address=ip_address
        )
    except Exception:
        pass

    return appointment

