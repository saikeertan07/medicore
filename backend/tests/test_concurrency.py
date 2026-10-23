import concurrent.futures
from datetime import date, time, timedelta
from app.core.security import create_access_token, get_password_hash
from app.models.models import User, UserRole, Doctor, Patient, Department, DoctorSchedule

def test_concurrent_slot_booking_prevents_double_booking(client, db_session):
    # Setup
    dept = Department(name="Concurrency Dept", code="CONC", description="Dept for concurrency")
    db_session.add(dept)
    db_session.commit()

    doc_user = User(email="conc.doc@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Dr. Conc", role=UserRole.DOCTOR)
    db_session.add(doc_user)
    db_session.commit()

    doc = Doctor(user_id=doc_user.id, department_id=dept.id, specialization="Concurrency", qualification="MD", consultation_fee=100.0)
    db_session.add(doc)
    db_session.commit()

    for day in range(7):
        sched = DoctorSchedule(doctor_id=doc.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0), slot_duration_minutes=30)
        db_session.add(sched)
    db_session.commit()

    ua = User(email="conc.a@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Conc A", role=UserRole.PATIENT)
    ub = User(email="conc.b@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Conc B", role=UserRole.PATIENT)
    db_session.add_all([ua, ub])
    db_session.commit()

    pa = Patient(user_id=ua.id)
    pb = Patient(user_id=ub.id)
    db_session.add_all([pa, pb])
    db_session.commit()

    token_a = create_access_token({"sub": str(ua.id), "role": "PATIENT"})
    token_b = create_access_token({"sub": str(ub.id), "role": "PATIENT"})

    target_date = (date.today() + timedelta(days=20)).isoformat()
    slot_payload = {
        "doctor_id": doc.id,
        "department_id": dept.id,
        "date": target_date,
        "start_time": "10:00:00",
        "end_time": "10:30:00",
        "type": "IN_PERSON",
        "reason": "Test concurrent booking"
    }

    # First booking succeeds
    res_a = client.post(
        "/api/v1/appointments",
        json=slot_payload,
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_a.status_code == 201, f"Booking A failed: {res_a.text}"

    # Second booking for the exact same slot MUST fail with 409 Conflict!
    res_b = client.post(
        "/api/v1/appointments",
        json=slot_payload,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_b.status_code == 409
    assert "already booked" in res_b.json()["detail"].lower() or "slot conflict" in res_b.json()["detail"].lower()

def test_cancelled_appointment_releases_slot_for_rebooking(client, db_session):
    dept = Department(name="Release Dept", code="RELS", description="Dept for slot release")
    db_session.add(dept)
    db_session.commit()

    doc_user = User(email="rels.doc@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Dr. Rels", role=UserRole.DOCTOR)
    db_session.add(doc_user)
    db_session.commit()

    doc = Doctor(user_id=doc_user.id, department_id=dept.id, specialization="Release", qualification="MD", consultation_fee=100.0)
    db_session.add(doc)
    db_session.commit()

    for day in range(7):
        sched = DoctorSchedule(doctor_id=doc.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0), slot_duration_minutes=30)
        db_session.add(sched)
    db_session.commit()

    ua = User(email="rels.a@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Rels A", role=UserRole.PATIENT)
    ub = User(email="rels.b@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Rels B", role=UserRole.PATIENT)
    db_session.add_all([ua, ub])
    db_session.commit()

    pa = Patient(user_id=ua.id)
    pb = Patient(user_id=ub.id)
    db_session.add_all([pa, pb])
    db_session.commit()

    token_a = create_access_token({"sub": str(ua.id), "role": "PATIENT"})
    token_b = create_access_token({"sub": str(ub.id), "role": "PATIENT"})

    target_date = (date.today() + timedelta(days=22)).isoformat()
    slot_payload = {
        "doctor_id": doc.id,
        "department_id": dept.id,
        "date": target_date,
        "start_time": "14:00:00",
        "end_time": "14:30:00",
        "type": "IN_PERSON",
        "reason": "Initial booking"
    }

    # 1. Patient A books slot -> 201
    res_book = client.post(
        "/api/v1/appointments",
        json=slot_payload,
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_book.status_code == 201
    app_id = res_book.json()["id"]

    # 2. Patient B tries to book the same slot -> 409 Conflict
    res_conflict = client.post(
        "/api/v1/appointments",
        json=slot_payload,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_conflict.status_code == 409

    # 3. Patient A cancels their appointment
    res_cancel = client.post(
        f"/api/v1/appointments/{app_id}/cancel",
        json={"cancellation_reason": "Schedule change"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # 4. Now Patient B books the released slot -> Succeeds (201 Created)!
    res_rebook = client.post(
        "/api/v1/appointments",
        json=slot_payload,
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_rebook.status_code == 201
    assert res_rebook.json()["status"] == "CONFIRMED"
