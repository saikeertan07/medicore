from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import Patient, User, UserRole, Appointment
from app.schemas.schemas import PatientOut, PatientCreate, PatientUpdate, AppointmentOut, ClinicalTimelineEntry
from app.services.patient_service import create_patient_record
from app.services.audit_service import record_audit_log
from app.services.clinical_service import get_patient_clinical_timeline

router = APIRouter(prefix="/patients", tags=["Patients"])

def patient_to_out(patient: Patient, user_role: Optional[UserRole] = None) -> PatientOut:
    full_name = patient.full_name or (patient.user.full_name if patient.user else "Unknown")
    email = patient.email or (patient.user.email if patient.user else None)
    phone = patient.phone or (patient.user.phone if patient.user else None)
    
    # Clinical Boundary: Receptionists do NOT receive clinical history
    clinical_history = patient.medical_history_summary
    if user_role == UserRole.RECEPTIONIST:
        clinical_history = None

    return PatientOut(
        id=patient.id,
        patient_number=patient.patient_number,
        user_id=patient.user_id,
        full_name=full_name,
        email=email,
        phone=phone,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        blood_group=patient.blood_group,
        emergency_contact=patient.emergency_contact,
        address=patient.address,
        medical_history_summary=clinical_history,
        insurance_provider=patient.insurance_provider,
        insurance_policy_number=patient.insurance_policy_number,
        created_at=patient.created_at
    )

@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def register_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]))
):
    patient = create_patient_record(db=db, data=patient_in, current_user_id=current_user.id)
    return patient_to_out(patient, user_role=current_user.role)

@router.get("", response_model=List[PatientOut])
def list_patients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]))
):
    query = db.query(Patient).outerjoin(User, Patient.user_id == User.id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Patient.patient_number.ilike(pattern),
                Patient.full_name.ilike(pattern),
                Patient.email.ilike(pattern),
                Patient.phone.ilike(pattern),
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern)
            )
        )
    patients = query.order_by(Patient.id.desc()).all()
    return [patient_to_out(p, user_role=current_user.role) for p in patients]

@router.get("/{patient_id}", response_model=PatientOut)
def get_patient_profile(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to view another patient's medical profile."
            )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found.")

    return patient_to_out(patient, user_role=current_user.role)

@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot modify another patient's profile."
            )
    elif current_user.role not in [UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found.")

    update_data = patient_update.model_dump(exclude_unset=True)

    # If updating medical history summary, receptionists are NOT allowed to modify clinical notes
    if "medical_history_summary" in update_data and current_user.role == UserRole.RECEPTIONIST:
        update_data.pop("medical_history_summary")

    for field, val in update_data.items():
        setattr(patient, field, val)

    db.commit()
    db.refresh(patient)

    record_audit_log(
        db=db,
        action="PATIENT_PROFILE_UPDATE",
        resource_type="Patient",
        resource_id=str(patient.id),
        user_id=current_user.id,
        details={"updated_fields": list(update_data.keys())}
    )

    return patient_to_out(patient, user_role=current_user.role)

@router.get("/{patient_id}/appointments", response_model=List[AppointmentOut])
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view another patient's appointments."
            )
    elif current_user.role not in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.RECEPTIONIST, UserRole.NURSE, UserRole.STAFF]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")

    appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.date.desc(), Appointment.start_time.desc()).all()
    
    out = []
    for appt in appointments:
        out.append(AppointmentOut(
            id=appt.id,
            appointment_number=appt.appointment_number,
            patient_id=appt.patient_id,
            patient_name=appt.patient.display_name if appt.patient else None,
            doctor_id=appt.doctor_id,
            doctor_name=appt.doctor.user.full_name if appt.doctor and appt.doctor.user else None,
            doctor_specialization=appt.doctor.specialization if appt.doctor else None,
            department_id=appt.department_id,
            department_name=appt.department.name if appt.department else None,
            date=appt.date,
            start_time=appt.start_time,
            end_time=appt.end_time,
            type=appt.type,
            status=appt.status,
            check_in_time=appt.check_in_time,
            reason=appt.reason,
            notes=appt.notes,
            created_at=appt.created_at,
            updated_at=appt.updated_at
        ))
    return out

@router.get("/{patient_id}/clinical-timeline", response_model=List[ClinicalTimelineEntry])
def fetch_patient_clinical_timeline(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the authoritative longitudinal clinical timeline for a patient.
    - RECEPTIONIST: 403 Forbidden.
    - PATIENT: Only allowed for own patient_id. Draft notes hidden.
    - DOCTOR / NURSE / ADMIN: Authorized access.
    """
    client_ip = request.client.host if request.client else None
    return get_patient_clinical_timeline(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        ip_address=client_ip
    )
