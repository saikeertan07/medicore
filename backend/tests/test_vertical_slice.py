from datetime import date, time, timedelta
from app.core.security import get_password_hash
from app.models.models import User, UserRole, Patient, Doctor, Department, DoctorSchedule

def test_complete_vertical_slice_end_to_end(client, db_session):
    # Ensure test department exists
    dept = Department(name="Cardiology", code="CARD", description="Cardiac Care")
    db_session.add(dept)
    db_session.commit()

    # Ensure test doctor exists
    doc_user = User(
        email="dr.marcus.test@medicore.ai",
        hashed_password=get_password_hash("Doctor@123"),
        full_name="Dr. Marcus Chen",
        role=UserRole.DOCTOR,
        is_active=True
    )
    db_session.add(doc_user)
    db_session.commit()

    doc = Doctor(
        user_id=doc_user.id,
        department_id=dept.id,
        specialization="Cardiologist",
        qualification="MD, Harvard",
        consultation_fee=250.00
    )
    db_session.add(doc)
    db_session.commit()

    for day in range(7):
        sched = DoctorSchedule(
            doctor_id=doc.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration_minutes=30
        )
        db_session.add(sched)
    db_session.commit()

    # Ensure test patient exists
    sarah_user = User(
        email="patient.sarah.test@medicore.ai",
        hashed_password=get_password_hash("Patient@123"),
        full_name="Sarah Jenkins",
        role=UserRole.PATIENT,
        is_active=True
    )
    db_session.add(sarah_user)
    db_session.commit()

    sarah_patient = Patient(user_id=sarah_user.id, address="742 Evergreen")
    db_session.add(sarah_patient)
    db_session.commit()

    # Ensure admin user exists
    admin_user = User(
        email="admin.test@medicore.ai",
        hashed_password=get_password_hash("Admin@123"),
        full_name="Admin Boss",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin_user)
    db_session.commit()

    # STEP 1: LOGIN as Sarah (Patient)
    login_res = client.post("/api/v1/auth/login", json={
        "email": "patient.sarah.test@medicore.ai",
        "password": "Patient@123"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    sarah_auth = login_res.json()
    token = sarah_auth["access_token"]
    patient_id = sarah_auth["patient_id"]
    assert sarah_auth["role"] == "PATIENT"
    assert patient_id is not None

    # STEP 2: PATIENT PROFILE / DASHBOARD VERIFICATION
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "patient.sarah.test@medicore.ai"

    # STEP 3: DOCTOR SEARCH
    search_res = client.get("/api/v1/doctors?search=Marcus")
    assert search_res.status_code == 200
    doctors = search_res.json()
    assert len(doctors) > 0
    dr_marcus = doctors[0]
    doc_id = dr_marcus["id"]
    dept_id = dr_marcus["department_id"]

    # STEP 4: REAL AVAILABILITY
    target_date = (date.today() + timedelta(days=5)).isoformat()
    slots_res = client.get(f"/api/v1/appointments/available-slots?doctor_id={doc_id}&date={target_date}")
    assert slots_res.status_code == 200
    slot_data = slots_res.json()
    available_slots = [s for s in slot_data["slots"] if s["is_available"]]
    assert len(available_slots) > 0, "Expected at least one available slot"
    chosen_slot = available_slots[0]

    # STEP 5: APPOINTMENT BOOKING
    booking_payload = {
        "doctor_id": doc_id,
        "department_id": dept_id,
        "date": target_date,
        "start_time": chosen_slot["start_time"],
        "end_time": chosen_slot["end_time"],
        "type": "IN_PERSON",
        "reason": "Vertical slice test consultation",
        "notes": "End-to-end integration test"
    }
    booking_res = client.post(
        "/api/v1/appointments",
        json=booking_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert booking_res.status_code == 201, f"Booking failed: {booking_res.text}"
    appointment = booking_res.json()
    appointment_id = appointment["id"]
    appointment_number = appointment["appointment_number"]
    assert appointment["status"] == "CONFIRMED"

    # STEP 6: DATABASE CONFIRMATION (Fetch appointment details)
    detail_res = client.get(
        f"/api/v1/appointments/{appointment_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["appointment_number"] == appointment_number
    assert detail_res.json()["doctor_id"] == doc_id

    # STEP 7: NOTIFICATION DISPATCHED
    notif_res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert notif_res.status_code == 200
    notifications = notif_res.json()
    found_notif = any("Appointment Confirmed" in n["title"] and "Marcus Chen" in n["message"] for n in notifications)
    assert found_notif, f"Notification not found in {notifications}"

    # STEP 8: AUDIT LOG VERIFICATION (Admin role required)
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin.test@medicore.ai",
        "password": "Admin@123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    audit_res = client.get(
        "/api/v1/audit-logs?action=APPOINTMENT_CREATE",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()
    found_audit = any(log["resource_id"] == str(appointment_id) for log in audit_logs)
    assert found_audit, f"Audit log for appointment {appointment_id} not found"
