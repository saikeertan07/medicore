import pytest
import os
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.models import (
    User, UserRole, Department, Doctor, DoctorSchedule, Patient, Appointment,
    AppointmentType, AppointmentStatus, Encounter, EncounterStatus,
    LabTestDefinition, LabOrder, LabOrderItem, LabSample, LabResult,
    LabOrderPriority, LabOrderStatus, LabOrderItemStatus, LabSampleStatus,
    LabResultStatus, AbnormalFlag, AuditLog, StaffProfile
)
from app.main import app
from app.core.migrations import run_step2_migrations, run_step3_migrations, run_step4_migrations

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
    run_step4_migrations(engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    test_emails = [
        "admin.step4@medicore.ai", "doctor1.step4@medicore.ai", "doctor2.step4@medicore.ai",
        "nurse.step4@medicore.ai", "labtech.step4@medicore.ai", "clerk.step4@medicore.ai",
        "patient1.step4@medicore.ai", "patient2.step4@medicore.ai"
    ]

    def cleanup():
        try:
            session.query(LabResult).delete(synchronize_session=False)
            session.query(LabOrderItem).delete(synchronize_session=False)
            session.query(LabSample).delete(synchronize_session=False)
            session.query(LabOrder).delete(synchronize_session=False)
            session.query(AuditLog).filter(AuditLog.action.like("LAB_%")).delete(synchronize_session=False)
            session.query(Encounter).filter(Encounter.encounter_number.like("ENC-%-S4%")).delete(synchronize_session=False)
            session.query(Patient).filter(Patient.email.in_(test_emails)).delete(synchronize_session=False)
            session.query(Doctor).filter(Doctor.user.has(User.email.in_(test_emails))).delete(synchronize_session=False)
            session.query(StaffProfile).filter(StaffProfile.user.has(User.email.in_(test_emails))).delete(synchronize_session=False)
            session.query(User).filter(User.email.in_(test_emails)).delete(synchronize_session=False)
            session.query(Department).filter(Department.code.in_(["PATH", "GEN"])).delete(synchronize_session=False)
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
def setup_step4_data(db_session):
    # Department: Pathology / Lab
    lab_dept = Department(
        name="Pathology and Clinical Laboratories",
        code="PATH",
        description="Authoritative clinical diagnostics, hematology, and biochemistry",
        floor="Basement 1",
        is_active=True
    )
    gen_dept = Department(
        name="General Medicine",
        code="GEN",
        description="General outpatient medicine",
        floor="1st Floor",
        is_active=True
    )
    db_session.add_all([lab_dept, gen_dept])
    db_session.commit()

    # Users
    hashed_pwd = get_password_hash("SecureLabPass123!")

    # 1. Admin
    admin_user = User(
        email="admin.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Hospital Director Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin_user)

    # 2. Attending Doctor (Dr. House)
    doc1_user = User(
        email="doctor1.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Dr. Gregory House",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db_session.add(doc1_user)
    db_session.flush()
    doc1 = Doctor(
        user_id=doc1_user.id,
        specialization="Diagnostic Medicine",
        qualification="MD, PhD",
        department_id=gen_dept.id,
        consultation_fee=250.0
    )
    db_session.add(doc1)

    # 3. Unrelated Doctor (Dr. Cuddy)
    doc2_user = User(
        email="doctor2.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Dr. Lisa Cuddy",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db_session.add(doc2_user)
    db_session.flush()
    doc2 = Doctor(
        user_id=doc2_user.id,
        specialization="Endocrinology",
        qualification="MD, FACP",
        department_id=gen_dept.id,
        consultation_fee=300.0
    )
    db_session.add(doc2)

    # 4. Phlebotomist / Nurse
    nurse_user = User(
        email="nurse.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Nurse Jackie Peyton",
        role=UserRole.NURSE,
        is_active=True
    )
    db_session.add(nurse_user)
    db_session.flush()
    nurse_profile = StaffProfile(
        user_id=nurse_user.id,
        department_id=gen_dept.id,
        employee_id="EMP-NURSE-001",
        job_title="Registered Nurse Phlebotomist"
    )
    db_session.add(nurse_profile)

    # 5. Qualified Lab Technician
    labtech_user = User(
        email="labtech.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Dr. James Wilson (Pathologist)",
        role=UserRole.STAFF,
        is_active=True
    )
    db_session.add(labtech_user)
    db_session.flush()
    labtech_profile = StaffProfile(
        user_id=labtech_user.id,
        department_id=lab_dept.id,
        employee_id="EMP-LAB-TECH-001",
        job_title="Senior Clinical Laboratory Technologist"
    )
    db_session.add(labtech_profile)

    # 6. Unqualified Staff (Billing / Reception Clerk)
    clerk_user = User(
        email="clerk.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Billing Clerk John",
        role=UserRole.STAFF,
        is_active=True
    )
    db_session.add(clerk_user)
    db_session.flush()
    clerk_profile = StaffProfile(
        user_id=clerk_user.id,
        department_id=gen_dept.id,
        employee_id="EMP-CLERK-001",
        job_title="Billing Specialist"
    )
    db_session.add(clerk_profile)

    # 7. Patients
    pat1_user = User(
        email="patient1.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Alice Step4 Patient",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add(pat1_user)
    db_session.flush()
    pat1 = Patient(
        user_id=pat1_user.id,
        patient_number="PAT-S4-001",
        date_of_birth=datetime(1985, 4, 12).date(),
        gender="Female",
        blood_group="O+",
        phone="555-0101"
    )
    db_session.add(pat1)

    pat2_user = User(
        email="patient2.step4@medicore.ai",
        hashed_password=hashed_pwd,
        full_name="Bob Step4 Patient",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add(pat2_user)
    db_session.flush()
    pat2 = Patient(
        user_id=pat2_user.id,
        patient_number="PAT-S4-002",
        date_of_birth=datetime(1990, 8, 20).date(),
        gender="Male",
        blood_group="A+",
        phone="555-0102"
    )
    db_session.add(pat2)

    # Clinical Encounter for Patient 1 with Doctor 1
    enc = Encounter(
        encounter_number="ENC-202609-S4001",
        patient_id=pat1.id,
        attending_doctor_id=doc1.id,
        department_id=gen_dept.id,
        status=EncounterStatus.IN_PROGRESS,
        started_at=datetime.utcnow()
    )
    db_session.add(enc)

    db_session.commit()

    return {
        "admin": admin_user,
        "doc1": doc1_user,
        "doc2": doc2_user,
        "nurse": nurse_user,
        "labtech": labtech_user,
        "clerk": clerk_user,
        "pat1": pat1_user,
        "pat2": pat2_user,
        "patient1_id": pat1.id,
        "patient2_id": pat2.id,
        "encounter_id": enc.id,
        "doc1_profile_id": doc1.id
    }


def test_lab_test_catalog_listing(client, setup_step4_data):
    """Test retrieving standard lab catalog."""
    headers = get_auth_headers(setup_step4_data["doc1"])
    response = client.get("/api/v1/lab/tests", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 10
    codes = [t["code"] for t in data]
    assert "CBC" in codes
    assert "GLU" in codes
    assert "CREAT" in codes
    assert "LIPID" in codes


def test_lab_order_creation_authorization_and_validation(client, setup_step4_data, db_session):
    """Test RBAC on order creation: Doctors allowed, Patient/Clerk forbidden; Attending Doctor validation."""
    pat_id = setup_step4_data["patient1_id"]
    enc_id = setup_step4_data["encounter_id"]

    # Get CBC test id
    cbc = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "CBC").first()
    assert cbc is not None

    payload = {
        "patient_id": pat_id,
        "encounter_id": enc_id,
        "priority": "ROUTINE",
        "clinical_indication": "Routine diagnostic workup for fatigue",
        "items": [{"test_id": cbc.id, "notes": "Fasting sample preferred"}]
    }

    # 1. Patient cannot create lab orders (403)
    resp = client.post("/api/v1/lab/orders", json=payload, headers=get_auth_headers(setup_step4_data["pat1"]))
    assert resp.status_code == 403

    # 2. Staff Clerk cannot create lab orders (403)
    resp = client.post("/api/v1/lab/orders", json=payload, headers=get_auth_headers(setup_step4_data["clerk"]))
    assert resp.status_code == 403

    # 3. Unrelated Doctor (doc2) is not the attending doctor for this encounter (403)
    resp = client.post("/api/v1/lab/orders", json=payload, headers=get_auth_headers(setup_step4_data["doc2"]))
    assert resp.status_code == 403
    assert "not the attending physician" in resp.json()["detail"]

    # 4. Attending Doctor (doc1) succeeds (201)
    resp = client.post("/api/v1/lab/orders", json=payload, headers=get_auth_headers(setup_step4_data["doc1"]))
    assert resp.status_code == 201
    order = resp.json()
    assert order["order_number"].startswith("LAB-")
    assert order["status"] == "ORDERED"
    assert len(order["items"]) == 1
    assert order["items"][0]["test_id"] == cbc.id
    assert order["items"][0]["status"] == "PENDING"


def test_lab_order_cancellation(client, setup_step4_data, db_session):
    """Test order cancellation invariants and role boundaries."""
    pat_id = setup_step4_data["patient1_id"]
    glu = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "GLU").first()

    # Create an order to cancel
    create_payload = {
        "patient_id": pat_id,
        "encounter_id": setup_step4_data["encounter_id"],
        "priority": "ROUTINE",
        "clinical_indication": "Glucose check",
        "items": [{"test_id": glu.id}]
    }
    create_resp = client.post("/api/v1/lab/orders", json=create_payload, headers=get_auth_headers(setup_step4_data["doc1"]))
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    # Non-attending doctor cannot cancel (403)
    cancel_payload = {"reason": "Patient declined test"}
    resp = client.post(f"/api/v1/lab/orders/{order_id}/cancel", json=cancel_payload, headers=get_auth_headers(setup_step4_data["doc2"]))
    assert resp.status_code == 403

    # Ordering doctor cancels successfully
    resp = client.post(f"/api/v1/lab/orders/{order_id}/cancel", json=cancel_payload, headers=get_auth_headers(setup_step4_data["doc1"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
    assert resp.json()["cancellation_reason"] == "Patient declined test"
    assert resp.json()["items"][0]["status"] == "CANCELLED"


def test_sample_collection_and_rejection_lifecycle(client, setup_step4_data, db_session):
    """Test specimen collection and rejection lifecycle with explicit rejection reason."""
    pat_id = setup_step4_data["patient1_id"]
    creat = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "CREAT").first()

    # Doctor places order
    order_resp = client.post(
        "/api/v1/lab/orders",
        json={
            "patient_id": pat_id,
            "encounter_id": setup_step4_data["encounter_id"],
            "priority": "URGENT",
            "clinical_indication": "Renal panel check",
            "items": [{"test_id": creat.id}]
        },
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]
    item_id = order_resp.json()["items"][0]["id"]

    # Unqualified clerk tries to collect sample (403)
    collect_payload = {"specimen_type": "Whole Blood", "item_ids": [item_id]}
    resp = client.post(f"/api/v1/lab/orders/{order_id}/samples", json=collect_payload, headers=get_auth_headers(setup_step4_data["clerk"]))
    assert resp.status_code == 403

    # Qualified nurse collects sample (201)
    resp = client.post(f"/api/v1/lab/orders/{order_id}/samples", json=collect_payload, headers=get_auth_headers(setup_step4_data["nurse"]))
    assert resp.status_code == 201
    sample = resp.json()
    assert sample["accession_number"].startswith("ACC-")
    assert sample["status"] == "COLLECTED"
    sample_id = sample["id"]

    # Lab technologist rejects sample due to hemolysis
    reject_payload = {"rejection_reason": "Specimen hemolyzed during transport; unsuitable for renal panel"}
    resp = client.post(f"/api/v1/lab/samples/{sample_id}/reject", json=reject_payload, headers=get_auth_headers(setup_step4_data["labtech"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["rejection_reason"] == reject_payload["rejection_reason"]

    # Verify item status reverted to PENDING for redraw
    order_check = client.get(f"/api/v1/lab/orders/{order_id}", headers=get_auth_headers(setup_step4_data["doc1"])).json()
    assert order_check["items"][0]["status"] == "PENDING"
    assert order_check["items"][0]["sample_id"] is None


def test_complete_end_to_end_lab_workflow_and_amendment(client, setup_step4_data, db_session):
    """
    Complete Step 4 vertical workflow:
    Order -> Sample -> Receive -> Enter Result -> Verify/Finalize -> Direct Edit Rejection -> Amendment Invariant.
    """
    pat_id = setup_step4_data["patient1_id"]
    hgb = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "HGB").first()

    # 1. Order
    order_resp = client.post(
        "/api/v1/lab/orders",
        json={
            "patient_id": pat_id,
            "encounter_id": setup_step4_data["encounter_id"],
            "priority": "STAT",
            "clinical_indication": "Suspected acute anemia",
            "items": [{"test_id": hgb.id, "notes": "Stat venous blood draw"}]
        },
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert order_resp.status_code == 201
    order = order_resp.json()
    order_id = order["id"]
    item_id = order["items"][0]["id"]

    # 2. Collect sample
    collect_resp = client.post(
        f"/api/v1/lab/orders/{order_id}/samples",
        json={"specimen_type": "Venous Blood", "item_ids": [item_id]},
        headers=get_auth_headers(setup_step4_data["nurse"])
    )
    assert collect_resp.status_code == 201
    sample_id = collect_resp.json()["id"]

    # 3. Receive sample in lab
    recv_resp = client.post(
        f"/api/v1/lab/samples/{sample_id}/receive",
        json={"notes": "Sample received in good condition"},
        headers=get_auth_headers(setup_step4_data["labtech"])
    )
    assert recv_resp.status_code == 200
    assert recv_resp.json()["status"] == "RECEIVED"

    # 4. Result Entry (Unverified / ENTERED)
    entry_payload = {
        "value": "7.8",
        "numeric_value": 7.8,
        "unit": "g/dL",
        "reference_range": "12.0 - 17.5 g/dL",
        "abnormal_flag": "CRITICAL",
        "comments": "Severe microcytic anemia detected on primary analyzer"
    }
    entry_resp = client.post(
        f"/api/v1/lab/order-items/{item_id}/results",
        json=entry_payload,
        headers=get_auth_headers(setup_step4_data["labtech"])
    )
    assert entry_resp.status_code == 201
    result_v1 = entry_resp.json()
    result_id = result_v1["id"]
    assert result_v1["status"] == "ENTERED"
    assert result_v1["abnormal_flag"] == "CRITICAL"

    # 5. Verify Patient Confidentiality Shield: Patient MUST NOT see ENTERED results!
    pat_results_resp = client.get(
        f"/api/v1/lab/patients/{pat_id}/results",
        headers=get_auth_headers(setup_step4_data["pat1"])
    )
    assert pat_results_resp.status_code == 200
    # Any unverified result for this item must NOT be in the patient's results
    unverified_ids = [r["id"] for r in pat_results_resp.json() if r["id"] == result_id]
    assert len(unverified_ids) == 0

    # 6. Verification and Finalization
    verify_resp = client.post(
        f"/api/v1/lab/results/{result_id}/verify",
        json={"comments": "Pathologist verified against smear examination"},
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert verify_resp.status_code == 200
    final_res = verify_resp.json()
    assert final_res["status"] == "FINAL"
    assert final_res["verified_at"] is not None

    # Verify idempotency / collision handling: re-verifying returns 409 Conflict
    re_verify = client.post(
        f"/api/v1/lab/results/{result_id}/verify",
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert re_verify.status_code == 409
    assert "already been verified" in re_verify.json()["detail"]

    # 7. Immutability Invariant: Direct modification of finalized result is strictly rejected (400)
    direct_edit_resp = client.post(
        f"/api/v1/lab/order-items/{item_id}/results",
        json={"value": "8.5", "abnormal_flag": "ABNORMAL"},
        headers=get_auth_headers(setup_step4_data["labtech"])
    )
    assert direct_edit_resp.status_code == 400
    assert "finalized result already exists" in direct_edit_resp.json()["detail"]

    # 8. Amendment Workflow: v1 becomes AMENDED, v2 is created as FINAL with parent_result_id = v1.id
    amend_payload = {
        "value": "8.1",
        "numeric_value": 8.1,
        "abnormal_flag": "ABNORMAL",
        "amendment_reason": "Analyzer recalibration showed 0.3 g/dL offset; corrected per QA standard",
        "comments": "Recalibrated run"
    }
    amend_resp = client.post(
        f"/api/v1/lab/results/{result_id}/amend",
        json=amend_payload,
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert amend_resp.status_code == 200
    result_v2 = amend_resp.json()
    assert result_v2["status"] == "FINAL"
    assert result_v2["parent_result_id"] == result_id
    assert result_v2["value"] == "8.1"
    assert result_v2["amendment_reason"] == amend_payload["amendment_reason"]

    # Query database directly to verify v1 was preserved with original value
    v1_row = db_session.query(LabResult).filter(LabResult.id == result_id).first()
    assert v1_row.status == LabResultStatus.AMENDED
    assert v1_row.value == "7.8"  # Original clinical value preserved!
    assert v1_row.amendment_reason == amend_payload["amendment_reason"]

    # 9. Patient View: Patient sees only active FINAL result (v2), obsolete AMENDED (v1) is shielded
    pat_view = client.get(
        f"/api/v1/lab/patients/{pat_id}/results",
        headers=get_auth_headers(setup_step4_data["pat1"])
    )
    assert pat_view.status_code == 200
    p_results = pat_view.json()
    p_ids = [r["id"] for r in p_results]
    assert result_v2["id"] in p_ids, "Patient must see current FINAL result v2"
    assert result_id not in p_ids, "Obsolete AMENDED v1 must NOT be exposed as an active result to the patient"

    # Clinician View: Doctor sees full historical version lineage (both v1 and v2)
    doc_view = client.get(
        f"/api/v1/lab/patients/{pat_id}/results",
        headers=get_auth_headers(setup_step4_data["doc1"])
    )
    assert doc_view.status_code == 200
    doc_results = doc_view.json()
    doc_res_ids = [r["id"] for r in doc_results]
    assert result_v2["id"] in doc_res_ids, "Doctor must see current FINAL result v2"
    assert result_id in doc_res_ids, "Doctor must see preserved AMENDED result v1 for clinical audit"


def test_unauthorized_staff_rejection(client, setup_step4_data, db_session):
    """
    Verify that STAFF authorization is NOT based solely on role=STAFF.
    Billing Clerk (role=STAFF, job_title='Billing Specialist', department='General Medicine')
    lacks laboratory qualification and must receive HTTP 403.
    """
    clerk_headers = get_auth_headers(setup_step4_data["clerk"])
    doc1_headers = get_auth_headers(setup_step4_data["doc1"])
    pat1_id = setup_step4_data["patient1_id"]
    cbc = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "CBC").first()
    assert cbc is not None
    cbc_id = cbc.id

    # 1. Create a fresh order by doc1
    order_resp = client.post(
        "/api/v1/lab/orders",
        json={
            "patient_id": pat1_id,
            "priority": "ROUTINE",
            "clinical_indication": "Staff qualification boundary test",
            "items": [{"test_id": cbc_id, "notes": "Specimen"}]
        },
        headers=doc1_headers
    )
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    order_id = order_data["id"]
    item_id = order_data["items"][0]["id"]

    # 2. Unauthorized staff cannot collect samples (403)
    resp = client.post(
        f"/api/v1/lab/orders/{order_id}/samples",
        json={"specimen_type": "Whole Blood", "item_ids": [item_id]},
        headers=clerk_headers
    )
    assert resp.status_code == 403, f"Expected 403 for unqualified staff, got {resp.status_code}"
    assert "qualification" in resp.json()["detail"].lower()

    # Collect with nurse
    nurse_headers = get_auth_headers(setup_step4_data["nurse"])
    col_resp = client.post(
        f"/api/v1/lab/orders/{order_id}/samples",
        json={"specimen_type": "Whole Blood", "item_ids": [item_id]},
        headers=nurse_headers
    )
    assert col_resp.status_code == 201
    sample_id = col_resp.json()["id"]

    # 3. Unauthorized staff cannot receive samples (403)
    resp = client.post(
        f"/api/v1/lab/samples/{sample_id}/receive",
        json={"notes": "Clerk receive attempt"},
        headers=clerk_headers
    )
    assert resp.status_code == 403
    assert "qualification" in resp.json()["detail"].lower()

    # Receive with nurse
    assert client.post(f"/api/v1/lab/samples/{sample_id}/receive", json={}, headers=nurse_headers).status_code == 200

    # 4. Unauthorized staff cannot enter results (403)
    resp = client.post(
        f"/api/v1/lab/order-items/{item_id}/results",
        json={"value": "12.5", "abnormal_flag": "NORMAL"},
        headers=clerk_headers
    )
    assert resp.status_code == 403
    assert "qualification" in resp.json()["detail"].lower()


def test_same_department_doctor_object_level_authorization(client, setup_step4_data, db_session):
    """
    Verify Doctor Object-Level Authorization:
    Doctor 2 is in the SAME department (General Medicine) as Doctor 1.
    Doctor 2 must NOT be allowed to access, order, cancel, verify, or amend Doctor 1's lab orders/results.
    All attempts must return HTTP 403 Forbidden.
    """
    doc1_headers = get_auth_headers(setup_step4_data["doc1"])
    doc2_headers = get_auth_headers(setup_step4_data["doc2"])  # Same department, unrelated doctor
    nurse_headers = get_auth_headers(setup_step4_data["nurse"])
    pat1_id = setup_step4_data["patient1_id"]
    enc_id = setup_step4_data["encounter_id"]  # Attending doctor is Doctor 1
    cbc = db_session.query(LabTestDefinition).filter(LabTestDefinition.code == "CBC").first()
    assert cbc is not None
    cbc_id = cbc.id

    # 1. Doctor 2 attempts to place lab order on Doctor 1's clinical encounter -> 403 Forbidden
    resp = client.post(
        "/api/v1/lab/orders",
        json={
            "patient_id": pat1_id,
            "encounter_id": enc_id,
            "priority": "ROUTINE",
            "clinical_indication": "Unauthorized doctor order attempt",
            "items": [{"test_id": cbc_id}]
        },
        headers=doc2_headers
    )
    assert resp.status_code == 403
    assert "attending physician" in resp.json()["detail"].lower()

    # 2. Doctor 1 creates a valid lab order
    resp = client.post(
        "/api/v1/lab/orders",
        json={
            "patient_id": pat1_id,
            "encounter_id": enc_id,
            "priority": "ROUTINE",
            "clinical_indication": "Doctor 1 official order",
            "items": [{"test_id": cbc_id}]
        },
        headers=doc1_headers
    )
    assert resp.status_code == 201
    order_data = resp.json()
    order_id = order_data["id"]
    item_id = order_data["items"][0]["id"]

    # 3. Doctor 2 attempts to view Doctor 1's lab order by ID -> 403 Forbidden
    resp = client.get(f"/api/v1/lab/orders/{order_id}", headers=doc2_headers)
    assert resp.status_code == 403
    assert "attending" in resp.json()["detail"].lower() or "denied" in resp.json()["detail"].lower()

    # 4. Doctor 2 attempts to cancel Doctor 1's lab order -> 403 Forbidden
    resp = client.post(
        f"/api/v1/lab/orders/{order_id}/cancel",
        json={"reason": "Unauthorized cancel attempt by same-department doctor"},
        headers=doc2_headers
    )
    assert resp.status_code == 403
    assert "ordering physician or attending" in resp.json()["detail"].lower()

    # 5. Collect, receive, and enter result
    col_resp = client.post(
        f"/api/v1/lab/orders/{order_id}/samples",
        json={"specimen_type": "Venous Whole Blood", "item_ids": [item_id]},
        headers=nurse_headers
    )
    sample_id = col_resp.json()["id"]
    client.post(f"/api/v1/lab/samples/{sample_id}/receive", json={}, headers=nurse_headers)
    res_entry = client.post(
        f"/api/v1/lab/order-items/{item_id}/results",
        json={"value": "13.2", "abnormal_flag": "NORMAL"},
        headers=nurse_headers
    )
    result_id = res_entry.json()["id"]

    # 6. Doctor 2 attempts to verify Doctor 1's lab result -> 403 Forbidden
    resp = client.post(
        f"/api/v1/lab/results/{result_id}/verify",
        json={"comments": "Unauthorized verification by same-dept doctor"},
        headers=doc2_headers
    )
    assert resp.status_code == 403
    assert "attending or ordering" in resp.json()["detail"].lower()

    # Doctor 1 successfully verifies
    v_resp = client.post(f"/api/v1/lab/results/{result_id}/verify", json={}, headers=doc1_headers)
    assert v_resp.status_code == 200

    # 7. Doctor 2 attempts to amend Doctor 1's finalized result -> 403 Forbidden
    resp = client.post(
        f"/api/v1/lab/results/{result_id}/amend",
        json={"value": "13.5", "amendment_reason": "Unauthorized amendment attempt"},
        headers=doc2_headers
    )
    assert resp.status_code == 403
    assert "attending or ordering" in resp.json()["detail"].lower()


def test_patient_and_doctor_idor_shielding(client, setup_step4_data):
    """Test cross-patient and cross-doctor isolation (IDOR defense)."""
    pat1_id = setup_step4_data["patient1_id"]
    pat2_id = setup_step4_data["patient2_id"]

    # 1. Patient 2 cannot access Patient 1's results (403)
    resp = client.get(f"/api/v1/lab/patients/{pat1_id}/results", headers=get_auth_headers(setup_step4_data["pat2"]))
    assert resp.status_code == 403

    # 2. Doctor 2 (no clinical relationship or order) cannot access Patient 1's results (403)
    resp = client.get(f"/api/v1/lab/patients/{pat1_id}/results", headers=get_auth_headers(setup_step4_data["doc2"]))
    assert resp.status_code == 403


def test_audit_trail_events_recorded(client, setup_step4_data, db_session):
    """Verify that all 10 required Step 4 actions created valid AuditLog records with actor, object, and timestamp."""
    expected_actions = [
        "LAB_ORDER_CREATED",
        "LAB_ORDER_CANCELLED",
        "LAB_SAMPLE_COLLECTED",
        "LAB_SAMPLE_RECEIVED",
        "LAB_SAMPLE_REJECTED",
        "LAB_PROCESSING_STARTED",
        "LAB_RESULT_ENTERED",
        "LAB_RESULT_VERIFIED",
        "LAB_RESULT_FINALIZED",
        "LAB_RESULT_AMENDED"
    ]

    audit_records = db_session.query(AuditLog).filter(
        AuditLog.action.in_(expected_actions)
    ).all()

    found_actions = set()
    for log in audit_records:
        assert log.user_id is not None, f"Audit event {log.action} missing actor (user_id)"
        assert log.resource_type is not None, f"Audit event {log.action} missing resource_type"
        assert log.resource_id is not None, f"Audit event {log.action} missing object reference (resource_id)"
        assert log.created_at is not None, f"Audit event {log.action} missing timestamp (created_at)"
        found_actions.add(log.action)

    for action in expected_actions:
        assert action in found_actions, f"Audit trail missing required Step 4 action: {action}"

