import pytest
from datetime import date, time, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.models import (
    User, UserRole, Department, Doctor, DoctorSchedule, Patient, Appointment,
    AppointmentType, AppointmentStatus, StaffProfile
)
from app.main import app

import os
TEST_DATABASE_URL = os.getenv("TEST_PG_URL", "sqlite:///:memory:")

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in TEST_DATABASE_URL else None
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

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

@pytest.fixture(scope="module")
def setup_step2_data(db_session):
    dept = Department(
        name="Emergency & Acute Care",
        code="EMAC",
        description="Emergency medicine and acute triage unit",
        floor="Ground Floor",
        is_active=True
    )
    db_session.add(dept)
    db_session.flush()

    # 1. Admin
    admin_u = User(
        email="admin.step2@medicore.ai",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Admin Supervisor",
        role=UserRole.ADMIN,
        is_active=True
    )
    # 2. Receptionist
    rec_u = User(
        email="receptionist.step2@medicore.ai",
        hashed_password=get_password_hash("ReceptionPass123!"),
        full_name="Receptionist John",
        role=UserRole.RECEPTIONIST,
        is_active=True
    )
    # 3. Nurse
    nurse_u = User(
        email="nurse.step2@medicore.ai",
        hashed_password=get_password_hash("NursePass123!"),
        full_name="Nurse Clara",
        role=UserRole.NURSE,
        is_active=True
    )
    # 4. Doctor
    doc_u = User(
        email="doctor.step2@medicore.ai",
        hashed_password=get_password_hash("DocPass123!"),
        full_name="Dr. Stephen Vance",
        role=UserRole.DOCTOR,
        is_active=True
    )
    # 5. Patient 1 & 2
    pat1_u = User(
        email="patient1.step2@medicore.ai",
        hashed_password=get_password_hash("PatPass123!"),
        full_name="Alice Step2",
        role=UserRole.PATIENT,
        is_active=True
    )
    pat2_u = User(
        email="patient2.step2@medicore.ai",
        hashed_password=get_password_hash("PatPass123!"),
        full_name="Bob Step2",
        role=UserRole.PATIENT,
        is_active=True
    )

    db_session.add_all([admin_u, rec_u, nurse_u, doc_u, pat1_u, pat2_u])
    db_session.flush()

    doc = Doctor(
        user_id=doc_u.id,
        department_id=dept.id,
        specialization="Acute Medicine",
        qualification="MD, Board Certified",
        experience_years=10,
        consultation_fee=180.00,
        room_number="Room 105"
    )
    db_session.add(doc)
    db_session.flush()

    for day in range(7):
        db_session.add(DoctorSchedule(
            doctor_id=doc.id,
            day_of_week=day,
            start_time=time(8, 0),
            end_time=time(20, 0),
            slot_duration_minutes=30,
            is_available=True
        ))

    pat1 = Patient(
        patient_number="PAT-202609-000101",
        user_id=pat1_u.id,
        date_of_birth=date(1990, 1, 1),
        gender="Female",
        blood_group="O+",
        medical_history_summary="Asthma, uses Albuterol as needed.",
    )
    pat2 = Patient(
        patient_number="PAT-202609-000102",
        user_id=pat2_u.id,
        date_of_birth=date(1985, 5, 12),
        gender="Male",
        blood_group="A+",
        medical_history_summary="Type 2 Diabetes controlled on Metformin.",
    )
    db_session.add_all([pat1, pat2])
    db_session.commit()

    return {
        "dept": dept,
        "admin": admin_u,
        "receptionist": rec_u,
        "nurse": nurse_u,
        "doctor": doc,
        "patient1": pat1,
        "patient2": pat2,
    }

def get_auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}

# ==========================================
# 1. Phase A & B: Patient Management & Boundaries
# ==========================================

def test_receptionist_create_patient_without_account(client, setup_step2_data):
    """Receptionist registers a walk-in patient directly with generated patient_number."""
    headers = get_auth_headers(setup_step2_data["receptionist"])
    res = client.post("/api/v1/patients", json={
        "full_name": "Walkin Walter",
        "email": "walkin.walter@example.com",
        "phone": "+1-555-9876",
        "gender": "Male",
        "medical_history_summary": "High cholesterol, allergic to Penicillin."
    }, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["patient_number"].startswith("PAT-")
    assert data["full_name"] == "Walkin Walter"
    assert data["user_id"] is None
    # Boundary: Receptionist cannot see clinical history in response
    assert data["medical_history_summary"] is None

def test_duplicate_patient_prevention(client, setup_step2_data):
    """Duplicate registration on existing email must be rejected with 409."""
    headers = get_auth_headers(setup_step2_data["receptionist"])
    res = client.post("/api/v1/patients", json={
        "full_name": "Duplicate Person",
        "email": "walkin.walter@example.com",
        "phone": "+1-555-1111"
    }, headers=headers)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()

def test_clinical_data_protection_boundary(client, setup_step2_data):
    """Receptionists receive redacted clinical history; Doctors see full history."""
    pat1_id = setup_step2_data["patient1"].id

    rec_headers = get_auth_headers(setup_step2_data["receptionist"])
    res_rec = client.get(f"/api/v1/patients/{pat1_id}", headers=rec_headers)
    assert res_rec.status_code == 200
    assert res_rec.json()["medical_history_summary"] is None

    doc_headers = get_auth_headers(setup_step2_data["doctor"].user)
    res_doc = client.get(f"/api/v1/patients/{pat1_id}", headers=doc_headers)
    assert res_doc.status_code == 200
    assert res_doc.json()["medical_history_summary"] == "Asthma, uses Albuterol as needed."

def test_patient_idor_protection(client, setup_step2_data):
    """Patient cannot access another patient's profile or appointments."""
    pat2_id = setup_step2_data["patient2"].id
    pat1_headers = get_auth_headers(setup_step2_data["patient1"].user)

    res = client.get(f"/api/v1/patients/{pat2_id}", headers=pat1_headers)
    assert res.status_code == 403

    res_appts = client.get(f"/api/v1/patients/{pat2_id}/appointments", headers=pat1_headers)
    assert res_appts.status_code == 403

# ==========================================
# 2. Phase C: Reception & Appointment Operations
# ==========================================

def test_appointment_lifecycle_and_check_in(client, setup_step2_data, db_session):
    """Full lifecycle: book -> check-in -> in-progress -> completed -> invalid transition check."""
    doc_id = setup_step2_data["doctor"].id
    dept_id = setup_step2_data["dept"].id
    pat_id = setup_step2_data["patient1"].id
    booking_date = (date.today() + timedelta(days=1)).isoformat()

    # Step 1: Receptionist books appointment for patient
    rec_headers = get_auth_headers(setup_step2_data["receptionist"])
    res_book = client.post("/api/v1/appointments", json={
        "patient_id": pat_id,
        "doctor_id": doc_id,
        "department_id": dept_id,
        "date": booking_date,
        "start_time": "10:00:00",
        "end_time": "10:30:00",
        "type": "IN_PERSON",
        "reason": "Severe acute respiratory symptoms"
    }, headers=rec_headers)
    assert res_book.status_code == 201
    appt_data = res_book.json()
    appt_id = appt_data["id"]
    assert appt_data["status"] == "CONFIRMED"
    assert appt_data["check_in_time"] is None

    # Step 2: Patient arrives -> Receptionist checks in
    res_checkin = client.post(f"/api/v1/appointments/{appt_id}/check-in", json={
        "notes": "Patient arrived on time, seated in waiting area 2."
    }, headers=rec_headers)
    assert res_checkin.status_code == 200
    checked_in_data = res_checkin.json()
    assert checked_in_data["status"] == "CHECKED_IN"
    assert checked_in_data["check_in_time"] is not None

    # Step 3: Nurse brings patient to triage -> changes status to IN_PROGRESS
    nurse_headers = get_auth_headers(setup_step2_data["nurse"])
    res_prog = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "IN_PROGRESS",
        "notes": "Vitals taken: BP 120/80, SpO2 98%."
    }, headers=nurse_headers)
    assert res_prog.status_code == 200
    assert res_prog.json()["status"] == "IN_PROGRESS"

    # Step 4: Doctor completes consultation -> changes status to COMPLETED
    doc_headers = get_auth_headers(setup_step2_data["doctor"].user)
    res_comp = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "COMPLETED",
        "notes": "Prescription issued."
    }, headers=doc_headers)
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "COMPLETED"

    # Step 5: Terminal state protection: Cannot transition out of COMPLETED
    res_invalid = client.post(f"/api/v1/appointments/{appt_id}/status", json={
        "status": "CHECKED_IN"
    }, headers=rec_headers)
    assert res_invalid.status_code == 400
    assert "invalid" in res_invalid.json()["detail"].lower()

# ==========================================
# 3. Phase D: Departments Management
# ==========================================

def test_department_crud_and_status_toggle(client, setup_step2_data):
    """Admin manages department; toggle active status; non-admin forbidden."""
    admin_headers = get_auth_headers(setup_step2_data["admin"])
    rec_headers = get_auth_headers(setup_step2_data["receptionist"])

    # Non-admin cannot create
    res_fail = client.post("/api/v1/departments", json={
        "name": "Dermatology Clinic",
        "code": "DERM"
    }, headers=rec_headers)
    assert res_fail.status_code == 403

    # Admin creates
    res_create = client.post("/api/v1/departments", json={
        "name": "Dermatology Clinic",
        "code": "DERM",
        "description": "Comprehensive skin and allergy care"
    }, headers=admin_headers)
    assert res_create.status_code == 201
    dept_id = res_create.json()["id"]

    # Admin deactivates
    res_toggle = client.patch(f"/api/v1/departments/{dept_id}/status", json={
        "is_active": False
    }, headers=admin_headers)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] is False

# ==========================================
# 4. Phase E: Staff Management & Deactivation
# ==========================================

def test_staff_management_and_doctor_deactivation(client, setup_step2_data):
    """Admin creates doctor staff and deactivates doctor, blocking new bookings."""
    admin_headers = get_auth_headers(setup_step2_data["admin"])
    dept_id = setup_step2_data["dept"].id

    # Admin creates new doctor staff
    res_staff = client.post("/api/v1/staff", json={
        "email": "doctor.new@medicore.ai",
        "password": "DocNewPassword123!",
        "full_name": "Dr. Natalie Young",
        "role": "DOCTOR",
        "department_id": dept_id,
        "specialization": "Trauma Surgery",
        "qualifications": "MD, FACS",
        "consultation_fee": 220.00
    }, headers=admin_headers)
    assert res_staff.status_code == 201
    doc_staff = res_staff.json()
    new_doc_id = doc_staff["doctor_id"]
    new_user_id = doc_staff["id"]

    # Admin deactivates this doctor
    res_deact = client.patch(f"/api/v1/staff/{new_user_id}/status", json={
        "is_active": False
    }, headers=admin_headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    # Attempting to book deactivated doctor must fail with 400
    pat_id = setup_step2_data["patient1"].id
    rec_headers = get_auth_headers(setup_step2_data["receptionist"])
    res_book_inactive = client.post("/api/v1/appointments", json={
        "patient_id": pat_id,
        "doctor_id": new_doc_id,
        "department_id": dept_id,
        "date": (date.today() + timedelta(days=2)).isoformat(),
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "reason": "Consultation"
    }, headers=rec_headers)
    assert res_book_inactive.status_code == 400
    assert "inactive" in res_book_inactive.json()["detail"].lower()

# ==========================================
# 5. Phase F: Dashboards & Analytics
# ==========================================

def test_operational_dashboard_metrics(client, setup_step2_data):
    """Dashboard returns live PostgreSQL summary counts and role breakdowns."""
    rec_headers = get_auth_headers(setup_step2_data["receptionist"])
    res = client.get("/api/v1/analytics/dashboard", headers=rec_headers)
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "reception" in data
    assert "nurse" in data
    assert data["summary"]["total_patients"] >= 2
    assert "today_total" in data["reception"]

