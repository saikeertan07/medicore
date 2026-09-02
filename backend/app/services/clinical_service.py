import uuid
from datetime import datetime, date
from app.core.datetime_utils import utc_now
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from fastapi import HTTPException, status

from app.models.models import (
    Encounter, EncounterVitals, ClinicalNote, ClinicalDiagnosis,
    EncounterStatus, EncounterType, ClinicalNoteStatus, DiagnosisType,
    Appointment, AppointmentStatus, Patient, Doctor, User, UserRole
)
from app.schemas.schemas import (
    EncounterCreate, VitalsCreate, VitalsUpdate, ClinicalNoteCreate,
    ClinicalNoteUpdate, ClinicalNoteAmend, DiagnosisCreate, ClinicalTimelineEntry
)
from app.services.audit_service import record_audit_log

ALLOWED_ENCOUNTER_TRANSITIONS = {
    EncounterStatus.OPEN: [EncounterStatus.IN_PROGRESS, EncounterStatus.CANCELLED],
    EncounterStatus.IN_PROGRESS: [EncounterStatus.COMPLETED, EncounterStatus.CANCELLED],
    EncounterStatus.COMPLETED: [],
    EncounterStatus.CANCELLED: [],
}

def generate_encounter_number(db: Session) -> str:
    """Generates a collision-resistant server-side encounter number: ENC-YYYYMM-XXXXXX"""
    now_str = utc_now().strftime("%Y%m")
    for _ in range(10):
        rand_hex = uuid.uuid4().hex[:6].upper()
        candidate = f"ENC-{now_str}-{rand_hex}"
        exists = db.query(Encounter).filter(Encounter.encounter_number == candidate).first()
        if not exists:
            return candidate
    return f"ENC-{now_str}-{uuid.uuid4().hex[:8].upper()}"

def calculate_bmi(height_cm: Optional[Any], weight_kg: Optional[Any]) -> Optional[float]:
    """Authoritative server-side BMI calculation: weight(kg) / (height(m))^2."""
    if height_cm is not None and weight_kg is not None:
        try:
            h = float(height_cm)
            w = float(weight_kg)
            if h > 0 and w > 0:
                height_m = h / 100.0
                return round(w / (height_m ** 2), 1)
        except (ValueError, TypeError):
            return None
    return None

def validate_vitals_values(vitals_data: VitalsCreate) -> None:
    """Validates clinical ranges and physiological consistency."""
    if vitals_data.systolic_bp is not None and vitals_data.diastolic_bp is not None:
        if vitals_data.systolic_bp <= vitals_data.diastolic_bp:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Systolic blood pressure ({vitals_data.systolic_bp}) must be greater than diastolic blood pressure ({vitals_data.diastolic_bp})."
            )

def create_encounter(
    db: Session,
    data: EncounterCreate,
    current_user: User,
    ip_address: Optional[str] = None
) -> Encounter:
    """Creates an encounter with strict relationship and uniqueness checks."""
    # Enforce role-specific creation rules: NURSE and DOCTOR only
    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or data.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Doctors can only create encounters where they are the attending doctor."
            )
    elif current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Nurse is not assigned to a department."
            )
        if data.department_id and current_user.staff_profile.department_id != data.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Nurses can only create encounters for their assigned department."
            )
    elif current_user.role not in [UserRole.DOCTOR, UserRole.NURSE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only nurses and doctors can create clinical encounters."
        )

    # 1. Verify Patient
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient ID {data.patient_id} not found.")

    # 2. Verify Doctor
    doctor = db.query(Doctor).filter(Doctor.id == data.attending_doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Doctor ID {data.attending_doctor_id} not found.")
    if not doctor.user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attending doctor is currently inactive.")

    # 3. If linked to an appointment, verify integrity
    appointment = None
    if data.appointment_id:
        appointment = db.query(Appointment).filter(Appointment.id == data.appointment_id).first()
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Appointment ID {data.appointment_id} not found.")
        
        if appointment.patient_id != data.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointment patient ID ({appointment.patient_id}) does not match encounter patient ID ({data.patient_id})."
            )
        if appointment.doctor_id != data.attending_doctor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointment doctor ID ({appointment.doctor_id}) does not match attending doctor ID ({data.attending_doctor_id})."
            )
        if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create encounter for an appointment that is {appointment.status.value}."
            )

        # Enforce single primary clinical encounter per appointment
        existing_enc = db.query(Encounter).filter(Encounter.appointment_id == data.appointment_id).first()
        if existing_enc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Appointment {appointment.appointment_number} already has an associated encounter ({existing_enc.encounter_number})."
            )

    dept_id = data.department_id or (current_user.staff_profile.department_id if current_user.role == UserRole.NURSE and current_user.staff_profile else doctor.department_id)

    encounter = Encounter(
        encounter_number=generate_encounter_number(db),
        patient_id=data.patient_id,
        appointment_id=data.appointment_id,
        attending_doctor_id=data.attending_doctor_id,
        department_id=dept_id,
        encounter_type=data.encounter_type,
        status=EncounterStatus.OPEN,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(encounter)
    db.commit()
    db.refresh(encounter)

    record_audit_log(
        db=db,
        action="ENCOUNTER_CREATE",
        resource_type="Encounter",
        resource_id=str(encounter.id),
        user_id=current_user.id,
        details={
            "encounter_number": encounter.encounter_number,
            "patient_id": encounter.patient_id,
            "attending_doctor_id": encounter.attending_doctor_id,
            "appointment_id": encounter.appointment_id,
            "encounter_type": encounter.encounter_type.value
        },
        ip_address=ip_address
    )
    return encounter

def start_encounter(
    db: Session,
    encounter_id: int,
    current_user: User,
    ip_address: Optional[str] = None
) -> Encounter:
    """Transitions encounter from OPEN to IN_PROGRESS and syncs linked appointment."""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or encounter.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not the attending doctor for this encounter."
            )
    elif current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or encounter.department_id != current_user.staff_profile.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Encounter is outside your assigned department."
            )

    if encounter.status == EncounterStatus.IN_PROGRESS:
        return encounter  # Idempotent

    valid_targets = ALLOWED_ENCOUNTER_TRANSITIONS.get(encounter.status, [])
    if EncounterStatus.IN_PROGRESS not in valid_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start encounter with current status {encounter.status.value}."
        )

    encounter.status = EncounterStatus.IN_PROGRESS
    encounter.started_at = utc_now()
    encounter.updated_at = utc_now()

    # Sync appointment status if linked and checked in
    if encounter.appointment and encounter.appointment.status == AppointmentStatus.CHECKED_IN:
        encounter.appointment.status = AppointmentStatus.IN_PROGRESS
        encounter.appointment.updated_at = utc_now()

    db.commit()
    db.refresh(encounter)

    record_audit_log(
        db=db,
        action="ENCOUNTER_START",
        resource_type="Encounter",
        resource_id=str(encounter.id),
        user_id=current_user.id,
        details={"encounter_number": encounter.encounter_number},
        ip_address=ip_address
    )
    return encounter

def complete_encounter(
    db: Session,
    encounter_id: int,
    current_user: User,
    ip_address: Optional[str] = None
) -> Encounter:
    """Transitions encounter from IN_PROGRESS to COMPLETED and syncs appointment."""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or encounter.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not the attending doctor for this encounter."
            )

    if encounter.status == EncounterStatus.COMPLETED:
        return encounter  # Idempotent

    valid_targets = ALLOWED_ENCOUNTER_TRANSITIONS.get(encounter.status, [])
    if EncounterStatus.COMPLETED not in valid_targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete encounter with current status {encounter.status.value}."
        )

    encounter.status = EncounterStatus.COMPLETED
    encounter.completed_at = utc_now()
    encounter.updated_at = utc_now()

    # Sync appointment to COMPLETED if linked
    if encounter.appointment and encounter.appointment.status == AppointmentStatus.IN_PROGRESS:
        encounter.appointment.status = AppointmentStatus.COMPLETED
        encounter.appointment.updated_at = utc_now()

    db.commit()
    db.refresh(encounter)

    record_audit_log(
        db=db,
        action="ENCOUNTER_COMPLETE",
        resource_type="Encounter",
        resource_id=str(encounter.id),
        user_id=current_user.id,
        details={"encounter_number": encounter.encounter_number},
        ip_address=ip_address
    )
    return encounter

def record_encounter_vitals(
    db: Session,
    encounter_id: int,
    vitals_in: VitalsCreate,
    current_user: User,
    ip_address: Optional[str] = None
) -> EncounterVitals:
    """Creates a vitals record for an encounter with server-side BMI calculation."""
    if current_user.role not in [UserRole.NURSE, UserRole.DOCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only nurses and doctors can record clinical vitals."
        )

    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or encounter.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not the attending doctor for this encounter."
            )
    elif current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or encounter.department_id != current_user.staff_profile.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only record vitals for encounters in your assigned department."
            )

    validate_vitals_values(vitals_in)
    calculated_bmi = calculate_bmi(vitals_in.height_cm, vitals_in.weight_kg)

    vitals = EncounterVitals(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        recorded_by_id=current_user.id,
        temperature_c=vitals_in.temperature_c,
        heart_rate=vitals_in.heart_rate,
        respiratory_rate=vitals_in.respiratory_rate,
        systolic_bp=vitals_in.systolic_bp,
        diastolic_bp=vitals_in.diastolic_bp,
        oxygen_saturation=vitals_in.oxygen_saturation,
        height_cm=vitals_in.height_cm,
        weight_kg=vitals_in.weight_kg,
        bmi=calculated_bmi,
        pain_score=vitals_in.pain_score,
        notes=vitals_in.notes,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(vitals)
    db.commit()
    db.refresh(vitals)

    record_audit_log(
        db=db,
        action="VITALS_CREATE",
        resource_type="EncounterVitals",
        resource_id=str(vitals.id),
        user_id=current_user.id,
        details={
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "bmi": calculated_bmi
        },
        ip_address=ip_address
    )
    return vitals

def update_encounter_vitals(
    db: Session,
    vitals_id: int,
    vitals_in: VitalsUpdate,
    current_user: User,
    ip_address: Optional[str] = None
) -> EncounterVitals:
    """Updates an existing vitals record."""
    if current_user.role not in [UserRole.NURSE, UserRole.DOCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only nurses and doctors can update clinical vitals."
        )

    vitals = db.query(EncounterVitals).filter(EncounterVitals.id == vitals_id).first()
    if not vitals:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vitals record not found.")

    encounter = vitals.encounter
    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or encounter.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not the attending doctor for this encounter."
            )
    elif current_user.role == UserRole.NURSE:
        is_author = (vitals.recorded_by_id == current_user.id)
        is_dept_nurse = bool(
            current_user.staff_profile and
            current_user.staff_profile.department_id and
            encounter.department_id == current_user.staff_profile.department_id
        )
        if not (is_author or is_dept_nurse):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not authorized to update these vitals."
            )

    validate_vitals_values(vitals_in)

    update_dict = vitals_in.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(vitals, field, val)

    vitals.bmi = calculate_bmi(vitals.height_cm, vitals.weight_kg)
    vitals.updated_at = utc_now()

    db.commit()
    db.refresh(vitals)

    record_audit_log(
        db=db,
        action="VITALS_UPDATE",
        resource_type="EncounterVitals",
        resource_id=str(vitals.id),
        user_id=current_user.id,
        details={"updated_fields": list(update_dict.keys())},
        ip_address=ip_address
    )
    return vitals

def create_clinical_note(
    db: Session,
    encounter_id: int,
    note_in: ClinicalNoteCreate,
    current_user: User,
    ip_address: Optional[str] = None
) -> ClinicalNote:
    """Creates a doctor clinical note in DRAFT status."""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if not current_user.doctor_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only verified doctors can author clinical notes.")

    doctor = current_user.doctor_profile
    if encounter.attending_doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not the attending doctor for this encounter."
        )

    note = ClinicalNote(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        doctor_id=doctor.id,
        author_id=current_user.id,
        status=ClinicalNoteStatus.DRAFT,
        version=1,
        chief_complaint=note_in.chief_complaint,
        history_of_present_illness=note_in.history_of_present_illness,
        symptoms=note_in.symptoms,
        medical_history_notes=note_in.medical_history_notes,
        examination_findings=note_in.examination_findings,
        vitals_summary=note_in.vitals_summary,
        observations=note_in.observations,
        clinical_assessment=note_in.clinical_assessment,
        differential_diagnosis=note_in.differential_diagnosis,
        treatment_plan=note_in.treatment_plan,
        patient_instructions=note_in.patient_instructions,
        follow_up_instructions=note_in.follow_up_instructions,
        follow_up_date=note_in.follow_up_date,
        recommendations=note_in.recommendations,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    record_audit_log(
        db=db,
        action="CLINICAL_NOTE_CREATE",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        user_id=current_user.id,
        details={
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "status": note.status.value,
            "version": note.version
        },
        ip_address=ip_address
    )
    return note

def update_clinical_note(
    db: Session,
    note_id: int,
    note_in: ClinicalNoteUpdate,
    current_user: User,
    ip_address: Optional[str] = None
) -> ClinicalNote:
    """Updates a DRAFT clinical note. Finalized notes are strictly immutable to direct PUT."""
    note = db.query(ClinicalNote).filter(ClinicalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found.")

    # Only authoring doctor can edit draft
    if note.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the authoring doctor can modify this clinical draft."
        )

    # Immutability check
    if note.status in [ClinicalNoteStatus.FINAL, ClinicalNoteStatus.AMENDED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot directly modify a {note.status.value} clinical note. Use the amendment mechanism."
        )

    update_dict = note_in.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(note, field, val)

    note.updated_at = utc_now()
    db.commit()
    db.refresh(note)

    record_audit_log(
        db=db,
        action="CLINICAL_NOTE_UPDATE",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        user_id=current_user.id,
        details={"updated_fields": list(update_dict.keys())},
        ip_address=ip_address
    )
    return note

def finalize_clinical_note(
    db: Session,
    note_id: int,
    current_user: User,
    ip_address: Optional[str] = None
) -> ClinicalNote:
    """
    Transaction-safe finalization of a DRAFT clinical note into FINAL.
    Uses row-level locking / conditional update to guarantee that concurrent
    finalization requests do not create duplicate finalization states.
    """
    # Use with_for_update if in postgres
    is_postgres = db.bind and db.bind.dialect.name == "postgresql"
    query = db.query(ClinicalNote).filter(ClinicalNote.id == note_id)
    if is_postgres:
        query = query.with_for_update()

    note = query.first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found.")

    if note.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the authoring doctor can finalize this note."
        )

    if note.status == ClinicalNoteStatus.FINAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This clinical note has already been finalized."
        )

    if note.status != ClinicalNoteStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot finalize note with status {note.status.value}."
        )

    note.status = ClinicalNoteStatus.FINAL
    note.finalized_at = utc_now()
    note.updated_at = utc_now()

    db.commit()
    db.refresh(note)

    record_audit_log(
        db=db,
        action="CLINICAL_NOTE_FINALIZE",
        resource_type="ClinicalNote",
        resource_id=str(note.id),
        user_id=current_user.id,
        details={
            "encounter_id": note.encounter_id,
            "version": note.version,
            "finalized_at": str(note.finalized_at)
        },
        ip_address=ip_address
    )
    return note

def amend_clinical_note(
    db: Session,
    note_id: int,
    amend_in: ClinicalNoteAmend,
    current_user: User,
    ip_address: Optional[str] = None
) -> ClinicalNote:
    """
    Creates an attributable versioned amendment for a finalized note.
    Preserves original note immutable; creates note v(N+1) linked to parent_note_id.
    """
    is_postgres = db.bind and db.bind.dialect.name == "postgresql"
    query = db.query(ClinicalNote).filter(ClinicalNote.id == note_id)
    if is_postgres:
        query = query.with_for_update()

    original_note = query.first()
    if not original_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found.")

    if not current_user.doctor_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can amend clinical records.")

    if original_note.encounter.attending_doctor_id != current_user.doctor_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not the attending doctor for this encounter."
        )

    if original_note.status != ClinicalNoteStatus.FINAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only FINAL notes can be amended (current status: {original_note.status.value})."
        )

    # Mark original note as AMENDED
    original_note.status = ClinicalNoteStatus.AMENDED
    original_note.updated_at = utc_now()

    # Create new versioned note (FINAL directly upon amendment)
    now = utc_now()
    new_version_note = ClinicalNote(
        encounter_id=original_note.encounter_id,
        patient_id=original_note.patient_id,
        doctor_id=current_user.doctor_profile.id,
        author_id=current_user.id,
        status=ClinicalNoteStatus.FINAL,
        version=original_note.version + 1,
        parent_note_id=original_note.id,
        chief_complaint=amend_in.chief_complaint if amend_in.chief_complaint is not None else original_note.chief_complaint,
        history_of_present_illness=amend_in.history_of_present_illness if amend_in.history_of_present_illness is not None else original_note.history_of_present_illness,
        symptoms=amend_in.symptoms if amend_in.symptoms is not None else original_note.symptoms,
        medical_history_notes=amend_in.medical_history_notes if amend_in.medical_history_notes is not None else original_note.medical_history_notes,
        examination_findings=amend_in.examination_findings if amend_in.examination_findings is not None else original_note.examination_findings,
        vitals_summary=amend_in.vitals_summary if amend_in.vitals_summary is not None else original_note.vitals_summary,
        observations=amend_in.observations if amend_in.observations is not None else original_note.observations,
        clinical_assessment=amend_in.clinical_assessment if amend_in.clinical_assessment is not None else original_note.clinical_assessment,
        differential_diagnosis=amend_in.differential_diagnosis if amend_in.differential_diagnosis is not None else original_note.differential_diagnosis,
        treatment_plan=amend_in.treatment_plan if amend_in.treatment_plan is not None else original_note.treatment_plan,
        patient_instructions=amend_in.patient_instructions if amend_in.patient_instructions is not None else original_note.patient_instructions,
        follow_up_instructions=amend_in.follow_up_instructions if amend_in.follow_up_instructions is not None else original_note.follow_up_instructions,
        follow_up_date=amend_in.follow_up_date if amend_in.follow_up_date is not None else original_note.follow_up_date,
        recommendations=amend_in.recommendations if amend_in.recommendations is not None else original_note.recommendations,
        created_at=now,
        updated_at=now,
        finalized_at=now,
        amended_at=now,
        amendment_reason=amend_in.amendment_reason
    )
    db.add(new_version_note)
    db.commit()
    db.refresh(new_version_note)

    record_audit_log(
        db=db,
        action="CLINICAL_NOTE_AMEND",
        resource_type="ClinicalNote",
        resource_id=str(new_version_note.id),
        user_id=current_user.id,
        details={
            "original_note_id": original_note.id,
            "new_version": new_version_note.version,
            "amendment_reason": amend_in.amendment_reason
        },
        ip_address=ip_address
    )
    return new_version_note

def create_clinical_diagnosis(
    db: Session,
    encounter_id: int,
    diag_in: DiagnosisCreate,
    current_user: User,
    ip_address: Optional[str] = None
) -> ClinicalDiagnosis:
    """Creates a structured diagnosis authored by a doctor."""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if not current_user.doctor_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can add diagnoses.")

    doctor = current_user.doctor_profile
    if encounter.attending_doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not the attending doctor for this encounter."
        )

    diagnosis = ClinicalDiagnosis(
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        doctor_id=doctor.id,
        name=diag_in.name,
        code=diag_in.code,
        code_system=diag_in.code_system,
        type=diag_in.type,
        notes=diag_in.notes,
        created_at=utc_now()
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    record_audit_log(
        db=db,
        action="DIAGNOSIS_CREATE",
        resource_type="ClinicalDiagnosis",
        resource_id=str(diagnosis.id),
        user_id=current_user.id,
        details={
            "encounter_id": encounter.id,
            "patient_id": encounter.patient_id,
            "diagnosis_name": diagnosis.name,
            "type": diagnosis.type.value
        },
        ip_address=ip_address
    )
    return diagnosis

def get_patient_clinical_timeline(
    db: Session,
    patient_id: int,
    current_user: User,
    ip_address: Optional[str] = None
) -> List[ClinicalTimelineEntry]:
    """
    Builds the authoritative longitudinal clinical timeline for a patient.
    Strictly enforces clinical access control:
    - Receptionist: FORBIDDEN (403).
    - Patient: Can ONLY view self. Draft doctor notes and internal notes are omitted.
    - Doctor: Can view if authorized clinical relationship exists.
    """
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Receptionists are not authorized to view clinical records."
        )

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view another patient's clinical timeline."
            )

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found.")
        has_attending_encounter = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.attending_doctor_id == current_user.doctor_profile.id
        ).first() is not None
        if not has_attending_encounter:
            has_appt = db.query(Appointment).filter(
                Appointment.patient_id == patient_id,
                Appointment.doctor_id == current_user.doctor_profile.id
            ).first() is not None
            if not has_appt:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not have an active attending clinical relationship with this patient."
                )

    elif current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Nurse is not assigned to a department."
            )
        has_dept_encounter = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.department_id == current_user.staff_profile.department_id
        ).first() is not None
        if not has_dept_encounter:
            has_dept_appt = db.query(Appointment).filter(
                Appointment.patient_id == patient_id,
                Appointment.department_id == current_user.staff_profile.department_id
            ).first() is not None
            if not has_dept_appt:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Patient has no clinical records in your assigned department."
                )

    elif current_user.role not in [UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.PATIENT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not authorized to view clinical records."
        )

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    timeline: List[ClinicalTimelineEntry] = []

    # 1. Encounters
    encounters = db.query(Encounter).filter(Encounter.patient_id == patient_id).all()
    for enc in encounters:
        timeline.append(ClinicalTimelineEntry(
            date=enc.created_at,
            entry_type="ENCOUNTER",
            encounter_id=enc.id,
            encounter_number=enc.encounter_number,
            doctor_name=enc.attending_doctor.user.full_name if enc.attending_doctor and enc.attending_doctor.user else None,
            department_name=enc.department.name if enc.department else None,
            summary=f"Clinical Encounter ({enc.encounter_type.value}) - Status: {enc.status.value}",
            details={
                "status": enc.status.value,
                "type": enc.encounter_type.value,
                "started_at": str(enc.started_at) if enc.started_at else None,
                "completed_at": str(enc.completed_at) if enc.completed_at else None
            }
        ))

    # 2. Vitals
    vitals_records = db.query(EncounterVitals).filter(EncounterVitals.patient_id == patient_id).all()
    for vit in vitals_records:
        summary_parts = []
        if vit.temperature_c: summary_parts.append(f"Temp: {vit.temperature_c}°C")
        if vit.heart_rate: summary_parts.append(f"HR: {vit.heart_rate} bpm")
        if vit.systolic_bp and vit.diastolic_bp: summary_parts.append(f"BP: {vit.systolic_bp}/{vit.diastolic_bp}")
        if vit.oxygen_saturation: summary_parts.append(f"SpO2: {vit.oxygen_saturation}%")
        if vit.bmi: summary_parts.append(f"BMI: {vit.bmi}")

        timeline.append(ClinicalTimelineEntry(
            date=vit.created_at,
            entry_type="VITALS",
            encounter_id=vit.encounter_id,
            encounter_number=vit.encounter.encounter_number if vit.encounter else "",
            doctor_name=vit.recorded_by.full_name if vit.recorded_by else None,
            department_name=vit.encounter.department.name if vit.encounter and vit.encounter.department else None,
            summary="Vitals Intake: " + (", ".join(summary_parts) or "Recorded"),
            details={
                "temperature_c": float(vit.temperature_c) if vit.temperature_c else None,
                "heart_rate": vit.heart_rate,
                "respiratory_rate": vit.respiratory_rate,
                "systolic_bp": vit.systolic_bp,
                "diastolic_bp": vit.diastolic_bp,
                "oxygen_saturation": float(vit.oxygen_saturation) if vit.oxygen_saturation else None,
                "bmi": float(vit.bmi) if vit.bmi else None,
                "pain_score": vit.pain_score,
                "notes": vit.notes
            }
        ))

    # 3. Clinical Notes (Patients only see FINAL / AMENDED; drafts only shown to authoring doctor)
    notes_query = db.query(ClinicalNote).filter(ClinicalNote.patient_id == patient_id)
    if current_user.role == UserRole.PATIENT:
        notes_query = notes_query.filter(ClinicalNote.status.in_([ClinicalNoteStatus.FINAL, ClinicalNoteStatus.AMENDED]))
    notes = notes_query.all()

    for n in notes:
        # If user is a doctor but not author, hide drafts
        if n.status == ClinicalNoteStatus.DRAFT and current_user.role == UserRole.DOCTOR and n.author_id != current_user.id:
            continue

        timeline.append(ClinicalTimelineEntry(
            date=n.created_at,
            entry_type="CLINICAL_NOTE",
            encounter_id=n.encounter_id,
            encounter_number=n.encounter.encounter_number if n.encounter else "",
            doctor_name=n.doctor.user.full_name if n.doctor and n.doctor.user else None,
            department_name=n.encounter.department.name if n.encounter and n.encounter.department else None,
            summary=f"Doctor Clinical Note v{n.version} ({n.status.value})",
            details={
                "status": n.status.value,
                "version": n.version,
                "chief_complaint": n.chief_complaint,
                "assessment": n.clinical_assessment,
                "treatment_plan": n.treatment_plan,
                "patient_instructions": n.patient_instructions,
                "follow_up_instructions": n.follow_up_instructions,
                "follow_up_date": str(n.follow_up_date) if n.follow_up_date else None,
                "amendment_reason": n.amendment_reason
            }
        ))

    # 4. Diagnoses
    diagnoses = db.query(ClinicalDiagnosis).filter(ClinicalDiagnosis.patient_id == patient_id).all()
    for d in diagnoses:
        timeline.append(ClinicalTimelineEntry(
            date=d.created_at,
            entry_type="DIAGNOSIS",
            encounter_id=d.encounter_id,
            encounter_number=d.encounter.encounter_number if d.encounter else "",
            doctor_name=d.doctor.user.full_name if d.doctor and d.doctor.user else None,
            department_name=d.encounter.department.name if d.encounter and d.encounter.department else None,
            summary=f"Diagnosis ({d.type.value}): {d.name}",
            details={
                "name": d.name,
                "code": d.code,
                "code_system": d.code_system,
                "type": d.type.value,
                "notes": d.notes
            }
        ))

    # Sort descending by date
    timeline.sort(key=lambda x: x.date, reverse=True)

    record_audit_log(
        db=db,
        action="CLINICAL_TIMELINE_ACCESS",
        resource_type="Patient",
        resource_id=str(patient_id),
        user_id=current_user.id,
        details={"entries_count": len(timeline)},
        ip_address=ip_address
    )
    return timeline
