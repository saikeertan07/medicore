import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time, timedelta
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.models.models import (
    Base, User, UserRole, Doctor, Patient, Department, DoctorSchedule, 
    Appointment, AppointmentStatus
)
from app.core.security import get_password_hash
from app.schemas.schemas import AppointmentCreate, AppointmentReschedule
from app.services.appointment_service import create_appointment, reschedule_appointment

PG_URL = os.getenv("TEST_PG_URL", "postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db")


@pytest.fixture(scope="module")
def pg_stress_engine():
    """Ensure authoritative PostgreSQL is reachable and isolated for stress tests."""
    try:
        engine = create_engine(PG_URL, pool_pre_ping=True, pool_size=30, max_overflow=20)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.fail(f"PostgreSQL stress test requires reachable database at {PG_URL}: {e}")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_twenty_thread_concurrent_booking_stress(pg_stress_engine):
    """
    STRESS TEST: 20 concurrent threads attempt to book the exact same slot simultaneously.
    Synchronized via threading.Barrier(20).
    Guarantees:
      - Exactly 1 thread succeeds (201 / returns Appointment).
      - Exactly 19 threads receive clean HTTP 409 Conflict.
      - Zero unhandled exceptions or 500s.
      - Exactly 1 confirmed appointment in the database for the given doctor/slot.
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_stress_engine)

    # 1. Setup Doctor, Department, Schedule, and 20 Patients
    setup_db = SessionMaker()
    try:
        dept = Department(name="Stress Cardiology", code="CARD-STRESS", description="Stress test dept")
        setup_db.add(dept)
        setup_db.commit()

        doc_user = User(
            email="dr.stress@medicore.ai",
            hashed_password=get_password_hash("StressPass@123"),
            full_name="Dr. Stress Validator",
            role=UserRole.DOCTOR
        )
        setup_db.add(doc_user)
        setup_db.commit()

        doctor = Doctor(
            user_id=doc_user.id,
            department_id=dept.id,
            specialization="Interventional Cardiology",
            qualification="MD, FACC",
            consultation_fee=300.0
        )
        setup_db.add(doctor)
        setup_db.commit()

        # Doctor available every day 08:00 - 18:00
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

        patients_info = []
        for i in range(20):
            u = User(
                email=f"patient_stress_{i}@medicore.ai",
                hashed_password=get_password_hash("StressPass@123"),
                full_name=f"Stress Patient {i}",
                role=UserRole.PATIENT
            )
            setup_db.add(u)
            setup_db.commit()
            p = Patient(user_id=u.id)
            setup_db.add(p)
            setup_db.commit()
            patients_info.append({"user_id": u.id, "patient_id": p.id, "full_name": u.full_name})

        doc_id = doctor.id
        dept_id = dept.id
    finally:
        setup_db.close()

    target_date = date.today() + timedelta(days=21)
    booking_payload = AppointmentCreate(
        doctor_id=doc_id,
        department_id=dept_id,
        date=target_date,
        start_time=time(14, 0),
        end_time=time(14, 30),
        reason="Twenty-thread high concurrency stress verification"
    )

    num_threads = 20
    barrier = threading.Barrier(num_threads)
    results = {}

    def worker_stress_book(thread_idx: int, patient_id: int, user_id: int, full_name: str):
        worker_session = SessionMaker()
        user_obj = User(id=user_id, role=UserRole.PATIENT, full_name=full_name)
        try:
            # Synchronize all 20 threads to release at the exact same microsecond
            barrier.wait(timeout=10)
            app = create_appointment(
                db=worker_session,
                patient_id=patient_id,
                booking_data=booking_payload,
                current_user=user_obj
            )
            results[thread_idx] = ("SUCCESS", app.id)
        except HTTPException as he:
            results[thread_idx] = ("HTTP_EXCEPTION", he.status_code, he.detail)
        except Exception as e:
            results[thread_idx] = ("FATAL_ERROR", str(e))
        finally:
            worker_session.close()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(
                worker_stress_book,
                i,
                patients_info[i]["patient_id"],
                patients_info[i]["user_id"],
                patients_info[i]["full_name"]
            )
            for i in range(num_threads)
        ]
        for f in futures:
            f.result()

    # Assertions
    successes = [res for res in results.values() if res[0] == "SUCCESS"]
    conflicts = [res for res in results.values() if res[0] == "HTTP_EXCEPTION" and res[1] == 409]
    fatal_errors = [res for res in results.values() if res[0] == "FATAL_ERROR"]

    assert len(fatal_errors) == 0, f"Encountered unexpected fatal errors: {fatal_errors}"
    assert len(successes) == 1, f"Expected exactly 1 success out of 20 threads, got {len(successes)}. Results: {results}"
    assert len(conflicts) == 19, f"Expected exactly 19 409 conflicts out of 20 threads, got {len(conflicts)}. Results: {results}"

    # Verify single persistent appointment in database
    verify_db = SessionMaker()
    try:
        active_apps = verify_db.query(Appointment).filter(
            Appointment.doctor_id == doc_id,
            Appointment.date == target_date,
            Appointment.start_time == time(14, 0),
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).all()
        assert len(active_apps) == 1
        assert active_apps[0].id == successes[0][1]
    finally:
        verify_db.close()


def test_concurrent_reschedule_collision_stress(pg_stress_engine):
    """
    Test two existing appointments attempting to reschedule into the same target slot concurrently.
    Guarantees:
      - 1 successfully claims the target slot.
      - 1 receives 409 Conflict and preserves its original slot and status untouched.
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_stress_engine)

    setup_db = SessionMaker()
    try:
        dept = Department(name="Reschedule Dept", code="RESCHED-01")
        setup_db.add(dept)
        setup_db.commit()

        doc_user = User(email="dr.resched@medicore.ai", hashed_password=get_password_hash("Pass@123"), full_name="Dr. Resched", role=UserRole.DOCTOR)
        setup_db.add(doc_user)
        setup_db.commit()

        doctor = Doctor(user_id=doc_user.id, department_id=dept.id, specialization="General Surgery", qualification="MD")
        setup_db.add(doctor)
        setup_db.commit()

        for day in range(7):
            setup_db.add(DoctorSchedule(
                doctor_id=doctor.id, day_of_week=day,
                start_time=time(8, 0), end_time=time(18, 0),
                slot_duration_minutes=30, is_available=True
            ))
        setup_db.commit()

        ua = User(email="pat_r1@medicore.ai", hashed_password=get_password_hash("Pass@123"), full_name="Patient R1", role=UserRole.PATIENT)
        ub = User(email="pat_r2@medicore.ai", hashed_password=get_password_hash("Pass@123"), full_name="Patient R2", role=UserRole.PATIENT)
        setup_db.add_all([ua, ub])
        setup_db.commit()

        pa = Patient(user_id=ua.id)
        pb = Patient(user_id=ub.id)
        setup_db.add_all([pa, pb])
        setup_db.commit()

        target_day = date.today() + timedelta(days=25)
        # Create initial appointment 1 at 09:00
        app1 = Appointment(
            appointment_number="APP-RESCHED-01",
            patient_id=pa.id, doctor_id=doctor.id, department_id=dept.id,
            date=target_day, start_time=time(9, 0), end_time=time(9, 30),
            status=AppointmentStatus.CONFIRMED, reason="Initial slot 1"
        )
        # Create initial appointment 2 at 10:00
        app2 = Appointment(
            appointment_number="APP-RESCHED-02",
            patient_id=pb.id, doctor_id=doctor.id, department_id=dept.id,
            date=target_day, start_time=time(10, 0), end_time=time(10, 30),
            status=AppointmentStatus.CONFIRMED, reason="Initial slot 2"
        )
        setup_db.add_all([app1, app2])
        setup_db.commit()

        app1_id = app1.id
        app2_id = app2.id
        pa_id = pa.id
        pb_id = pb.id
        ua_id = ua.id
        ub_id = ub.id
    finally:
        setup_db.close()

    # Both try to reschedule into 11:00 on the same date concurrently
    resched_payload = AppointmentReschedule(
        new_date=target_day,
        new_start_time=time(11, 0),
        new_end_time=time(11, 30),
        reason="Concurrent rescheduling test"
    )

    barrier = threading.Barrier(2)
    results = {}

    def worker_resched(w_name: str, app_id: int, user_id: int, full_name: str):
        session = SessionMaker()
        u = User(id=user_id, role=UserRole.PATIENT, full_name=full_name)
        try:
            barrier.wait(timeout=5)
            updated = reschedule_appointment(
                db=session,
                appointment_id=app_id,
                reschedule_data=resched_payload,
                current_user=u
            )
            results[w_name] = ("SUCCESS", updated.id, updated.start_time)
        except HTTPException as he:
            results[w_name] = ("HTTP_EXCEPTION", he.status_code, he.detail)
        except Exception as e:
            results[w_name] = ("FATAL_ERROR", str(e))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_resched, "W1", app1_id, ua_id, "Patient R1")
        f2 = executor.submit(worker_resched, "W2", app2_id, ub_id, "Patient R2")
        f1.result()
        f2.result()

    successes = [r for r in results.values() if r[0] == "SUCCESS"]
    conflicts = [r for r in results.values() if r[0] == "HTTP_EXCEPTION" and r[1] == 409]

    assert len(successes) == 1, f"Expected 1 successful reschedule, got: {results}"
    assert len(conflicts) == 1, f"Expected 1 conflict reschedule, got: {results}"

    # Verify database state
    verify_db = SessionMaker()
    try:
        a1 = verify_db.query(Appointment).filter(Appointment.id == app1_id).first()
        a2 = verify_db.query(Appointment).filter(Appointment.id == app2_id).first()
        times = {a1.start_time, a2.start_time}
        assert time(11, 0) in times, "One appointment must have moved to 11:00"
        # The other must remain at its original slot (either 09:00 or 10:00)
        assert (time(9, 0) in times) or (time(10, 0) in times)
    finally:
        verify_db.close()
