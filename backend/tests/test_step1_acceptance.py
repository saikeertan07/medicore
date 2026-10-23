import pytest
from datetime import date, time, timedelta, datetime
from app.core.security import create_access_token, get_password_hash
from app.models.models import (
    User, UserRole, Doctor, Patient, Department, DoctorSchedule, 
    Appointment, AppointmentStatus, AuditLog
)
from app.ai.tools.doctor_tools import summarize_patient_history, search_hospital_clinical_guidelines

def create_hospital_seed(db_session):
    # Setup Dept
    dept1 = Department(name="General Medicine", code="MED-GEN", description="Primary Care")
    dept2 = Department(name="Pediatrics", code="PED-01", description="Child Care")
    db_session.add_all([dept1, dept2])
    db_session.commit()

    # Setup 2 Doctors
    u_doc1 = User(email="dr.prim@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Dr. Primary", role=UserRole.DOCTOR)
    u_doc2 = User(email="dr.ped@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Dr. Pediatric", role=UserRole.DOCTOR)
    db_session.add_all([u_doc1, u_doc2])
    db_session.commit()

    doc1 = Doctor(user_id=u_doc1.id, department_id=dept1.id, specialization="Internal Medicine", qualification="MD", consultation_fee=150.0)
    doc2 = Doctor(user_id=u_doc2.id, department_id=dept2.id, specialization="Pediatrics", qualification="MD", consultation_fee=160.0)
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # Schedules for all 7 weekdays: 09:00 - 17:00, 30 min slots
    for d in range(7):
        s1 = DoctorSchedule(doctor_id=doc1.id, day_of_week=d, start_time=time(9, 0), end_time=time(17, 0), slot_duration_minutes=30, is_available=True)
        s2 = DoctorSchedule(doctor_id=doc2.id, day_of_week=d, start_time=time(9, 0), end_time=time(17, 0), slot_duration_minutes=30, is_available=True)
        db_session.add_all([s1, s2])
    db_session.commit()

    # 2 Patients
    u_pat1 = User(email="pat.one@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="John Doe", role=UserRole.PATIENT)
    u_pat2 = User(email="pat.two@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Jane Smith", role=UserRole.PATIENT)
    db_session.add_all([u_pat1, u_pat2])
    db_session.commit()

    pat1 = Patient(user_id=u_pat1.id)
    pat2 = Patient(user_id=u_pat2.id)
    db_session.add_all([pat1, pat2])
    db_session.commit()

    return {
        "dept1": dept1,
        "dept2": dept2,
        "doc1": doc1,
        "doc2": doc2,
        "pat1": pat1,
        "pat2": pat2,
        "u_doc1": u_doc1,
        "u_doc2": u_doc2,
        "u_pat1": u_pat1,
        "u_pat2": u_pat2,
    }

def test_doctor_search_and_availability(client, db_session):
    seed = create_hospital_seed(db_session)

    # 7. Valid doctor search
    res = client.get(f"/api/v1/doctors?search=Primary")
    assert res.status_code == 200
    doctors = res.json()
    assert len(doctors) == 1
    assert doctors[0]["full_name"] == "Dr. Primary"

    # 8. Valid availability query
    target_date = (date.today() + timedelta(days=5)).isoformat()
    res_avail = client.get(f"/api/v1/appointments/available-slots?doctor_id={seed['doc1'].id}&date={target_date}")
    assert res_avail.status_code == 200
    slots_data = res_avail.json()
    assert len(slots_data["slots"]) > 0
    assert slots_data["slots"][0]["is_available"] is True

def test_invalid_slots_and_department_rejection(client, db_session):
    seed = create_hospital_seed(db_session)
    token_pat = create_access_token({"sub": str(seed["u_pat1"].id), "role": "PATIENT"})
    headers = {"Authorization": f"Bearer {token_pat}"}

    future_date = (date.today() + timedelta(days=6)).isoformat()

    # 9a. Past date rejected
    past_date = (date.today() - timedelta(days=1)).isoformat()
    res_past = client.post("/api/v1/appointments", headers=headers, json={
        "doctor_id": seed["doc1"].id,
        "department_id": seed["dept1"].id,
        "date": past_date,
        "start_time": "10:00:00",
        "end_time": "10:30:00",
        "reason": "Past date"
    })
    assert res_past.status_code == 400
    assert "past" in res_past.json()["detail"].lower()

    # 9b. Invalid slot duration rejected (15 mins instead of 30 mins)
    res_duration = client.post("/api/v1/appointments", headers=headers, json={
        "doctor_id": seed["doc1"].id,
        "department_id": seed["dept1"].id,
        "date": future_date,
        "start_time": "10:00:00",
        "end_time": "10:15:00",
        "reason": "Wrong duration"
    })
    assert res_duration.status_code == 400
    assert "duration" in res_duration.json()["detail"].lower()

    # 9c. Unaligned slot rejected (10:17 start time)
    res_align = client.post("/api/v1/appointments", headers=headers, json={
        "doctor_id": seed["doc1"].id,
        "department_id": seed["dept1"].id,
        "date": future_date,
        "start_time": "10:17:00",
        "end_time": "10:47:00",
        "reason": "Unaligned time"
    })
    assert res_align.status_code == 400
    assert "aligned" in res_align.json()["detail"].lower()

    # 10. Wrong department rejected (Doctor 1 belongs to dept1, but dept2 requested)
    res_dept = client.post("/api/v1/appointments", headers=headers, json={
        "doctor_id": seed["doc1"].id,
        "department_id": seed["dept2"].id,
        "date": future_date,
        "start_time": "10:00:00",
        "end_time": "10:30:00",
        "reason": "Mismatched department"
    })
    assert res_dept.status_code == 400
    assert "department" in res_dept.json()["detail"].lower()

def test_booking_duplicate_cancellation_and_reschedule_flow(client, db_session):
    seed = create_hospital_seed(db_session)
    token_pat1 = create_access_token({"sub": str(seed["u_pat1"].id), "role": "PATIENT"})
    token_pat2 = create_access_token({"sub": str(seed["u_pat2"].id), "role": "PATIENT"})
    token_doc2 = create_access_token({"sub": str(seed["u_doc2"].id), "role": "DOCTOR"})

    headers1 = {"Authorization": f"Bearer {token_pat1}"}
    headers2 = {"Authorization": f"Bearer {token_pat2}"}
    headers_doc2 = {"Authorization": f"Bearer {token_doc2}"}

    target_date = (date.today() + timedelta(days=7)).isoformat()
    booking_body = {
        "doctor_id": seed["doc1"].id,
        "department_id": seed["dept1"].id,
        "date": target_date,
        "start_time": "11:00:00",
        "end_time": "11:30:00",
        "reason": "Health checkup"
    }

    # 11. Successful appointment booking (201)
    res_book = client.post("/api/v1/appointments", headers=headers1, json=booking_body)
    assert res_book.status_code == 201
    app_data = res_book.json()
    app_id = app_data["id"]
    assert app_data["status"] == "CONFIRMED"

    # 20. Audit record is created after booking
    audit = db_session.query(AuditLog).filter(
        AuditLog.resource_type == "Appointment",
        AuditLog.resource_id == str(app_id),
        AuditLog.action == "APPOINTMENT_CREATE"
    ).first()
    assert audit is not None
    assert audit.user_id == seed["u_pat1"].id

    # 12. Duplicate booking returns 409
    res_dup = client.post("/api/v1/appointments", headers=headers2, json=booking_body)
    assert res_dup.status_code == 409

    # 4. Patient appointment ownership & isolation:
    # Patient 2 cannot access Patient 1's appointment detail
    res_denied = client.get(f"/api/v1/appointments/{app_id}", headers=headers2)
    assert res_denied.status_code == 403

    # 6. Doctor 2 (unrelated doctor) cannot access Doctor 1's consultation
    res_doc_denied = client.get(f"/api/v1/appointments/{app_id}", headers=headers_doc2)
    assert res_doc_denied.status_code == 403

    # 15. Rescheduling succeeds
    res_resched = client.post(f"/api/v1/appointments/{app_id}/reschedule", headers=headers1, json={
        "new_date": target_date,
        "new_start_time": "11:30:00",
        "new_end_time": "12:00:00",
        "reason": "Need later slot"
    })
    assert res_resched.status_code == 200
    assert res_resched.json()["start_time"] == "11:30:00"

    # Previous slot (11:00:00) is now freed: Patient 2 books it -> 201
    res_claim_old = client.post("/api/v1/appointments", headers=headers2, json=booking_body)
    assert res_claim_old.status_code == 201
    app2_id = res_claim_old.json()["id"]

    # 16. Rescheduling to occupied slot returns 409
    res_resched_conflict = client.post(f"/api/v1/appointments/{app_id}/reschedule", headers=headers1, json={
        "new_date": target_date,
        "new_start_time": "11:00:00",
        "new_end_time": "11:30:00",
        "reason": "Move back to 11:00 which is now taken by Patient 2"
    })
    assert res_resched_conflict.status_code == 409

    # 13. Cancellation releases slot
    res_cancel = client.post(f"/api/v1/appointments/{app2_id}/cancel", headers=headers2, json={
        "cancellation_reason": "Travelling"
    })
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # 14. Rebooking cancelled slot succeeds
    res_rebook = client.post("/api/v1/appointments", headers=headers1, json=booking_body)
    assert res_rebook.status_code == 201
    assert res_rebook.json()["status"] == "CONFIRMED"

def test_ai_authorization_and_unauthorized_patient_access(db_session):
    seed = create_hospital_seed(db_session)

    # 19. AI tools require authenticated user
    no_user_res = summarize_patient_history(db=db_session, current_user=None, patient_id=seed["pat1"].id)
    assert no_user_res.get("authorized") is False

    # 18. AI cannot access unauthorized patient:
    # Dr. Pediatric (doc2) has NEVER had a clinical encounter with Patient 1 (pat1)
    unauthorized_res = summarize_patient_history(
        db=db_session,
        current_user=seed["u_doc2"],
        patient_id=seed["pat1"].id
    )
    assert unauthorized_res.get("authorized") is False
    assert "Access denied" in unauthorized_res["error"]

    # Now create an authorized active appointment between Dr. Primary (doc1) and Patient 1
    future_date = date.today() + timedelta(days=10)
    app = Appointment(
        appointment_number="MED-AUTH-TEST",
        doctor_id=seed["doc1"].id,
        patient_id=seed["pat1"].id,
        department_id=seed["dept1"].id,
        date=future_date,
        start_time=time(14, 0),
        end_time=time(14, 30),
        status=AppointmentStatus.CONFIRMED,
        reason="Checkup"
    )
    db_session.add(app)
    db_session.commit()

    # Dr. Primary now has an authorized active relationship -> MUST SUCCEED
    authorized_res = summarize_patient_history(
        db=db_session,
        current_user=seed["u_doc1"],
        patient_id=seed["pat1"].id
    )
    assert authorized_res.get("authorized") is True
    assert authorized_res["patient_name"] == "John Doe"
