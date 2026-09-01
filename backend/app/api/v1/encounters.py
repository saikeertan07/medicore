from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import (
    Encounter, EncounterVitals, ClinicalNote, ClinicalDiagnosis,
    User, UserRole, ClinicalNoteStatus, Patient
)
from app.schemas.schemas import (
    EncounterCreate, EncounterOut, VitalsCreate, VitalsUpdate, VitalsOut,
    ClinicalNoteCreate, ClinicalNoteUpdate, ClinicalNoteAmend, ClinicalNoteOut,
    DiagnosisCreate, DiagnosisOut
)
from app.services.clinical_service import (
    create_encounter, start_encounter, complete_encounter,
    record_encounter_vitals, update_encounter_vitals,
    create_clinical_note, update_clinical_note, finalize_clinical_note,
    amend_clinical_note, create_clinical_diagnosis
)

router = APIRouter(tags=["Clinical Documentation & EMR"])

def encounter_to_out(enc: Encounter) -> EncounterOut:
    return EncounterOut(
        id=enc.id,
        encounter_number=enc.encounter_number,
        patient_id=enc.patient_id,
        patient_name=enc.patient.display_name if enc.patient else None,
        appointment_id=enc.appointment_id,
        appointment_number=enc.appointment.appointment_number if enc.appointment else None,
        attending_doctor_id=enc.attending_doctor_id,
        doctor_name=enc.attending_doctor.user.full_name if enc.attending_doctor and enc.attending_doctor.user else None,
        department_id=enc.department_id,
        department_name=enc.department.name if enc.department else None,
        encounter_type=enc.encounter_type,
        status=enc.status,
        started_at=enc.started_at,
        completed_at=enc.completed_at,
        created_at=enc.created_at,
        updated_at=enc.updated_at
    )

def vitals_to_out(vit: EncounterVitals) -> VitalsOut:
    return VitalsOut(
        id=vit.id,
        encounter_id=vit.encounter_id,
        patient_id=vit.patient_id,
        recorded_by_id=vit.recorded_by_id,
        recorded_by_name=vit.recorded_by.full_name if vit.recorded_by else None,
        temperature_c=float(vit.temperature_c) if vit.temperature_c is not None else None,
        heart_rate=vit.heart_rate,
        respiratory_rate=vit.respiratory_rate,
        systolic_bp=vit.systolic_bp,
        diastolic_bp=vit.diastolic_bp,
        oxygen_saturation=float(vit.oxygen_saturation) if vit.oxygen_saturation is not None else None,
        height_cm=float(vit.height_cm) if vit.height_cm is not None else None,
        weight_kg=float(vit.weight_kg) if vit.weight_kg is not None else None,
        bmi=float(vit.bmi) if vit.bmi is not None else None,
        pain_score=vit.pain_score,
        notes=vit.notes,
        created_at=vit.created_at,
        updated_at=vit.updated_at
    )

def note_to_out(note: ClinicalNote) -> ClinicalNoteOut:
    return ClinicalNoteOut(
        id=note.id,
        encounter_id=note.encounter_id,
        patient_id=note.patient_id,
        doctor_id=note.doctor_id,
        doctor_name=note.doctor.user.full_name if note.doctor and note.doctor.user else None,
        author_id=note.author_id,
        author_name=note.author.full_name if note.author else None,
        status=note.status,
        version=note.version,
        parent_note_id=note.parent_note_id,
        chief_complaint=note.chief_complaint,
        history_of_present_illness=note.history_of_present_illness,
        symptoms=note.symptoms,
        medical_history_notes=note.medical_history_notes,
        examination_findings=note.examination_findings,
        vitals_summary=note.vitals_summary,
        observations=note.observations,
        clinical_assessment=note.clinical_assessment,
        differential_diagnosis=note.differential_diagnosis,
        treatment_plan=note.treatment_plan,
        patient_instructions=note.patient_instructions,
        follow_up_instructions=note.follow_up_instructions,
        follow_up_date=note.follow_up_date,
        recommendations=note.recommendations,
        created_at=note.created_at,
        updated_at=note.updated_at,
        finalized_at=note.finalized_at,
        amended_at=note.amended_at,
        amendment_reason=note.amendment_reason
    )

def diagnosis_to_out(diag: ClinicalDiagnosis) -> DiagnosisOut:
    return DiagnosisOut(
        id=diag.id,
        encounter_id=diag.encounter_id,
        patient_id=diag.patient_id,
        doctor_id=diag.doctor_id,
        doctor_name=diag.doctor.user.full_name if diag.doctor and diag.doctor.user else None,
        name=diag.name,
        code=diag.code,
        code_system=diag.code_system,
        type=diag.type,
        notes=diag.notes,
        created_at=diag.created_at
    )

# ==========================================
# 1. ENCOUNTERS
# ==========================================

@router.post("/encounters", response_model=EncounterOut, status_code=status.HTTP_201_CREATED)
def create_new_encounter(
    enc_in: EncounterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE]))
):
    client_ip = request.client.host if request.client else None
    enc = create_encounter(db=db, data=enc_in, current_user=current_user, ip_address=client_ip)
    return encounter_to_out(enc)

@router.get("/encounters/{encounter_id}", response_model=EncounterOut)
def get_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Receptionists cannot access clinical encounters.")

    enc = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not enc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or enc.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You cannot view another patient's encounter.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or enc.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You are not authorized to view this encounter.")

    if current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or enc.department_id != current_user.staff_profile.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Encounter is outside your assigned department.")

    return encounter_to_out(enc)

@router.get("/patients/{patient_id}/encounters", response_model=List[EncounterOut])
def list_patient_encounters(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Receptionists cannot access clinical encounters.")

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You cannot view another patient's encounters.")

    query = db.query(Encounter).filter(Encounter.patient_id == patient_id)
    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found.")
        query = query.filter(Encounter.attending_doctor_id == current_user.doctor_profile.id)
    elif current_user.role == UserRole.NURSE:
        if current_user.staff_profile and current_user.staff_profile.department_id:
            query = query.filter(Encounter.department_id == current_user.staff_profile.department_id)

    encounters = query.order_by(Encounter.created_at.desc()).all()
    return [encounter_to_out(e) for e in encounters]

@router.post("/encounters/{encounter_id}/start", response_model=EncounterOut)
def start_clinical_encounter(
    encounter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN]))
):
    client_ip = request.client.host if request.client else None
    enc = start_encounter(db=db, encounter_id=encounter_id, current_user=current_user, ip_address=client_ip)
    return encounter_to_out(enc)

@router.post("/encounters/{encounter_id}/complete", response_model=EncounterOut)
def complete_clinical_encounter(
    encounter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    client_ip = request.client.host if request.client else None
    enc = complete_encounter(db=db, encounter_id=encounter_id, current_user=current_user, ip_address=client_ip)
    return encounter_to_out(enc)

# ==========================================
# 2. VITALS / INTAKE
# ==========================================

@router.post("/encounters/{encounter_id}/vitals", response_model=VitalsOut, status_code=status.HTTP_201_CREATED)
def record_vitals(
    encounter_id: int,
    vitals_in: VitalsCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.NURSE, UserRole.DOCTOR]))
):
    client_ip = request.client.host if request.client else None
    vit = record_encounter_vitals(
        db=db,
        encounter_id=encounter_id,
        vitals_in=vitals_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return vitals_to_out(vit)

@router.get("/encounters/{encounter_id}/vitals", response_model=List[VitalsOut])
def get_encounter_vitals(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Receptionists cannot access clinical vitals.")

    enc = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not enc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or enc.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You cannot view another patient's vitals.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or enc.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You are not authorized to view vitals for this encounter.")

    if current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or enc.department_id != current_user.staff_profile.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Encounter is outside your assigned department.")

    vitals_list = db.query(EncounterVitals).filter(EncounterVitals.encounter_id == encounter_id).order_by(EncounterVitals.created_at.desc()).all()
    return [vitals_to_out(v) for v in vitals_list]

@router.put("/vitals/{vitals_id}", response_model=VitalsOut)
def update_vitals(
    vitals_id: int,
    vitals_in: VitalsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.NURSE, UserRole.DOCTOR]))
):
    client_ip = request.client.host if request.client else None
    vit = update_encounter_vitals(
        db=db,
        vitals_id=vitals_id,
        vitals_in=vitals_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return vitals_to_out(vit)

# ==========================================
# 3. CLINICAL NOTES
# ==========================================

@router.post("/encounters/{encounter_id}/clinical-notes", response_model=ClinicalNoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    encounter_id: int,
    note_in: ClinicalNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR]))
):
    client_ip = request.client.host if request.client else None
    note = create_clinical_note(
        db=db,
        encounter_id=encounter_id,
        note_in=note_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return note_to_out(note)

@router.get("/encounters/{encounter_id}/clinical-notes", response_model=List[ClinicalNoteOut])
def get_encounter_notes(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Receptionists cannot access clinical notes.")

    enc = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not enc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or enc.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        # Patients only see FINAL or AMENDED notes
        notes = db.query(ClinicalNote).filter(
            ClinicalNote.encounter_id == encounter_id,
            ClinicalNote.status.in_([ClinicalNoteStatus.FINAL, ClinicalNoteStatus.AMENDED])
        ).order_by(ClinicalNote.version.asc()).all()
        return [note_to_out(n) for n in notes]

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or enc.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You are not authorized to view clinical notes for this encounter.")

    if current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or enc.department_id != current_user.staff_profile.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Encounter is outside your assigned department.")

    notes = db.query(ClinicalNote).filter(ClinicalNote.encounter_id == encounter_id).order_by(ClinicalNote.version.asc()).all()
    # Filter out drafts of other doctors unless admin
    out = []
    for n in notes:
        if n.status == ClinicalNoteStatus.DRAFT and current_user.role == UserRole.DOCTOR and n.author_id != current_user.id:
            continue
        out.append(note_to_out(n))
    return out

@router.put("/clinical-notes/{note_id}", response_model=ClinicalNoteOut)
def update_note(
    note_id: int,
    note_in: ClinicalNoteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    client_ip = request.client.host if request.client else None
    note = update_clinical_note(
        db=db,
        note_id=note_id,
        note_in=note_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return note_to_out(note)

@router.post("/clinical-notes/{note_id}/finalize", response_model=ClinicalNoteOut)
def finalize_note(
    note_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    client_ip = request.client.host if request.client else None
    note = finalize_clinical_note(
        db=db,
        note_id=note_id,
        current_user=current_user,
        ip_address=client_ip
    )
    return note_to_out(note)

@router.post("/clinical-notes/{note_id}/amend", response_model=ClinicalNoteOut, status_code=status.HTTP_201_CREATED)
def amend_note(
    note_id: int,
    amend_in: ClinicalNoteAmend,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR]))
):
    client_ip = request.client.host if request.client else None
    amended = amend_clinical_note(
        db=db,
        note_id=note_id,
        amend_in=amend_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return note_to_out(amended)

# ==========================================
# 4. DIAGNOSES
# ==========================================

@router.post("/encounters/{encounter_id}/diagnoses", response_model=DiagnosisOut, status_code=status.HTTP_201_CREATED)
def add_diagnosis(
    encounter_id: int,
    diag_in: DiagnosisCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR]))
):
    client_ip = request.client.host if request.client else None
    diag = create_clinical_diagnosis(
        db=db,
        encounter_id=encounter_id,
        diag_in=diag_in,
        current_user=current_user,
        ip_address=client_ip
    )
    return diagnosis_to_out(diag)

@router.get("/encounters/{encounter_id}/diagnoses", response_model=List[DiagnosisOut])
def get_encounter_diagnoses(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECEPTIONIST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Receptionists cannot access clinical diagnoses.")

    enc = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not enc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or enc.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile or enc.attending_doctor_id != current_user.doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: You are not authorized to view diagnoses for this encounter.")

    if current_user.role == UserRole.NURSE:
        if not current_user.staff_profile or not current_user.staff_profile.department_id or enc.department_id != current_user.staff_profile.department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Encounter is outside your assigned department.")

    diags = db.query(ClinicalDiagnosis).filter(ClinicalDiagnosis.encounter_id == encounter_id).order_by(ClinicalDiagnosis.created_at.asc()).all()
    return [diagnosis_to_out(d) for d in diags]
