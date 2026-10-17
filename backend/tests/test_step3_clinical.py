import pytest
import os
from datetime import date, time, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.models import (
    User, UserRole, Department, Doctor, DoctorSchedule, Patient, Appointment,
    AppointmentType, AppointmentStatus, Encounter, EncounterVitals, ClinicalNote,
    ClinicalDiagnosis, EncounterType, EncounterStatus, ClinicalNoteStatus, DiagnosisType,
    AuditLog, StaffProfile
)
from app.main import app
from app.core.migrations import run_step2_migrations, run_step3_migrations

TEST_DATABASE_URL = os.getenv("TEST_PG_URL", "sqlite:///:memory:")

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in TEST_DATABASE_URL else None
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    run_step2_migrations(engine)
    run_step3_migrations(engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    test_emails = [
        "admin.step3@medicore.ai", "receptionist.step3@medicore.ai",
        "nurse.step3@medicore.ai", "nurse2.step3@medicore.ai", "staff.step3@medicore.ai",
        "doctor1.step3@medicore.ai", "doctor2.step3@medicore.ai",
        "patient1.step3@medicore.ai", "patient2.step3@medicore.ai"
    ]

    def cleanup():
        try:
            session.query(ClinicalDiagnosis).delete(synchronize_session=False)
            session.query(ClinicalNote).delete(synchronize_session=False)
            session.query(EncounterVitals).delete(synchronize_session=False)
            session.query(Encounter).delete(synchronize_session=False)
            session.query(Appointment).filter(Appointment.appointment_number.like("MED-%-CLIN%")).delete(synchronize_session=False)
            session.query(Patient).filter(Patient.email.in_(test_emails)).delete(synchronize_session=False)
            session.query(Doctor).filter(Doctor.user.has(User.email.in_(test_emails))).delete(synchronize_session=False)
            session.query(StaffProfile).filter(StaffProfile.user.has(User.email.in_(test_emails))).delete(synchronize_session=False)
            session.query(User).filter(User.email.in_(test_emails)).delete(synchronize_session=False)
            session.query(Department).filter(Department.code.in_(["IMD", "CARD"])).delete(synchronize_session=False)
            session.commit()
        except Exception:
            session.rollback()

    cleanup()
    yield session
    cleanup()
    session.close()

@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def get_auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def setup_step3_data(db_session):
    # Department 1: Internal Medicine
    dept = Department(
        name="Internal Medicine & Diagnostics",
        code="IMD",
        description="Comprehensive diagnostic medicine and clinical care",
        floor="2nd Floor",
        is_active=True
    )
    # Department 2: Cardiology (different department)
    dept2 = Department(
        name="Cardiology",
        code="CARD",
        description="Cardiovascular medicine and care",
        floor="3rd Floor",
        is_active=True
    )
    db_session.add_all([dept, dept2])
    db_session.flush()

    # Admin
    admin_u = User(
        email="admin.step3@medicore.ai",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Director",
        role=UserRole.ADMIN,
        is_active=True
    )
    # Receptionist
    rec_u = User(
        email="receptionist.step3@medicore.ai",
        hashed_password=get_password_hash("ReceptionPass123!"),
        full_name="Receptionist Amy",
        role=UserRole.RECEPTIONIST,
        is_active=True
    )
    # Nurse 1 (Assigned to dept IMD)
    nurse_u = User(
        email="nurse.step3@medicore.ai",
        hashed_password=get_password_hash("NursePass123!"),
        full_name="Nurse David",
        role=UserRole.NURSE,
        is_active=True
    )
    # Nurse 2 (Assigned to dept2 Cardiology)
    nurse2_u = User(
        email="nurse2.step3@medicore.ai",
        hashed_password=get_password_hash("NursePass123!"),
        full_name="Nurse Sarah",
        role=UserRole.NURSE,
        is_active=True
    )
    # Generic Staff
    staff_u = User(
        email="staff.step3@medicore.ai",
        hashed_password=get_password_hash("StaffPass123!"),
        full_name="Staff Bob",
        role=UserRole.STAFF,
        is_active=True
    )
    # Doctor 1 (Attending - in IMD)
    doc1_u = User(
        email="doctor1.step3@medicore.ai",
        hashed_password=get_password_hash("DocPass123!"),
        full_name="Dr. Gregory House",
        role=UserRole.DOCTOR,
        is_active=True
    )
    # Doctor 2 (Same department IMD, but NOT attending)
    doc2_u = User(
        email="doctor2.step3@medicore.ai",
        hashed_password=get_password_hash("DocPass123!"),
        full_name="Dr. Allison Cameron",
        role=UserRole.DOCTOR,
        is_active=True
    )
    # Patient 1
    pat1_u = User(
        email="patient1.step3@medicore.ai",
        hashed_password=get_password_hash("PatPass123!"),
        full_name="John Doe",
        role=UserRole.PATIENT,
        is_active=True
    )
    # Patient 2
    pat2_u = User(
        email="patient2.step3@medicore.ai",
        hashed_password=get_password_hash("PatPass123!"),
        full_name="Jane Smith",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add_all([admin_u, rec_u, nurse_u, nurse2_u, staff_u, doc1_u, doc2_u, pat1_u, pat2_u])
    db_session.flush()

    # Staff Profiles
    nurse_prof = StaffProfile(
        user_id=nurse_u.id,
        department_id=dept.id,
        job_title="Registered Nurse",
        employee_id="NURSE-001"
    )
    nurse2_prof = StaffProfile(
        user_id=nurse2_u.id,
        department_id=dept2.id,
        job_title="Cardiology Nurse",
        employee_id="NURSE-002"
    )
    db_session.add_all([nurse_prof, nurse2_prof])

    doc1 = Doctor(
        user_id=doc1_u.id,
        department_id=dept.id,
        specialization="Diagnostician",
        qualification="MD",
        experience_years=15
    )
    doc2 = Doctor(
        user_id=doc2_u.id,
        department_id=dept.id,
        specialization="Immunology",
        qualification="MD",
        experience_years=8
    )
    db_session.add_all([doc1, doc2])
    db_session.flush()

    pat1 = Patient(
        patient_number="PAT-202609-000031",
        user_id=pat1_u.id,
        full_name="John Doe",
        email=pat1_u.email,
        phone="+1555000001",
        date_of_birth=date(1985, 5, 20),
        gender="Male",
        blood_group="O+"
    )
    pat2 = Patient(
        patient_number="PAT-202609-000032",
        user_id=pat2_u.id,
        full_name="Jane Smith",
        email=pat2_u.email,
        phone="+1555000002",
        date_of_birth=date(1990, 8, 15),
        gender="Female",
        blood_group="A+"
    )
    db_session.add_all([pat1, pat2])
    db_session.flush()

    # Create checked-in appointment for Patient 1 with Doctor 1
    appt = Appointment(
        appointment_number="MED-202609-CLIN01",
        patient_id=pat1.id,
        doctor_id=doc1.id,
        department_id=dept.id,
        date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 30),
        type=AppointmentType.IN_PERSON,
        status=AppointmentStatus.CHECKED_IN,
        check_in_time=datetime.utcnow(),
        reason="Persistent joint pain and fever"
    )
    db_session.add(appt)
    db_session.commit()

    return {
        "dept": dept,
        "dept2": dept2,
        "admin": admin_u,
        "receptionist": rec_u,
        "nurse": nurse_u,
        "nurse2": nurse2_u,
        "staff": staff_u,
        "doctor1": doc1_u,
        "doctor2": doc2_u,
        "doc1_profile": doc1,
        "doc2_profile": doc2,
        "patient1": pat1_u,
        "patient2": pat2_u,
        "pat1_profile": pat1,
        "pat2_profile": pat2,
        "appointment": appt
    }

# =========================================================================
# 1. ENCOUNTER TESTS
# =========================================================================

def test_encounter_creation_and_uniqueness(client, setup_step3_data):
    """Encounter can be created from checked-in appointment; duplicates are rejected with 409."""
    nurse_headers = get_auth_headers(setup_step3_data["nurse"])
    appt = setup_step3_data["appointment"]

    payload = {
        "patient_id": appt.patient_id,
        "appointment_id": appt.id,
        "attending_doctor_id": appt.doctor_id,
        "department_id": appt.department_id,
        "encounter_type": "OUTPATIENT"
    }

    # 1. Create primary encounter
    res = client.post("/api/v1/encounters", json=payload, headers=nurse_headers)
    assert res.status_code == 201, res.text
    enc_data = res.json()
    assert enc_data["encounter_number"].startswith("ENC-")
    assert enc_data["status"] == "OPEN"
    assert enc_data["patient_id"] == appt.patient_id
    assert enc_data["appointment_id"] == appt.id

    # 2. Duplicate encounter for the same appointment must fail with 409 Conflict
    res_dup = client.post("/api/v1/encounters", json=payload, headers=nurse_headers)
    assert res_dup.status_code == 409
    assert "already has an associated encounter" in res_dup.json()["detail"]

    # Save encounter id for subsequent tests
    setup_step3_data["encounter_id"] = enc_data["id"]

def test_encounter_lifecycle_transitions(client, setup_step3_data):
    """Encounter strictly follows OPEN -> IN_PROGRESS -> COMPLETED."""
    doc_headers = get_auth_headers(setup_step3_data["doctor1"])
    enc_id = setup_step3_data["encounter_id"]

    # 1. Invalid: Cannot complete directly from OPEN
    res_inv = client.post(f"/api/v1/encounters/{enc_id}/complete", headers=doc_headers)
    assert res_inv.status_code == 400

    # 2. Start encounter: OPEN -> IN_PROGRESS
    res_start = client.post(f"/api/v1/encounters/{enc_id}/start", headers=doc_headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "IN_PROGRESS"
    assert res_start.json()["started_at"] is not None

    # 3. Complete encounter: IN_PROGRESS -> COMPLETED
    res_comp = client.post(f"/api/v1/encounters/{enc_id}/complete", headers=doc_headers)
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"
    assert res_comp.json()["completed_at"] is not None

# =========================================================================
# 2. VITALS & INTAKE TESTS
# =========================================================================

def test_vitals_recording_and_validation(client, setup_step3_data):
    """Nurse records valid vitals with auto-calculated BMI; invalid clinical ranges are rejected."""
    nurse_headers = get_auth_headers(setup_step3_data["nurse"])
    enc_id = setup_step3_data["encounter_id"]

    # 1. Invalid temperature (e.g. 55 °C)
    res_temp = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"temperature_c": 55.0}, headers=nurse_headers)
    assert res_temp.status_code == 422

    # 2. Invalid heart rate (e.g. -10 bpm)
    res_hr = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"heart_rate": -10}, headers=nurse_headers)
    assert res_hr.status_code == 422

    # 3. Invalid BP (systolic <= diastolic: 80/120)
    res_bp = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"systolic_bp": 80, "diastolic_bp": 120}, headers=nurse_headers)
    assert res_bp.status_code == 422

    # 4. Valid Vitals
    valid_payload = {
        "temperature_c": 37.2,
        "heart_rate": 78,
        "respiratory_rate": 16,
        "systolic_bp": 122,
        "diastolic_bp": 80,
        "oxygen_saturation": 98.5,
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "pain_score": 3,
        "notes": "Patient alert, ambulatory, complaining of knee stiffness."
    }
    res_valid = client.post(f"/api/v1/encounters/{enc_id}/vitals", json=valid_payload, headers=nurse_headers)
    assert res_valid.status_code == 201
    vitals_data = res_valid.json()
    assert vitals_data["heart_rate"] == 78
    # BMI: 70 / (1.75^2) = 22.86 -> 22.9
    assert vitals_data["bmi"] == 22.9
    assert vitals_data["recorded_by_name"] == "Nurse David"

    setup_step3_data["vitals_id"] = vitals_data["id"]

def test_vitals_authorization_and_receptionist_rejection(client, setup_step3_data):
    """Receptionist is strictly blocked from vitals endpoints (403)."""
    rec_headers = get_auth_headers(setup_step3_data["receptionist"])
    enc_id = setup_step3_data["encounter_id"]
    vit_id = setup_step3_data["vitals_id"]

    # Receptionist cannot create vitals
    res_post = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"heart_rate": 80}, headers=rec_headers)
    assert res_post.status_code == 403

    # Receptionist cannot view vitals
    res_get = client.get(f"/api/v1/encounters/{enc_id}/vitals", headers=rec_headers)
    assert res_get.status_code == 403

    # Receptionist cannot update vitals
    res_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 82}, headers=rec_headers)
    assert res_put.status_code == 403

# =========================================================================
# 3. CLINICAL NOTES, INTEGRITY & AMENDMENT TESTS
# =========================================================================

def test_clinical_note_lifecycle_immutability_and_amendment(client, setup_step3_data):
    """Doctor authors draft, finalizes it (locked), and creates versioned amendment."""
    doc1_headers = get_auth_headers(setup_step3_data["doctor1"])
    doc2_headers = get_auth_headers(setup_step3_data["doctor2"])
    nurse_headers = get_auth_headers(setup_step3_data["nurse"])
    enc_id = setup_step3_data["encounter_id"]

    # 1. Nurse cannot author clinical note
    res_nurse = client.post(f"/api/v1/encounters/{enc_id}/clinical-notes", json={"chief_complaint": "Joint pain"}, headers=nurse_headers)
    assert res_nurse.status_code == 403

    # 2. Doctor 1 authors draft SOAP note
    soap_payload = {
        "chief_complaint": "Bilateral knee arthralgia for 3 weeks.",
        "history_of_present_illness": "Patient reports gradual onset swelling and stiffness, worse in morning.",
        "symptoms": "Morning stiffness > 45 mins, low-grade fever.",
        "examination_findings": "Mild effusion right knee, warm to touch.",
        "clinical_assessment": "Suspected early rheumatoid arthritis vs seronegative arthropathy.",
        "treatment_plan": "Start oral NSAIDs, obtain rheumatoid factor and anti-CCP titers.",
        "patient_instructions": "Rest joint, ice twice daily, return if fever spikes > 38.5C.",
        "follow_up_instructions": "Follow up in 2 weeks with lab results.",
        "follow_up_date": str(date.today() + timedelta(days=14))
    }
    res_note = client.post(f"/api/v1/encounters/{enc_id}/clinical-notes", json=soap_payload, headers=doc1_headers)
    assert res_note.status_code == 201
    note_data = res_note.json()
    assert note_data["status"] == "DRAFT"
    assert note_data["version"] == 1
    assert note_data["author_name"] == "Dr. Gregory House"
    note_id = note_data["id"]

    # 3. Doctor 2 cannot edit Doctor 1's draft
    res_doc2_edit = client.put(f"/api/v1/clinical-notes/{note_id}", json={"chief_complaint": "Hacked"}, headers=doc2_headers)
    assert res_doc2_edit.status_code == 403

    # 4. Doctor 1 edits own draft
    res_doc1_edit = client.put(f"/api/v1/clinical-notes/{note_id}", json={"chief_complaint": "Severe bilateral knee arthralgia."}, headers=doc1_headers)
    assert res_doc1_edit.status_code == 200
    assert res_doc1_edit.json()["chief_complaint"] == "Severe bilateral knee arthralgia."

    # 5. Doctor 1 finalizes the note
    res_fin = client.post(f"/api/v1/clinical-notes/{note_id}/finalize", headers=doc1_headers)
    assert res_fin.status_code == 200
    assert res_fin.json()["status"] == "FINAL"
    assert res_fin.json()["finalized_at"] is not None

    # 6. Finalized note is locked: direct PUT must be rejected
    res_locked = client.put(f"/api/v1/clinical-notes/{note_id}", json={"chief_complaint": "Illegal edit"}, headers=doc1_headers)
    assert res_locked.status_code == 400
    assert "Cannot directly modify a FINAL clinical note" in res_locked.json()["detail"]

    # 7. Double finalization returns 409 Conflict
    res_double_fin = client.post(f"/api/v1/clinical-notes/{note_id}/finalize", headers=doc1_headers)
    assert res_double_fin.status_code == 409

    # 8. Amendment: creates version 2 linked to parent note
    amend_payload = {
        "amendment_reason": "Corrected dosage recommendation following renal profile check.",
        "treatment_plan": "Oral NSAID adjusted to 200mg BID; renal panel normal.",
        "patient_instructions": "Take medication after food."
    }
    res_amend = client.post(f"/api/v1/clinical-notes/{note_id}/amend", json=amend_payload, headers=doc1_headers)
    assert res_amend.status_code == 201
    amended_note = res_amend.json()
    assert amended_note["version"] == 2
    assert amended_note["parent_note_id"] == note_id
    assert amended_note["status"] == "FINAL"
    assert amended_note["amendment_reason"] == "Corrected dosage recommendation following renal profile check."

    # Verify original note v1 is preserved
    res_v1 = client.get(f"/api/v1/encounters/{enc_id}/clinical-notes", headers=doc1_headers)
    assert res_v1.status_code == 200
    notes_list = res_v1.json()
    assert len(notes_list) == 2
    assert notes_list[0]["version"] == 1
    assert notes_list[0]["status"] == "AMENDED"
    assert notes_list[1]["version"] == 2
    assert notes_list[1]["status"] == "FINAL"

# =========================================================================
# 4. DIAGNOSES TESTS
# =========================================================================

def test_clinical_diagnosis_recording(client, setup_step3_data):
    """Doctor records structured diagnosis with code and type; non-clinical users rejected."""
    doc1_headers = get_auth_headers(setup_step3_data["doctor1"])
    rec_headers = get_auth_headers(setup_step3_data["receptionist"])
    enc_id = setup_step3_data["encounter_id"]

    # 1. Receptionist rejected
    res_rec = client.post(f"/api/v1/encounters/{enc_id}/diagnoses", json={"name": "Arthritis"}, headers=rec_headers)
    assert res_rec.status_code == 403

    # 2. Doctor records primary diagnosis
    diag_payload = {
        "name": "Rheumatoid arthritis, unspecified",
        "code": "M06.9",
        "code_system": "ICD-10",
        "type": "PRIMARY",
        "notes": "Positive joint swelling with elevated inflammatory markers."
    }
    res_diag = client.post(f"/api/v1/encounters/{enc_id}/diagnoses", json=diag_payload, headers=doc1_headers)
    assert res_diag.status_code == 201
    d_data = res_diag.json()
    assert d_data["name"] == "Rheumatoid arthritis, unspecified"
    assert d_data["code"] == "M06.9"
    assert d_data["type"] == "PRIMARY"
    assert d_data["doctor_name"] == "Dr. Gregory House"

# =========================================================================
# 5. LONGITUDINAL CLINICAL TIMELINE & IDOR TESTS
# =========================================================================

def test_longitudinal_clinical_timeline_and_idor(client, setup_step3_data):
    """Patient views own finalized timeline; cross-patient IDOR and receptionist access strictly blocked."""
    pat1_headers = get_auth_headers(setup_step3_data["patient1"])
    pat2_headers = get_auth_headers(setup_step3_data["patient2"])
    rec_headers = get_auth_headers(setup_step3_data["receptionist"])
    pat1_id = setup_step3_data["pat1_profile"].id
    pat2_id = setup_step3_data["pat2_profile"].id

    # 1. Receptionist accessing clinical timeline returns 403
    res_rec = client.get(f"/api/v1/patients/{pat1_id}/clinical-timeline", headers=rec_headers)
    assert res_rec.status_code == 403

    # 2. Patient 2 cannot access Patient 1's timeline (IDOR protection: 403)
    res_idor = client.get(f"/api/v1/patients/{pat1_id}/clinical-timeline", headers=pat2_headers)
    assert res_idor.status_code == 403

    # 3. Patient 1 views own timeline
    res_self = client.get(f"/api/v1/patients/{pat1_id}/clinical-timeline", headers=pat1_headers)
    assert res_self.status_code == 200
    timeline = res_self.json()
    assert len(timeline) >= 4  # Encounter, Vitals, Notes, Diagnosis

    entry_types = [e["entry_type"] for e in timeline]
    assert "ENCOUNTER" in entry_types
    assert "VITALS" in entry_types
    assert "CLINICAL_NOTE" in entry_types
    assert "DIAGNOSIS" in entry_types

    # Ensure chronological sort (most recent first)
    dates = [e["date"] for e in timeline]
    assert dates == sorted(dates, reverse=True)

# =========================================================================
# 6. CLINICAL AUDIT TRAIL VERIFICATION
# =========================================================================

def test_clinical_audit_trail_events(db_session, setup_step3_data):
    """Verifies that all required clinical audit log events exist in PostgreSQL."""
    expected_actions = [
        "ENCOUNTER_CREATE",
        "ENCOUNTER_START",
        "ENCOUNTER_COMPLETE",
        "VITALS_CREATE",
        "CLINICAL_NOTE_CREATE",
        "CLINICAL_NOTE_FINALIZE",
        "CLINICAL_NOTE_AMEND",
        "DIAGNOSIS_CREATE",
        "CLINICAL_TIMELINE_ACCESS"
    ]

    for action in expected_actions:
        log = db_session.query(AuditLog).filter(AuditLog.action == action).first()
        assert log is not None, f"Expected audit log action '{action}' was not recorded!"
        assert log.resource_type is not None
        assert log.created_at is not None

# =========================================================================
# 7. TARGETED SECURITY PASS: OBJECT-LEVEL AUTHORIZATION & IDOR TESTS
# =========================================================================

def test_doctor_same_department_isolation_and_idor(client, setup_step3_data):
    """
    Department membership alone MUST NOT grant access to another doctor's clinical encounter.
    Doctor 2 belongs to the same department as Doctor 1, but is NOT the attending doctor.
    Every clinical endpoint must strictly return 403 Forbidden for Doctor 2.
    """
    doc2_headers = get_auth_headers(setup_step3_data["doctor2"])
    enc_id = setup_step3_data["encounter_id"]
    pat1_id = setup_step3_data["pat1_profile"].id

    # 1. GET encounter
    res_enc = client.get(f"/api/v1/encounters/{enc_id}", headers=doc2_headers)
    assert res_enc.status_code == 403, f"Expected 403 on GET encounter for non-attending doctor, got {res_enc.status_code}"

    # 2. GET encounter vitals
    res_vit_get = client.get(f"/api/v1/encounters/{enc_id}/vitals", headers=doc2_headers)
    assert res_vit_get.status_code == 403, f"Expected 403 on GET vitals for non-attending doctor, got {res_vit_get.status_code}"

    # 3. POST encounter vitals
    res_vit_post = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"heart_rate": 72}, headers=doc2_headers)
    assert res_vit_post.status_code == 403, f"Expected 403 on POST vitals for non-attending doctor, got {res_vit_post.status_code}"

    # 4. GET encounter clinical notes
    res_notes_get = client.get(f"/api/v1/encounters/{enc_id}/clinical-notes", headers=doc2_headers)
    assert res_notes_get.status_code == 403, f"Expected 403 on GET clinical notes for non-attending doctor, got {res_notes_get.status_code}"

    # 5. POST encounter clinical notes
    res_notes_post = client.post(f"/api/v1/encounters/{enc_id}/clinical-notes", json={"chief_complaint": "Unauthorized note"}, headers=doc2_headers)
    assert res_notes_post.status_code == 403, f"Expected 403 on POST clinical notes for non-attending doctor, got {res_notes_post.status_code}"

    # 6. GET encounter diagnoses
    res_diag_get = client.get(f"/api/v1/encounters/{enc_id}/diagnoses", headers=doc2_headers)
    assert res_diag_get.status_code == 403, f"Expected 403 on GET diagnoses for non-attending doctor, got {res_diag_get.status_code}"

    # 7. POST encounter diagnoses
    res_diag_post = client.post(f"/api/v1/encounters/{enc_id}/diagnoses", json={"name": "Unauthorized diagnosis"}, headers=doc2_headers)
    assert res_diag_post.status_code == 403, f"Expected 403 on POST diagnoses for non-attending doctor, got {res_diag_post.status_code}"

    # 8. POST encounter start
    res_start = client.post(f"/api/v1/encounters/{enc_id}/start", headers=doc2_headers)
    assert res_start.status_code == 403, f"Expected 403 on start encounter for non-attending doctor, got {res_start.status_code}"

    # 9. POST encounter complete
    res_complete = client.post(f"/api/v1/encounters/{enc_id}/complete", headers=doc2_headers)
    assert res_complete.status_code == 403, f"Expected 403 on complete encounter for non-attending doctor, got {res_complete.status_code}"

    # 10. GET patient clinical timeline
    res_timeline = client.get(f"/api/v1/patients/{pat1_id}/clinical-timeline", headers=doc2_headers)
    assert res_timeline.status_code == 403, f"Expected 403 on timeline for doctor without clinical relationship, got {res_timeline.status_code}"

def test_vitals_object_level_authorization_and_idor(client, setup_step3_data):
    """
    - Admin cannot author or update vitals (clinical roles only).
    - Unrelated doctor cannot update vitals.
    - Unrelated nurse (outside assigned department) cannot author or update vitals.
    - Attending doctor and author nurse can update vitals.
    """
    admin_headers = get_auth_headers(setup_step3_data["admin"])
    doc1_headers = get_auth_headers(setup_step3_data["doctor1"])
    doc2_headers = get_auth_headers(setup_step3_data["doctor2"])
    nurse1_headers = get_auth_headers(setup_step3_data["nurse"])
    nurse2_headers = get_auth_headers(setup_step3_data["nurse2"])
    enc_id = setup_step3_data["encounter_id"]
    vit_id = setup_step3_data["vitals_id"]

    # 1. Admin cannot create vitals (HTTP 403)
    res_adm_post = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"heart_rate": 75}, headers=admin_headers)
    assert res_adm_post.status_code == 403

    # 2. Admin cannot update vitals (HTTP 403)
    res_adm_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 76}, headers=admin_headers)
    assert res_adm_put.status_code == 403

    # 3. Unrelated nurse (Cardiology) cannot create vitals on IMD encounter (HTTP 403)
    res_n2_post = client.post(f"/api/v1/encounters/{enc_id}/vitals", json={"heart_rate": 74}, headers=nurse2_headers)
    assert res_n2_post.status_code == 403

    # 4. Unrelated nurse (Cardiology) cannot update IMD vitals (HTTP 403)
    res_n2_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 77}, headers=nurse2_headers)
    assert res_n2_put.status_code == 403

    # 5. Unrelated doctor cannot update vitals (HTTP 403)
    res_d2_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 78}, headers=doc2_headers)
    assert res_d2_put.status_code == 403

    # 6. Author nurse (Nurse 1) can update vitals (HTTP 200)
    res_n1_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 80, "notes": "Updated by author nurse"}, headers=nurse1_headers)
    assert res_n1_put.status_code == 200
    assert res_n1_put.json()["heart_rate"] == 80

    # 7. Attending doctor (Doctor 1) can update vitals (HTTP 200)
    res_d1_put = client.put(f"/api/v1/vitals/{vit_id}", json={"heart_rate": 82, "notes": "Verified by attending physician"}, headers=doc1_headers)
    assert res_d1_put.status_code == 200
    assert res_d1_put.json()["heart_rate"] == 82

def test_diagnosis_object_level_authorization_and_idor(client, setup_step3_data):
    """
    Diagnosis authoring requires current_user.doctor_profile.id == encounter.attending_doctor_id.
    Doctor B cannot add diagnosis to Doctor A's encounter merely because they are in the same department.
    """
    doc2_headers = get_auth_headers(setup_step3_data["doctor2"])
    nurse_headers = get_auth_headers(setup_step3_data["nurse"])
    enc_id = setup_step3_data["encounter_id"]

    diag_payload = {
        "name": "Osteoarthritis, generalized",
        "code": "M15.9",
        "code_system": "ICD-10",
        "type": "SECONDARY"
    }

    # 1. Same-department non-attending doctor cannot create diagnosis (403)
    res_doc2 = client.post(f"/api/v1/encounters/{enc_id}/diagnoses", json=diag_payload, headers=doc2_headers)
    assert res_doc2.status_code == 403

    # 2. Nurse cannot create diagnosis (403)
    res_nurse = client.post(f"/api/v1/encounters/{enc_id}/diagnoses", json=diag_payload, headers=nurse_headers)
    assert res_nurse.status_code == 403

def test_encounter_creation_authorization_and_rbac(client, setup_step3_data):
    """
    Encounter creation (POST /api/v1/encounters) is strictly restricted to NURSE and DOCTOR.
    - Receptionist -> 403
    - Generic Staff -> 403
    - Admin -> 403
    - Doctor creating for another doctor -> 403
    - Nurse creating for another department -> 403
    """
    rec_headers = get_auth_headers(setup_step3_data["receptionist"])
    staff_headers = get_auth_headers(setup_step3_data["staff"])
    admin_headers = get_auth_headers(setup_step3_data["admin"])
    doc1_headers = get_auth_headers(setup_step3_data["doctor1"])
    doc2_headers = get_auth_headers(setup_step3_data["doctor2"])
    nurse2_headers = get_auth_headers(setup_step3_data["nurse2"])
    pat2 = setup_step3_data["pat2_profile"]
    doc1 = setup_step3_data["doc1_profile"]
    dept = setup_step3_data["dept"]

    payload = {
        "patient_id": pat2.id,
        "attending_doctor_id": doc1.id,
        "department_id": dept.id,
        "encounter_type": "WALK_IN"
    }

    # 1. Receptionist rejected (403)
    res_rec = client.post("/api/v1/encounters", json=payload, headers=rec_headers)
    assert res_rec.status_code == 403

    # 2. Generic staff rejected (403)
    res_staff = client.post("/api/v1/encounters", json=payload, headers=staff_headers)
    assert res_staff.status_code == 403

    # 3. Admin rejected from direct clinical encounter creation (403)
    res_adm = client.post("/api/v1/encounters", json=payload, headers=admin_headers)
    assert res_adm.status_code == 403

    # 4. Doctor 2 cannot create encounter where Doctor 1 is attending doctor (403)
    res_doc2 = client.post("/api/v1/encounters", json=payload, headers=doc2_headers)
    assert res_doc2.status_code == 403

    # 5. Nurse 2 (Cardiology) cannot create encounter for IMD department (403)
    res_nurse2 = client.post("/api/v1/encounters", json=payload, headers=nurse2_headers)
    assert res_nurse2.status_code == 403

    # 6. Doctor 1 can create encounter where Doctor 1 is attending doctor (201)
    res_doc1 = client.post("/api/v1/encounters", json=payload, headers=doc1_headers)
    assert res_doc1.status_code == 201
    assert res_doc1.json()["attending_doctor_id"] == doc1.id

