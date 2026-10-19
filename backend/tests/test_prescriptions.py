import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.models import User, UserRole, Doctor, Patient, Department, Prescription
from app.core.security import create_access_token, get_password_hash


@pytest.fixture
def prescription_test_data(db_session: Session):
    db = db_session
    dept = Department(name="Cardiology", code="CARD", is_active=True)
    db.add(dept)
    db.commit()
    db.refresh(dept)

    # Doctor
    u_doc = User(
        email="doctor_rx@hospital.com",
        hashed_password=get_password_hash("Pass@123"),
        full_name="Dr. Sarah Cardio",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db.add(u_doc)
    db.commit()
    db.refresh(u_doc)

    doc = Doctor(user_id=u_doc.id, department_id=dept.id, specialization="Cardiology", qualification="MD Cardiology")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Patient Alice
    u_pa = User(
        email="alice_rx@patient.com",
        hashed_password=get_password_hash("Pass@123"),
        full_name="Alice Patient",
        role=UserRole.PATIENT,
        is_active=True
    )
    db.add(u_pa)
    db.commit()
    db.refresh(u_pa)

    p_alice = Patient(user_id=u_pa.id, blood_group="O+")
    db.add(p_alice)
    db.commit()
    db.refresh(p_alice)

    # Patient Bob
    u_pb = User(
        email="bob_rx@patient.com",
        hashed_password=get_password_hash("Pass@123"),
        full_name="Bob Patient",
        role=UserRole.PATIENT,
        is_active=True
    )
    db.add(u_pb)
    db.commit()
    db.refresh(u_pb)

    p_bob = Patient(user_id=u_pb.id, blood_group="A+")
    db.add(p_bob)
    db.commit()
    db.refresh(p_bob)

    return {
        "doctor": doc,
        "doctor_user": u_doc,
        "patient_alice": p_alice,
        "patient_bob": p_bob,
        "alice_user": u_pa,
        "bob_user": u_pb
    }


def test_doctor_creates_valid_prescription(client: TestClient, prescription_test_data):
    doc_token = create_access_token({"sub": str(prescription_test_data["doctor_user"].id), "email": prescription_test_data["doctor_user"].email, "role": UserRole.DOCTOR.value})
    patient_id = prescription_test_data["patient_alice"].id

    payload = {
        "patient_id": patient_id,
        "medications": [
            {
                "name": "Metoprolol Succinate",
                "dosage": "50mg PO Daily",
                "frequency": "Daily",
                "duration": "30 days",
                "instructions": "Take with breakfast",
                "refills": 3
            }
        ],
        "instructions": "Monitor heart rate and blood pressure weekly."
    }

    res = client.post(
        "/api/v1/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["patient_id"] == patient_id
    assert data["doctor_name"] == "Dr. Sarah Cardio"
    assert len(data["medications"]) == 1
    assert data["medications"][0]["name"] == "Metoprolol Succinate"


def test_patient_cannot_issue_prescription(client: TestClient, prescription_test_data):
    alice_token = create_access_token({"sub": str(prescription_test_data["alice_user"].id), "email": prescription_test_data["alice_user"].email, "role": UserRole.PATIENT.value})

    payload = {
        "patient_id": prescription_test_data["patient_alice"].id,
        "medications": [
            {"name": "Amoxicillin", "dosage": "500mg", "frequency": "TID"}
        ]
    }

    res = client.post(
        "/api/v1/prescriptions",
        json=payload,
        headers={"Authorization": f"Bearer {alice_token}"}
    )
    assert res.status_code == 403


def test_patient_views_only_own_prescriptions_idor_shielding(client: TestClient, prescription_test_data):
    doc_token = create_access_token({"sub": str(prescription_test_data["doctor_user"].id), "email": prescription_test_data["doctor_user"].email, "role": UserRole.DOCTOR.value})
    alice_token = create_access_token({"sub": str(prescription_test_data["alice_user"].id), "email": prescription_test_data["alice_user"].email, "role": UserRole.PATIENT.value})
    bob_token = create_access_token({"sub": str(prescription_test_data["bob_user"].id), "email": prescription_test_data["bob_user"].email, "role": UserRole.PATIENT.value})

    # Doctor issues prescription for Alice
    rx_alice = client.post(
        "/api/v1/prescriptions",
        json={
            "patient_id": prescription_test_data["patient_alice"].id,
            "medications": [{"name": "Lisinopril", "dosage": "10mg", "frequency": "Daily"}]
        },
        headers={"Authorization": f"Bearer {doc_token}"}
    ).json()

    # Doctor issues prescription for Bob
    rx_bob = client.post(
        "/api/v1/prescriptions",
        json={
            "patient_id": prescription_test_data["patient_bob"].id,
            "medications": [{"name": "Atorvastatin", "dosage": "20mg", "frequency": "Nightly"}]
        },
        headers={"Authorization": f"Bearer {doc_token}"}
    ).json()

    # Alice lists prescriptions -> only gets her own
    alice_list = client.get("/api/v1/prescriptions", headers={"Authorization": f"Bearer {alice_token}"})
    assert alice_list.status_code == 200
    alice_items = alice_list.json()
    assert len(alice_items) >= 1
    assert all(item["patient_id"] == prescription_test_data["patient_alice"].id for item in alice_items)

    # Alice attempts IDOR: read Bob's prescription by ID
    bob_rx_id = rx_bob["id"]
    idor_res = client.get(f"/api/v1/prescriptions/{bob_rx_id}", headers={"Authorization": f"Bearer {alice_token}"})
    assert idor_res.status_code == 403


def test_doctor_cancels_prescription(client: TestClient, prescription_test_data):
    doc_token = create_access_token({"sub": str(prescription_test_data["doctor_user"].id), "email": prescription_test_data["doctor_user"].email, "role": UserRole.DOCTOR.value})

    rx = client.post(
        "/api/v1/prescriptions",
        json={
            "patient_id": prescription_test_data["patient_alice"].id,
            "medications": [{"name": "Omeprazole", "dosage": "20mg", "frequency": "Daily"}]
        },
        headers={"Authorization": f"Bearer {doc_token}"}
    ).json()

    rx_id = rx["id"]

    del_res = client.delete(f"/api/v1/prescriptions/{rx_id}", headers={"Authorization": f"Bearer {doc_token}"})
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/api/v1/prescriptions/{rx_id}", headers={"Authorization": f"Bearer {doc_token}"})
    assert get_res.status_code == 404


def test_unauthenticated_request_rejected(client: TestClient):
    res = client.get("/api/v1/prescriptions")
    assert res.status_code == 401
