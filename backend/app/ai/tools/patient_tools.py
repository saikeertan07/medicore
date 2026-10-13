from datetime import datetime, date, time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import User, Doctor, Department, Appointment, HospitalService, Patient, Prescription
from app.schemas.schemas import AppointmentCreate, AppointmentReschedule
from app.services.appointment_service import (
    get_available_slots as fetch_slots,
    create_appointment as book_slot,
    reschedule_appointment as resched_slot,
    cancel_appointment as cancel_slot
)
from app.services.rag_service import rag_service

def search_doctors(db: Session, current_user: User, search_term: Optional[str] = None, department: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(Doctor).join(User, Doctor.user_id == User.id).join(Department, Doctor.department_id == Department.id)
    if search_term:
        query = query.filter((User.full_name.ilike(f"%{search_term}%")) | (Doctor.specialization.ilike(f"%{search_term}%")))
    if department:
        query = query.filter((Department.name.ilike(f"%{department}%")) | (Department.code.ilike(f"%{department}%")))
    doctors = query.all()
    return [{
        "doctor_id": d.id,
        "name": d.user.full_name,
        "specialization": d.specialization,
        "department": d.department.name,
        "department_id": d.department_id,
        "fee": float(d.consultation_fee),
        "rating": float(d.rating),
        "room": d.room_number
    } for d in doctors]

def get_available_slots(db: Session, current_user: User, doctor_id: int, date_str: str) -> Dict[str, Any]:
    try:
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}
    
    slots_out = fetch_slots(db=db, doctor_id=doctor_id, target_date=t_date)
    return {
        "doctor_id": doctor_id,
        "date": date_str,
        "available_slots": [
            f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}"
            for s in slots_out.slots if s.is_available
        ]
    }

def create_appointment(
    db: Session,
    current_user: User,
    doctor_id: int,
    department_id: int,
    date_str: str,
    start_time_str: str,
    end_time_str: str,
    reason: str
) -> Dict[str, Any]:
    if not current_user.patient_profile:
        return {"error": "User does not have an active patient profile."}

    try:
        app_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        s_time = datetime.strptime(start_time_str, "%H:%M").time()
        e_time = datetime.strptime(end_time_str, "%H:%M").time()
    except Exception as e:
        return {"error": f"Invalid date or time format: {e}"}

    create_data = AppointmentCreate(
        doctor_id=doctor_id,
        department_id=department_id,
        date=app_date,
        start_time=s_time,
        end_time=e_time,
        reason=reason
    )

    try:
        app = book_slot(
            db=db,
            patient_id=current_user.patient_profile.id,
            booking_data=create_data,
            current_user=current_user
        )
        return {
            "success": True,
            "appointment_id": app.id,
            "appointment_number": app.appointment_number,
            "status": app.status.value,
            "doctor": app.doctor.user.full_name,
            "date": str(app.date),
            "time": app.start_time.strftime("%H:%M")
        }
    except Exception as exc:
        return {"error": str(exc.detail if hasattr(exc, "detail") else exc)}

def get_patient_appointments(db: Session, current_user: User) -> List[Dict[str, Any]]:
    if not current_user.patient_profile:
        return []

    apps = db.query(Appointment).filter(
        Appointment.patient_id == current_user.patient_profile.id
    ).order_by(Appointment.date.desc()).all()

    return [{
        "appointment_id": a.id,
        "appointment_number": a.appointment_number,
        "doctor": a.doctor.user.full_name,
        "department": a.department.name,
        "date": str(a.date),
        "start_time": a.start_time.strftime("%H:%M"),
        "status": a.status.value,
        "reason": a.reason
    } for a in apps]

def cancel_appointment(db: Session, current_user: User, appointment_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    app = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not app:
        return {"error": "Appointment not found."}
    if not current_user.patient_profile or app.patient_id != current_user.patient_profile.id:
        return {"error": "Access denied: You cannot cancel another patient's appointment."}

    try:
        updated = cancel_slot(db=db, appointment_id=appointment_id, cancellation_reason=reason, current_user=current_user)
        return {
            "success": True,
            "appointment_id": updated.id,
            "status": updated.status.value,
            "message": "Appointment cancelled successfully."
        }
    except Exception as e:
        return {"error": str(e)}

def search_hospital_knowledge(db: Session, current_user: User, query: str) -> List[Dict[str, Any]]:
    results = rag_service.search_knowledge(db=db, query=query, limit=3)
    return results

def get_patient_prescriptions(db: Session, current_user: User) -> List[Dict[str, Any]]:
    if not current_user.patient_profile:
        return []

    prescriptions = db.query(Prescription).filter(
        Prescription.patient_id == current_user.patient_profile.id
    ).order_by(Prescription.created_at.desc()).all()

    results = []
    for p in prescriptions:
        results.append({
            "prescription_id": p.id,
            "doctor": p.doctor.user.full_name if p.doctor and p.doctor.user else "Attending Physician",
            "is_active": True,
            "medications": p.medications,
            "instructions": p.instructions,
            "date": p.created_at.strftime("%Y-%m-%d") if p.created_at else "Recent"
        })
    return results

