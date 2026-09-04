from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import Prescription, Patient, Doctor, User, UserRole
from app.schemas.schemas import PrescriptionCreate, PrescriptionOut
from app.api.v1.pharmacy import verify_prescription_safety, PrescriptionCheckRequest
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])


def prescription_to_out(rx: Prescription) -> PrescriptionOut:
    patient_name = rx.patient.display_name if rx.patient else None
    doctor_name = rx.doctor.user.full_name if rx.doctor and rx.doctor.user else None
    return PrescriptionOut(
        id=rx.id,
        patient_id=rx.patient_id,
        patient_name=patient_name,
        doctor_id=rx.doctor_id,
        doctor_name=doctor_name,
        appointment_id=rx.appointment_id,
        medications=rx.medications,
        instructions=rx.instructions,
        created_at=rx.created_at,
        updated_at=rx.updated_at
    )


@router.post("", response_model=PrescriptionOut, status_code=status.HTTP_201_CREATED)
def create_prescription(
    prescription_in: PrescriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    # 1. Resolve Doctor Identity
    doctor_id = None
    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile not found.")
        doctor_id = current_user.doctor_profile.id
    else:
        # Admin must associate with a doctor or default first doctor
        doc = db.query(Doctor).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No doctor available to issue prescription.")
        doctor_id = doc.id

    # 2. Verify Patient Exists
    patient = db.query(Patient).filter(Patient.id == prescription_in.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    # 3. Automated Medication Safety & Interaction Audit
    med_dumps = [m.model_dump() for m in prescription_in.medications]
    if not med_dumps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one medication is required.")

    # Extract existing active medications from patient's previous prescriptions
    past_rx = db.query(Prescription).filter(Prescription.patient_id == patient.id).all()
    active_med_names = []
    for r in past_rx:
        if isinstance(r.medications, list):
            for m in r.medications:
                if isinstance(m, dict) and "name" in m:
                    active_med_names.append(m["name"])

    # Audit primary proposed drug against active meds
    primary_med = med_dumps[0]
    audit_req = PrescriptionCheckRequest(
        proposed_drug=primary_med.get("name", ""),
        dosage=primary_med.get("dosage", ""),
        active_medications=list(set(active_med_names)),
        patient_allergies=[],
        patient_egfr=90.0
    )
    safety_audit = verify_prescription_safety(audit_req)
    if safety_audit.get("verdict") == "BLOCKED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prescription safety violation: {safety_audit.get('action_guidance')}"
        )

    # 4. Persist Prescription
    rx = Prescription(
        patient_id=prescription_in.patient_id,
        doctor_id=doctor_id,
        appointment_id=prescription_in.appointment_id,
        medications=med_dumps,
        instructions=prescription_in.instructions
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)

    # 5. Record Clinical Audit Log
    client_ip = request.client.host if request.client else None
    record_audit_log(
        db=db,
        action="PRESCRIPTION_CREATED",
        resource_type="Prescription",
        resource_id=str(rx.id),
        user_id=current_user.id,
        details={
            "patient_id": rx.patient_id,
            "doctor_id": rx.doctor_id,
            "medication_count": len(med_dumps),
            "safety_verdict": safety_audit.get("verdict")
        },
        ip_address=client_ip
    )

    return prescription_to_out(rx)


@router.get("", response_model=List[PrescriptionOut])
def list_prescriptions(
    patient_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Prescription)

    # Object-level authorization & IDOR shielding
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            return []
        query = query.filter(Prescription.patient_id == current_user.patient_profile.id)
    elif current_user.role in [UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.STAFF]:
        if patient_id:
            query = query.filter(Prescription.patient_id == patient_id)
        elif current_user.role == UserRole.DOCTOR and current_user.doctor_profile:
            query = query.filter(Prescription.doctor_id == current_user.doctor_profile.id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    prescriptions = query.order_by(Prescription.created_at.desc()).all()
    return [prescription_to_out(rx) for rx in prescriptions]


@router.get("/{prescription_id}", response_model=PrescriptionOut)
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    # IDOR Shielding
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or rx.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    elif current_user.role not in [UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return prescription_to_out(rx)


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_prescription(
    prescription_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found.")

    if current_user.role == UserRole.DOCTOR and current_user.doctor_profile:
        if rx.doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only cancel prescriptions you issued.")

    db.delete(rx)
    db.commit()

    client_ip = request.client.host if request.client else None
    record_audit_log(
        db=db,
        action="PRESCRIPTION_CANCELLED",
        resource_type="Prescription",
        resource_id=str(prescription_id),
        user_id=current_user.id,
        details={"prescription_id": prescription_id},
        ip_address=client_ip
    )
    return None
