import random
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Patient, User
from app.schemas.schemas import PatientCreate
from app.services.audit_service import record_audit_log


def generate_patient_number(db: Session) -> str:
    """Generate collision-resistant PAT-YYYYMM-XXXXXX format identifier."""
    prefix = f"PAT-{date.today().strftime('%Y%m')}"
    for _ in range(30):
        suffix = f"{random.randint(100000, 999999)}"
        candidate = f"{prefix}-{suffix}"
        if not db.query(Patient).filter(Patient.patient_number == candidate).first():
            return candidate
    raise RuntimeError("Failed to generate unique patient identifier")


def create_patient_record(db: Session, data: PatientCreate, current_user_id: int) -> Patient:
    """Create a new patient record decoupled from an auth user account."""
    # Duplicate prevention checks
    if data.email:
        existing_patient_email = db.query(Patient).filter(
            (Patient.email == data.email) | (Patient.user.has(User.email == data.email))
        ).first()
        if existing_patient_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A patient with this email address already exists."
            )

    if data.phone and data.full_name:
        existing_phone_name = db.query(Patient).filter(
            (Patient.phone == data.phone) & 
            ((Patient.full_name == data.full_name) | (Patient.user.has(User.full_name == data.full_name)))
        ).first()
        if existing_phone_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A patient with this full name and phone number already exists."
            )

    patient_number = generate_patient_number(db)

    patient = Patient(
        patient_number=patient_number,
        user_id=None,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        blood_group=data.blood_group,
        emergency_contact=data.emergency_contact,
        address=data.address,
        medical_history_summary=data.medical_history_summary,
        insurance_provider=data.insurance_provider,
        insurance_policy_number=data.insurance_policy_number
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    record_audit_log(
        db=db,
        action="PATIENT_CREATE",
        resource_type="Patient",
        resource_id=str(patient.id),
        user_id=current_user_id,
        details={
            "patient_number": patient.patient_number,
            "full_name": patient.full_name,
            "created_by": current_user_id
        }
    )

    return patient
