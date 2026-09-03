import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.core.database import Base
from app.models.models import (
    User, UserRole, Department, Doctor, Patient, Encounter, EncounterStatus,
    LabTestDefinition, LabOrder, LabOrderItem, LabSample, LabResult,
    LabOrderPriority, LabOrderStatus, LabOrderItemStatus, LabSampleStatus,
    LabResultStatus, AbnormalFlag, StaffProfile
)
from app.core.security import get_password_hash
from app.schemas.schemas import ResultVerifyIn, SampleCollectIn, ResultAmendIn
from app.services.lab_service import verify_result, collect_sample, amend_result
from app.core.migrations import run_step2_migrations, run_step3_migrations, run_step4_migrations

PG_URL = os.getenv("TEST_PG_URL", "postgresql://medicore:medicore_secure_pass@localhost:5432/medicore_db")


@pytest.fixture(scope="module")
def pg_engine():
    try:
        engine = create_engine(PG_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.fail(f"PostgreSQL connection to {PG_URL} failed: {e}")

    Base.metadata.create_all(bind=engine)
    run_step2_migrations(engine)
    run_step3_migrations(engine)
    run_step4_migrations(engine)
    yield engine
    engine.dispose()


def test_concurrent_result_verification_row_lock(pg_engine):
    """
    True concurrent race condition test against PostgreSQL.
    Two independent threads using isolated DB sessions attempt to verify
    the exact same laboratory result simultaneously, synchronized with a threading.Barrier.
    
    Expected: Exactly one succeeds; exactly one fails with 409 Conflict.
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    setup_db = SessionMaker()

    try:
        # Pre-cleanup in case of previous aborted runs
        existing_order = setup_db.query(LabOrder).filter(LabOrder.order_number == "LAB-CONC-000001").first()
        if existing_order:
            item_ids = [i.id for i in existing_order.items]
            setup_db.query(LabResult).filter(LabResult.lab_order_item_id.in_(item_ids)).delete(synchronize_session=False)
            setup_db.query(LabOrderItem).filter(LabOrderItem.id.in_(item_ids)).delete(synchronize_session=False)
            setup_db.query(LabSample).filter(LabSample.lab_order_id == existing_order.id).delete(synchronize_session=False)
            setup_db.delete(existing_order)
            setup_db.commit()

        setup_db.query(Doctor).filter(Doctor.user.has(User.email.in_(["doc1.conc@medicore.ai", "doc2.conc@medicore.ai"]))).delete(synchronize_session=False)
        setup_db.query(Patient).filter(Patient.patient_number == "PAT-CONC-001").delete(synchronize_session=False)
        setup_db.query(User).filter(User.email.in_(["doc1.conc@medicore.ai", "doc2.conc@medicore.ai", "pat.conc@medicore.ai"])).delete(synchronize_session=False)
        setup_db.query(Department).filter(Department.code == "LCONC").delete(synchronize_session=False)
        setup_db.commit()

        dept = Department(name="Lab Concurrency Dept", code="LCONC", description="Lab Concurrency Test Dept")
        setup_db.add(dept)
        setup_db.commit()

        doc1_user = User(
            email="doc1.conc@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Dr. Conc Doctor 1",
            role=UserRole.DOCTOR
        )
        doc2_user = User(
            email="doc2.conc@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Dr. Conc Doctor 2",
            role=UserRole.DOCTOR
        )
        setup_db.add_all([doc1_user, doc2_user])
        setup_db.commit()

        doc1 = Doctor(user_id=doc1_user.id, department_id=dept.id, specialization="Pathology", qualification="MD")
        doc2 = Doctor(user_id=doc2_user.id, department_id=dept.id, specialization="Pathology", qualification="MD")
        setup_db.add_all([doc1, doc2])
        setup_db.commit()

        pat_user = User(
            email="pat.conc@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Conc Patient",
            role=UserRole.PATIENT
        )
        setup_db.add(pat_user)
        setup_db.commit()
        patient = Patient(user_id=pat_user.id, patient_number="PAT-CONC-001")
        setup_db.add(patient)
        setup_db.commit()

        test_def = setup_db.query(LabTestDefinition).filter(LabTestDefinition.code == "CBC").first()

        order = LabOrder(
            order_number="LAB-CONC-000001",
            patient_id=patient.id,
            ordered_by_doctor_id=doc1.id,
            department_id=dept.id,
            status=LabOrderStatus.COLLECTED,
            priority=LabOrderPriority.ROUTINE
        )
        setup_db.add(order)
        setup_db.commit()

        sample = LabSample(
            accession_number="ACC-CONC-000001",
            lab_order_id=order.id,
            patient_id=patient.id,
            sample_type="Whole Blood",
            status=LabSampleStatus.RECEIVED,
            collected_at=datetime.utcnow(),
            received_at=datetime.utcnow()
        )
        setup_db.add(sample)
        setup_db.commit()

        item = LabOrderItem(
            lab_order_id=order.id,
            test_definition_id=test_def.id,
            sample_id=sample.id,
            status=LabOrderItemStatus.PROCESSING
        )
        setup_db.add(item)
        setup_db.commit()

        result = LabResult(
            lab_order_item_id=item.id,
            patient_id=patient.id,
            value="14.2",
            numeric_value=14.2,
            unit="g/dL",
            reference_range="12.0 - 17.5 g/dL",
            abnormal_flag=AbnormalFlag.NORMAL,
            status=LabResultStatus.ENTERED,
            entered_by_id=doc1_user.id,
            entered_at=datetime.utcnow()
        )
        setup_db.add(result)
        setup_db.commit()
        result_id = result.id
        item_id = item.id
        sample_id = sample.id
        order_id = order.id
        doc1_id = doc1.id
        doc2_id = doc2.id
        pat_id = patient.id
        dept_id = dept.id

    finally:
        setup_db.close()

    barrier = threading.Barrier(2)
    results = {}
    exceptions = {}

    def attempt_verification(thread_idx: int, user_email: str):
        db = SessionMaker()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            # Synchronize both threads at barrier
            barrier.wait(timeout=5)
            # Call verify_result
            verified = verify_result(
                db=db,
                result_id=result_id,
                verify_data=ResultVerifyIn(comments=f"Verified by thread {thread_idx}"),
                current_user=user
            )
            results[thread_idx] = verified.id
        except Exception as exc:
            exceptions[thread_idx] = exc
            db.rollback()
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_verification, 1, "doc1.conc@medicore.ai")
        f2 = executor.submit(attempt_verification, 2, "doc1.conc@medicore.ai")
        f1.result()
        f2.result()

    # Verify exactly one succeeded and one got 409
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(exceptions) == 1, f"Expected 1 conflict exception, got {len(exceptions)}"

    failed_exc = list(exceptions.values())[0]
    assert isinstance(failed_exc, HTTPException), f"Expected HTTPException, got {type(failed_exc)}"
    assert failed_exc.status_code == 409, f"Expected 409 Conflict, got {failed_exc.status_code}"
    assert "already been verified" in failed_exc.detail

    # Verify database state
    verify_db = SessionMaker()
    try:
        final_row = verify_db.query(LabResult).filter(LabResult.id == result_id).first()
        assert final_row.status == LabResultStatus.FINAL
        assert final_row.verified_by_id is not None
        assert final_row.verified_at is not None

        # Clean up
        verify_db.query(LabResult).filter(LabResult.id == result_id).delete()
        verify_db.query(LabOrderItem).filter(LabOrderItem.id == item_id).delete()
        verify_db.query(LabSample).filter(LabSample.id == sample_id).delete()
        verify_db.query(LabOrder).filter(LabOrder.id == order_id).delete()
        verify_db.query(Doctor).filter(Doctor.id.in_([doc1_id, doc2_id])).delete()
        verify_db.query(Patient).filter(Patient.id == pat_id).delete()
        verify_db.query(User).filter(User.email.in_(["doc1.conc@medicore.ai", "doc2.conc@medicore.ai", "pat.conc@medicore.ai"])).delete()
        verify_db.query(Department).filter(Department.id == dept_id).delete()
        verify_db.commit()
    finally:
        verify_db.close()


def test_concurrent_result_amendment_invariants(pg_engine):
    """
    Two independent threads attempt to amend the SAME finalized result concurrently.
    Expected: Exactly one succeeds in creating v2; second thread fails because result status is no longer FINAL.
    """
    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    setup_db = SessionMaker()

    try:
        # Pre-cleanup in case of previous aborted runs
        existing_order = setup_db.query(LabOrder).filter(LabOrder.order_number == "LAB-AMEND-000001").first()
        if existing_order:
            item_ids = [i.id for i in existing_order.items]
            setup_db.query(LabResult).filter(LabResult.lab_order_item_id.in_(item_ids)).delete(synchronize_session=False)
            setup_db.query(LabOrderItem).filter(LabOrderItem.id.in_(item_ids)).delete(synchronize_session=False)
            setup_db.query(LabSample).filter(LabSample.lab_order_id == existing_order.id).delete(synchronize_session=False)
            setup_db.delete(existing_order)
            setup_db.commit()

        setup_db.query(Doctor).filter(Doctor.user.has(User.email.in_(["doc1.amend@medicore.ai", "doc2.amend@medicore.ai"]))).delete(synchronize_session=False)
        setup_db.query(Patient).filter(Patient.patient_number == "PAT-AMEND-001").delete(synchronize_session=False)
        setup_db.query(User).filter(User.email.in_(["doc1.amend@medicore.ai", "doc2.amend@medicore.ai", "pat.amend@medicore.ai"])).delete(synchronize_session=False)
        setup_db.query(Department).filter(Department.code == "LAMEND").delete(synchronize_session=False)
        setup_db.commit()

        dept = Department(name="Lab Amend Dept", code="LAMEND", description="Lab Amend Test Dept")
        setup_db.add(dept)
        setup_db.commit()

        doc1_user = User(
            email="doc1.amend@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Dr. Amend Doctor 1",
            role=UserRole.DOCTOR
        )
        doc2_user = User(
            email="doc2.amend@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Dr. Amend Doctor 2",
            role=UserRole.DOCTOR
        )
        setup_db.add_all([doc1_user, doc2_user])
        setup_db.commit()

        doc1 = Doctor(user_id=doc1_user.id, department_id=dept.id, specialization="Pathology", qualification="MD")
        doc2 = Doctor(user_id=doc2_user.id, department_id=dept.id, specialization="Pathology", qualification="MD")
        setup_db.add_all([doc1, doc2])
        setup_db.commit()

        pat_user = User(
            email="pat.amend@medicore.ai",
            hashed_password=get_password_hash("Pass@123"),
            full_name="Amend Patient",
            role=UserRole.PATIENT
        )
        setup_db.add(pat_user)
        setup_db.commit()
        patient = Patient(user_id=pat_user.id, patient_number="PAT-AMEND-001")
        setup_db.add(patient)
        setup_db.commit()

        test_def = setup_db.query(LabTestDefinition).filter(LabTestDefinition.code == "GLU").first()

        order = LabOrder(
            order_number="LAB-AMEND-000001",
            patient_id=patient.id,
            ordered_by_doctor_id=doc1.id,
            department_id=dept.id,
            status=LabOrderStatus.COMPLETED,
            priority=LabOrderPriority.ROUTINE
        )
        setup_db.add(order)
        setup_db.commit()

        sample = LabSample(
            accession_number="ACC-AMEND-000001",
            lab_order_id=order.id,
            patient_id=patient.id,
            sample_type="Plasma",
            status=LabSampleStatus.RECEIVED,
            collected_at=datetime.utcnow(),
            received_at=datetime.utcnow()
        )
        setup_db.add(sample)
        setup_db.commit()

        item = LabOrderItem(
            lab_order_id=order.id,
            test_definition_id=test_def.id,
            sample_id=sample.id,
            status=LabOrderItemStatus.COMPLETED
        )
        setup_db.add(item)
        setup_db.commit()

        # Initial FINAL result
        result = LabResult(
            lab_order_item_id=item.id,
            patient_id=patient.id,
            value="95",
            numeric_value=95.0,
            unit="mg/dL",
            reference_range="70 - 99 mg/dL",
            abnormal_flag=AbnormalFlag.NORMAL,
            status=LabResultStatus.FINAL,
            entered_by_id=doc1_user.id,
            entered_at=datetime.utcnow(),
            verified_by_id=doc1_user.id,
            verified_at=datetime.utcnow()
        )
        setup_db.add(result)
        setup_db.commit()
        result_id = result.id
        item_id = item.id
        sample_id = sample.id
        order_id = order.id
        doc1_id = doc1.id
        doc2_id = doc2.id
        pat_id = patient.id
        dept_id = dept.id

    finally:
        setup_db.close()

    barrier = threading.Barrier(2)
    results = {}
    exceptions = {}

    def attempt_amend(thread_idx: int, user_email: str):
        db = SessionMaker()
        try:
            user = db.query(User).filter(User.email == user_email).first()
            barrier.wait(timeout=5)
            amended = amend_result(
                db=db,
                result_id=result_id,
                amend_data=ResultAmendIn(
                    value=f"10{thread_idx}",
                    numeric_value=100.0 + thread_idx,
                    abnormal_flag=AbnormalFlag.HIGH,
                    amendment_reason=f"Concurrent amendment reason from thread {thread_idx}",
                    comments=f"Amendment thread {thread_idx}"
                ),
                current_user=user
            )
            results[thread_idx] = amended.id
        except Exception as exc:
            exceptions[thread_idx] = exc
            db.rollback()
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_amend, 1, "doc1.amend@medicore.ai")
        f2 = executor.submit(attempt_amend, 2, "doc1.amend@medicore.ai")
        f1.result()
        f2.result()

    assert len(results) == 1, f"Expected 1 amendment success, got {len(results)}"
    assert len(exceptions) == 1, f"Expected 1 amendment conflict, got {len(exceptions)}"

    failed_exc = list(exceptions.values())[0]
    assert isinstance(failed_exc, HTTPException)
    assert failed_exc.status_code == 400
    assert "Only finalized results can be amended" in failed_exc.detail

    # Clean up
    verify_db = SessionMaker()
    try:
        verify_db.query(LabResult).filter(LabResult.lab_order_item_id == item_id).delete()
        verify_db.query(LabOrderItem).filter(LabOrderItem.id == item_id).delete()
        verify_db.query(LabSample).filter(LabSample.id == sample_id).delete()
        verify_db.query(LabOrder).filter(LabOrder.id == order_id).delete()
        verify_db.query(Doctor).filter(Doctor.id.in_([doc1_id, doc2_id])).delete()
        verify_db.query(Patient).filter(Patient.id == pat_id).delete()
        verify_db.query(User).filter(User.email.in_(["doc1.amend@medicore.ai", "doc2.amend@medicore.ai", "pat.amend@medicore.ai"])).delete()
        verify_db.query(Department).filter(Department.id == dept_id).delete()
        verify_db.commit()
    finally:
        verify_db.close()
