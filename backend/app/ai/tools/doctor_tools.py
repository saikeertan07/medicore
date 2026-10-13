from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import (
    User, UserRole, Patient, MedicalDocument, Appointment, AppointmentStatus, MedicalReport, Prescription
)
from app.services.rag_service import rag_service

# Permitted active/clinical attending statuses that establish an authorized relationship
AUTHORIZED_ENCOUNTER_STATUSES = [
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.COMPLETED
]

def verify_doctor_patient_authorization(db: Session, current_user: User, patient_id: int) -> Optional[str]:
    """
    Verifies that the authenticated user is an authorized attending physician for the specified patient.
    Authorization is established strictly via active, scheduled, in-progress, or completed appointments.
    """
    if not current_user:
        return "Authentication required. No authenticated user context provided."

    if current_user.role == UserRole.ADMIN:
        # Administrative clinical audit access permitted
        return None

    if current_user.role != UserRole.DOCTOR:
        return f"Access denied: User role '{current_user.role.value}' is not authorized to access clinical records."

    if not current_user.doctor_profile:
        return "Access denied: Physician clinical profile is not configured."

    # Check for active clinical relationship in database model
    encounter = db.query(Appointment).filter(
        Appointment.doctor_id == current_user.doctor_profile.id,
        Appointment.patient_id == patient_id,
        Appointment.status.in_(AUTHORIZED_ENCOUNTER_STATUSES)
    ).first()

    if not encounter:
        return (
            f"Access denied: Dr. {current_user.full_name} does not have an active, scheduled, "
            f"or completed clinical encounter with patient ID {patient_id}. Access to protected records is restricted."
        )

    return None

def summarize_patient_history(db: Session, current_user: User, patient_id: int) -> Dict[str, Any]:
    # 1. Enforce strict backend authorization check
    auth_error = verify_doctor_patient_authorization(db, current_user, patient_id)
    if auth_error:
        return {"error": auth_error, "authorized": False}

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"error": f"Patient with ID {patient_id} not found.", "authorized": False}

    docs = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id).all()
    past_apps = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.status.in_(AUTHORIZED_ENCOUNTER_STATUSES)
    ).all()

    doc_summaries = [d.summary for d in docs if d.summary]
    app_reasons = [f"{a.date} ({a.status.value}): {a.reason}" for a in past_apps]

    return {
        "authorized": True,
        "patient_name": patient.user.full_name,
        "patient_id": patient.id,
        "dob": str(patient.date_of_birth),
        "blood_group": patient.blood_group,
        "medical_history": patient.medical_history_summary,
        "recent_documents_count": len(docs),
        "document_summaries": doc_summaries[:3],
        "clinical_encounters": app_reasons[:4],
        "clinical_disclaimer": "AI-generated clinical digest for healthcare provider review only. Professional clinical assessment required."
    }

def summarize_document(db: Session, current_user: User, document_id: int) -> Dict[str, Any]:
    if not current_user:
        return {"error": "Authentication required."}

    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        return {"error": "Document not found."}

    # Verify authorization to view this document
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or doc.patient_id != current_user.patient_profile.id:
            return {"error": "Access denied to this document."}
    elif current_user.role == UserRole.DOCTOR:
        auth_error = verify_doctor_patient_authorization(db, current_user, doc.patient_id)
        if auth_error:
            return {"error": auth_error}

    return {
        "document_id": doc.id,
        "file_name": doc.file_name,
        "patient_id": doc.patient_id,
        "status": doc.status.value,
        "summary": doc.summary or "No summary available.",
        "extracted_data": doc.extracted_data or {},
        "clinical_disclaimer": "AI-generated extraction. Requires physician verification."
    }

def search_hospital_clinical_guidelines(db: Session, current_user: User, query: str):
    if not current_user:
        return []
    return rag_service.search_knowledge(db=db, query=query, limit=3)

def get_patient_prescriptions(db: Session, current_user: User, patient_id: int) -> Dict[str, Any]:
    auth_error = verify_doctor_patient_authorization(db, current_user, patient_id)
    if auth_error:
        return {"error": auth_error, "authorized": False}

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"error": f"Patient with ID {patient_id} not found.", "authorized": False}

    prescriptions = db.query(Prescription).filter(
        Prescription.patient_id == patient_id
    ).order_by(Prescription.created_at.desc()).all()

    rx_list = []
    for p in prescriptions:
        rx_list.append({
            "prescription_id": p.id,
            "is_active": True,
            "created_at": p.created_at.strftime("%Y-%m-%d") if p.created_at else "Recent",
            "medications": p.medications,
            "instructions": p.instructions
        })

    return {
        "authorized": True,
        "patient_name": patient.user.full_name if patient.user else f"Patient #{patient_id}",
        "patient_id": patient_id,
        "count": len(rx_list),
        "prescriptions": rx_list
    }

