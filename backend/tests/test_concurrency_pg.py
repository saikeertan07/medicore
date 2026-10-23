import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.models.models import (
    Base, User, UserRole, Doctor, Patient, Department, DoctorSchedule, 
    Appointment, AppointmentStatus, Notification, AuditLog
)
from app.core.security import get_password_hash
from app.schemas.schemas import AppointmentCreate, AppointmentReschedule
from app.services.appointment_service import create_appointment, reschedule_appointment, cancel_appointment
from fastapi import HTTPException

# Authoritative PostgreSQL configuration for acceptance tests
PG_URL = os.getenv("TEST_PG_URL", "postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db")

@pytest.fixture(scope="module")
def pg_engine():
    # If PostgreSQL cannot be reached, FAIL loudly as required for acceptance testing
    try:
        engine = create_engine(PG_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.fail(
            f"FATAL: PostgreSQL acceptance test failure. The test requires an authoritative PostgreSQL instance "
            f"reachable at {PG_URL}. Skipping is prohibited: {e}"
        )

    # Recreate tables in test database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

def test_true_concurrent_booking_postgresql_race_condition(pg_engine):
    """
    Genuine concurrent race condition test against PostgreSQL.
    Two independent threads using isolated DB sessions attempt to book
    the same doctor, date, and time slot concurrently, synchronized via a threading.Barrier.
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

    # 1. Setup Doctor, Department, Schedule, and 2 Patients in setup session
    setup_db = SessionMaker()
    try:
        dept = Department(name="Cardiac Surgery", code="CARD-PG", description="PostgreSQL Concurrency Dept")
        setup_db.add(dept)
        setup_db.commit()

        doc_user = User(
            email="dr.pg_race@medicore.ai",
            hashed_password=get_password_hash("Pass@1234"),
            full_name="Dr. PG Race",
            role=UserRole.DOCTOR
        )
        setup_db.add(doc_user)
        setup_db.commit()

        doctor = Doctor(
            user_id=doc_user.id,
            department_id=dept.id,
            specialization="Cardiac Electrophysiology",
            qualification="MD, FACC",
            consultation_fee=250.0
        )
        setup_db.add(doctor)
        setup_db.commit()

        # Available Monday through Sunday 08:00 - 18:00 (30 min slots)
        for day in range(7):
            sched = DoctorSchedule(
                doctor_id=doctor.id,
                day_of_week=day,
                start_time=time(8, 0),
                end_time=time(18, 0),
                slot_duration_minutes=30,
                is_available=True
            )
            setup_db.add(sched)
        setup_db.commit()

        user_a = User(email="pt.a_pg@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Patient A", role=UserRole.PATIENT)
        user_b = User(email="pt.b_pg@medicore.ai", hashed_password=get_password_hash("Pass@1234"), full_name="Patient B", role=UserRole.PATIENT)
        setup_db.add_all([user_a, user_b])
        setup_db.commit()

        pat_a = Patient(user_id=user_a.id)
        pat_b = Patient(user_id=user_b.id)
        setup_db.add_all([pat_a, pat_b])
        setup_db.commit()

        doc_id = doctor.id
        dept_id = dept.id
        pat_a_id = pat_a.id
        pat_b_id = pat_b.id
        user_a_id = user_a.id
        user_b_id = user_b.id
    finally:
        setup_db.close()

    # Target slot: 15 days in the future, 10:00 - 10:30
    target_date = date.today() + timedelta(days=15)
    booking_payload = AppointmentCreate(
        doctor_id=doc_id,
        department_id=dept_id,
        date=target_date,
        start_time=time(10, 0),
        end_time=time(10, 30),
        reason="Concurrent PostgreSQL race test"
    )

    barrier = threading.Barrier(2)
    results = {}

    def worker_book(worker_name: str, patient_id: int, user_obj: User):
        # Crucial: Each worker thread creates its OWN independent database session
        worker_session = SessionMaker()
        try:
            # Synchronize both threads before executing booking
            barrier.wait(timeout=5)
            app = create_appointment(
                db=worker_session,
                patient_id=patient_id,
                booking_data=booking_payload,
                current_user=user_obj
            )
            results[worker_name] = ("SUCCESS", app.id)
        except HTTPException as he:
            results[worker_name] = ("HTTP_EXCEPTION", he.status_code, he.detail)
        except Exception as e:
            results[worker_name] = ("ERROR", str(e))
        finally:
            worker_session.close()

    u_a = User(id=user_a_id, role=UserRole.PATIENT, full_name="Patient A")
    u_b = User(id=user_b_id, role=UserRole.PATIENT, full_name="Patient B")

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_book, "worker_A", pat_a_id, u_a)
        f2 = executor.submit(worker_book, "worker_B", pat_b_id, u_b)
        f1.result()
        f2.result()

    # Explicit Race Assertions:
    # 1. Exactly 1 SUCCESS
    successes = [res for res in results.values() if res[0] == "SUCCESS"]
    assert len(successes) == 1, f"Expected exactly 1 SUCCESS, got {len(successes)}. Results: {results}"

    # 2. Exactly 1 HTTP 409
    conflicts = [res for res in results.values() if res[0] == "HTTP_EXCEPTION" and res[1] == 409]
    assert len(conflicts) == 1, f"Expected exactly 1 HTTP 409 conflict, got {len(conflicts)}. Results: {results}"

    # 3. Exactly 1 active appointment in PostgreSQL
    verify_db = SessionMaker()
    try:
        active_apps = verify_db.query(Appointment).filter(
            Appointment.doctor_id == doc_id,
            Appointment.date == target_date,
            Appointment.start_time == time(10, 0),
            Appointment.status != AppointmentStatus.CANCELLED
        ).all()
        assert len(active_apps) == 1, f"Expected exactly 1 active appointment in PostgreSQL, found {len(active_apps)}"
        winning_app_id = active_apps[0].id

        # 4. Test Cancellation releases the slot in PostgreSQL
        winning_user = u_a if active_apps[0].patient_id == pat_a_id else u_b
        cancel_appointment(
            db=verify_db,
            appointment_id=winning_app_id,
            cancellation_reason="Slot release verification",
            current_user=winning_user
        )

        # 5. Test Rebooking the cancelled slot succeeds
        rebook_user = u_b if winning_user == u_a else u_a
        rebook_pat_id = pat_b_id if winning_user == u_a else pat_a_id
        rebooked = create_appointment(
            db=verify_db,
            patient_id=rebook_pat_id,
            booking_data=booking_payload,
            current_user=rebook_user
        )
        assert rebooked is not None
        assert rebooked.status == AppointmentStatus.CONFIRMED

        # Verify active count is still 1 (one CANCELLED, one CONFIRMED)
        all_apps = verify_db.query(Appointment).filter(
            Appointment.doctor_id == doc_id,
            Appointment.date == target_date,
            Appointment.start_time == time(10, 0)
        ).all()
        assert len(all_apps) == 2
        active_count = sum(1 for a in all_apps if a.status != AppointmentStatus.CANCELLED)
        assert active_count == 1
    finally:
        verify_db.close()

def test_postgresql_rescheduling_atomicity_and_conflict(pg_engine):
    """
    Verify that rescheduling is transaction-safe in PostgreSQL:
    - If target slot is already occupied, returns HTTP 409
    - Original appointment is NOT cancelled or lost
    - Rescheduling to a valid open slot updates date/time cleanly
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    db = SessionMaker()
    try:
        dept = db.query(Department).filter(Department.code == "CARD-PG").first()
        doctor = db.query(Doctor).filter(Doctor.department_id == dept.id).first()
        patients = db.query(Patient).all()
        pat1, pat2 = patients[0], patients[1]

        target_date = date.today() + timedelta(days=20)

        # Book slot 1 (09:00 - 09:30) for Patient 1
        app1 = create_appointment(
            db=db,
            patient_id=pat1.id,
            booking_data=AppointmentCreate(
                doctor_id=doctor.id,
                department_id=dept.id,
                date=target_date,
                start_time=time(9, 0),
                end_time=time(9, 30),
                reason="Slot 1"
            ),
            current_user=pat1.user
        )

        # Book slot 2 (09:30 - 10:00) for Patient 2
        app2 = create_appointment(
            db=db,
            patient_id=pat2.id,
            booking_data=AppointmentCreate(
                doctor_id=doctor.id,
                department_id=dept.id,
                date=target_date,
                start_time=time(9, 30),
                end_time=time(10, 0),
                reason="Slot 2"
            ),
            current_user=pat2.user
        )

        # Patient 1 attempts to reschedule to Slot 2 (which is occupied by Patient 2)
        with pytest.raises(HTTPException) as exc_info:
            reschedule_appointment(
                db=db,
                appointment_id=app1.id,
                reschedule_data=AppointmentReschedule(
                    new_date=target_date,
                    new_start_time=time(9, 30),
                    new_end_time=time(10, 0),
                    reason="Move to occupied slot"
                ),
                current_user=pat1.user
            )
        assert exc_info.value.status_code == 409

        # Crucial verification: Original appointment MUST remain at 09:00 with status CONFIRMED!
        db.refresh(app1)
        assert app1.start_time == time(9, 0)
        assert app1.status == AppointmentStatus.CONFIRMED

        # Patient 1 reschedules to an open slot (11:00 - 11:30) -> MUST SUCCEED
        rescheduled = reschedule_appointment(
            db=db,
            appointment_id=app1.id,
            reschedule_data=AppointmentReschedule(
                new_date=target_date,
                new_start_time=time(11, 0),
                new_end_time=time(11, 30),
                reason="Move to valid open slot"
            ),
            current_user=pat1.user
        )
        assert rescheduled.start_time == time(11, 0)
        assert rescheduled.status == AppointmentStatus.CONFIRMED

        # Previous slot (09:00) should now be free for re-booking
        rebooking = create_appointment(
            db=db,
            patient_id=pat2.id,
            booking_data=AppointmentCreate(
                doctor_id=doctor.id,
                department_id=dept.id,
                date=target_date,
                start_time=time(9, 0),
                end_time=time(9, 30),
                reason="Claim released 09:00 slot"
            ),
            current_user=pat2.user
        )
        assert rebooking.status == AppointmentStatus.CONFIRMED
    finally:
        db.close()

def test_postgresql_persistence_across_backend_restart(pg_engine):
    """
    Persistence test:
    1. Perform booking in PostgreSQL
    2. Completely dispose the engine connection pool (simulating full backend crash/restart)
    3. Reconnect with a fresh engine and verify Appointment, Notification, and AuditLog exist.
    """
    SessionMaker1 = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    db1 = SessionMaker1()
    try:
        dept = db1.query(Department).first()
        doc = db1.query(Doctor).first()
        pat = db1.query(Patient).first()

        future_date = date.today() + timedelta(days=25)
        app = create_appointment(
            db=db1,
            patient_id=pat.id,
            booking_data=AppointmentCreate(
                doctor_id=doc.id,
                department_id=dept.id,
                date=future_date,
                start_time=time(14, 0),
                end_time=time(14, 30),
                reason="Persistence test booking"
            ),
            current_user=pat.user,
            ip_address="192.168.1.100"
        )
        app_id = app.id
        app_number = app.appointment_number
        pat_user_id = pat.user_id
    finally:
        db1.close()

    # Simulate hard backend restart: dispose engine connection pool completely
    pg_engine.dispose()

    # Re-initialize new connection pool
    fresh_engine = create_engine(PG_URL, pool_pre_ping=True)
    SessionMaker2 = sessionmaker(autocommit=False, autoflush=False, bind=fresh_engine)
    db2 = SessionMaker2()
    try:
        # Verify Appointment persisted
        restarted_app = db2.query(Appointment).filter(Appointment.id == app_id).first()
        assert restarted_app is not None
        assert restarted_app.appointment_number == app_number
        assert restarted_app.date == future_date
        assert restarted_app.start_time == time(14, 0)
        assert restarted_app.status == AppointmentStatus.CONFIRMED

        # Verify Notification persisted
        notif = db2.query(Notification).filter(Notification.user_id == pat_user_id).order_by(Notification.id.desc()).first()
        assert notif is not None
        assert "Confirmed" in notif.title or "Scheduled" in notif.title

        # Verify Audit Log persisted
        audit = db2.query(AuditLog).filter(
            AuditLog.resource_type == "Appointment",
            AuditLog.resource_id == str(app_id),
            AuditLog.action == "APPOINTMENT_CREATE"
        ).first()
        assert audit is not None
        assert audit.ip_address == "192.168.1.100"
        assert audit.details["appointment_number"] == app_number
    finally:
        db2.close()
        fresh_engine.dispose()
