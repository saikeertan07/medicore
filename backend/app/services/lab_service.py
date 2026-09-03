import uuid
from datetime import datetime
from app.core.datetime_utils import utc_now
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Doctor, Encounter, EncounterStatus,
    LabTestDefinition, LabOrder, LabOrderItem, LabSample, LabResult,
    LabOrderPriority, LabOrderStatus, LabOrderItemStatus, LabSampleStatus,
    LabResultStatus, AbnormalFlag
)
from app.schemas.schemas import (
    LabOrderCreate, LabOrderCancel, SampleCollectIn, SampleReceiveIn, SampleRejectIn,
    ResultEntryIn, ResultVerifyIn, ResultAmendIn
)
from app.services.audit_service import record_audit_log


def generate_lab_order_number(db: Session) -> str:
    """Generates a collision-resistant server-side order number: LAB-YYYYMM-XXXXXX"""
    now_str = utc_now().strftime("%Y%m")
    for _ in range(10):
        rand_hex = uuid.uuid4().hex[:6].upper()
        candidate = f"LAB-{now_str}-{rand_hex}"
        exists = db.query(LabOrder).filter(LabOrder.order_number == candidate).first()
        if not exists:
            return candidate
    return f"LAB-{now_str}-{uuid.uuid4().hex[:8].upper()}"


def generate_accession_number(db: Session) -> str:
    """Generates a collision-resistant accession number: ACC-YYYYMM-XXXXXX"""
    now_str = utc_now().strftime("%Y%m")
    for _ in range(10):
        rand_hex = uuid.uuid4().hex[:6].upper()
        candidate = f"ACC-{now_str}-{rand_hex}"
        exists = db.query(LabSample).filter(LabSample.accession_number == candidate).first()
        if not exists:
            return candidate
    return f"ACC-{now_str}-{uuid.uuid4().hex[:8].upper()}"


def is_lab_qualified(user: User) -> bool:
    """
    Determines if a user has laboratory qualification.
    - DOCTOR: authorized
    - NURSE: authorized for specimen collection and clinical support
    - STAFF: requires explicit lab assignment (department or job title keywords)
    - RECEPTIONIST / PATIENT / ADMIN: not lab-qualified
    """
    if user.role == UserRole.DOCTOR:
        return True
    if user.role == UserRole.NURSE:
        return True
    if user.role == UserRole.STAFF:
        if not user.staff_profile:
            return False
        title = (user.staff_profile.job_title or "").lower()
        dept = user.staff_profile.department
        dept_name = (dept.name or "").lower() if dept else ""
        dept_code = (dept.code or "").upper() if dept else ""
        
        lab_keywords = ["lab", "technician", "patholog", "biochem", "chemist", "microbiolog"]
        if any(k in title for k in lab_keywords):
            return True
        if dept_code in ["LAB", "PATH", "DIAG"] or any(k in dept_name for k in lab_keywords):
            return True
        return False
    return False


def get_lab_test_catalog(db: Session, category: Optional[str] = None, active_only: bool = True) -> List[LabTestDefinition]:
    """Retrieves standard laboratory test catalog definitions."""
    query = db.query(LabTestDefinition)
    if active_only:
        query = query.filter(LabTestDefinition.is_active == True)
    if category:
        query = query.filter(LabTestDefinition.category.ilike(f"%{category}%"))
    return query.order_by(LabTestDefinition.category, LabTestDefinition.name).all()


def create_lab_order(
    db: Session,
    order_data: LabOrderCreate,
    current_user: User
) -> LabOrder:
    """
    Creates a new laboratory order.
    Authorization: DOCTOR only.
    """
    if current_user.role != UserRole.DOCTOR or not current_user.doctor_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only licensed physicians may create laboratory orders."
        )

    doctor = current_user.doctor_profile
    doctor_id = doctor.id

    patient = db.query(Patient).filter(Patient.id == order_data.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {order_data.patient_id} not found."
        )

    encounter = None
    if order_data.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == order_data.encounter_id).first()
        if not encounter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Encounter with ID {order_data.encounter_id} not found."
            )
        if encounter.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encounter does not belong to the specified patient."
            )
        if encounter.status == EncounterStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot place laboratory orders on a cancelled encounter."
            )
        if encounter.attending_doctor_id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not the attending physician for this clinical encounter."
            )

    if not order_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A laboratory order must contain at least one test item."
        )

    test_ids = [item.test_id for item in order_data.items]
    tests = db.query(LabTestDefinition).filter(
        LabTestDefinition.id.in_(test_ids),
        LabTestDefinition.is_active == True
    ).all()
    found_test_ids = {t.id for t in tests}
    missing_tests = set(test_ids) - found_test_ids
    if missing_tests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active lab test definitions not found for IDs: {list(missing_tests)}"
        )

    order_number = generate_lab_order_number(db)
    dept_id = encounter.department_id if encounter else doctor.department_id
    lab_order = LabOrder(
        order_number=order_number,
        patient_id=patient.id,
        ordered_by_doctor_id=doctor_id,
        department_id=dept_id,
        encounter_id=encounter.id if encounter else None,
        status=LabOrderStatus.ORDERED,
        priority=order_data.priority,
        clinical_indication=order_data.clinical_indication,
        ordered_at=utc_now()
    )
    db.add(lab_order)
    db.flush()

    for item_data in order_data.items:
        order_item = LabOrderItem(
            lab_order_id=lab_order.id,
            test_definition_id=item_data.test_id,
            status=LabOrderItemStatus.PENDING,
            instructions=item_data.notes
        )
        db.add(order_item)

    db.commit()
    db.refresh(lab_order)

    record_audit_log(
        db=db,
        action="LAB_ORDER_CREATED",
        resource_type="LabOrder",
        resource_id=str(lab_order.id),
        user_id=current_user.id,
        details={
            "order_number": lab_order.order_number,
            "patient_id": patient.id,
            "ordered_by_doctor_id": doctor_id,
            "encounter_id": lab_order.encounter_id,
            "priority": lab_order.priority.value,
            "item_count": len(order_data.items)
        }
    )

    return lab_order


def cancel_lab_order(
    db: Session,
    order_id: int,
    cancel_data: LabOrderCancel,
    current_user: User
) -> LabOrder:
    """
    Cancels an existing laboratory order.
    Authorization: Ordering DOCTOR or attending doctor.
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found."
        )

    if current_user.role != UserRole.DOCTOR or not current_user.doctor_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only licensed physicians may cancel laboratory orders."
        )

    doctor_id = current_user.doctor_profile.id
    if lab_order.ordered_by_doctor_id != doctor_id:
        if not (lab_order.encounter and lab_order.encounter.attending_doctor_id == doctor_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the ordering physician or attending doctor may cancel this order."
            )

    if lab_order.status in [LabOrderStatus.COMPLETED, LabOrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel laboratory order with status {lab_order.status.value}."
        )

    for item in lab_order.items:
        if item.status in [LabOrderItemStatus.PROCESSING, LabOrderItemStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel order because one or more laboratory items are already in processing or completed."
            )

    lab_order.status = LabOrderStatus.CANCELLED
    lab_order.cancelled_at = utc_now()
    lab_order.cancellation_reason = cancel_data.reason

    for item in lab_order.items:
        item.status = LabOrderItemStatus.CANCELLED

    db.commit()
    db.refresh(lab_order)

    record_audit_log(
        db=db,
        action="LAB_ORDER_CANCELLED",
        resource_type="LabOrder",
        resource_id=str(lab_order.id),
        user_id=current_user.id,
        details={
            "order_number": lab_order.order_number,
            "patient_id": lab_order.patient_id,
            "cancellation_reason": cancel_data.reason
        }
    )

    return lab_order


def collect_sample(
    db: Session,
    order_id: int,
    collect_data: SampleCollectIn,
    current_user: User
) -> LabSample:
    """
    Collects a laboratory specimen and links order items.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks clinical laboratory qualification to collect specimens."
        )

    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found."
        )

    if lab_order.status in [LabOrderStatus.CANCELLED, LabOrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot collect samples for an order with status {lab_order.status.value}."
        )

    order_item_map = {item.id: item for item in lab_order.items}
    for item_id in collect_data.item_ids:
        if item_id not in order_item_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item ID {item_id} does not belong to laboratory order {order_id}."
            )
        item = order_item_map[item_id]
        if item.status == LabOrderItemStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item ID {item_id} is cancelled and cannot be collected."
            )

    accession = generate_accession_number(db)
    sample = LabSample(
        accession_number=accession,
        lab_order_id=lab_order.id,
        patient_id=lab_order.patient_id,
        sample_type=collect_data.specimen_type,
        status=LabSampleStatus.COLLECTED,
        collected_at=utc_now(),
        collected_by_id=current_user.id
    )
    db.add(sample)
    db.flush()

    for item_id in collect_data.item_ids:
        item = order_item_map[item_id]
        item.sample_id = sample.id
        item.status = LabOrderItemStatus.COLLECTED
        item.specimen_type = collect_data.specimen_type

    all_collected = all(i.status in [LabOrderItemStatus.COLLECTED, LabOrderItemStatus.RECEIVED, LabOrderItemStatus.PROCESSING, LabOrderItemStatus.COMPLETED] for i in lab_order.items)
    lab_order.status = LabOrderStatus.COLLECTED if all_collected else LabOrderStatus.PARTIALLY_COLLECTED

    db.commit()
    db.refresh(sample)

    record_audit_log(
        db=db,
        action="LAB_SAMPLE_COLLECTED",
        resource_type="LabSample",
        resource_id=str(sample.id),
        user_id=current_user.id,
        details={
            "accession_number": sample.accession_number,
            "order_id": lab_order.id,
            "specimen_type": sample.sample_type,
            "item_ids": collect_data.item_ids
        }
    )

    return sample


def receive_sample(
    db: Session,
    sample_id: int,
    receive_data: SampleReceiveIn,
    current_user: User
) -> LabSample:
    """
    Marks a specimen as received in the lab.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks clinical laboratory qualification to receive specimens."
        )

    sample = db.query(LabSample).filter(LabSample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory sample with ID {sample_id} not found."
        )

    if sample.status != LabSampleStatus.COLLECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive sample with current status '{sample.status.value}'. Must be COLLECTED."
        )

    sample.status = LabSampleStatus.RECEIVED
    sample.received_at = utc_now()
    sample.received_by_id = current_user.id
    sample.notes = receive_data.notes

    for item in sample.order_items:
        if item.status == LabOrderItemStatus.COLLECTED:
            item.status = LabOrderItemStatus.RECEIVED

    if sample.lab_order and sample.lab_order.status == LabOrderStatus.ORDERED:
        sample.lab_order.status = LabOrderStatus.IN_PROGRESS

    db.commit()
    db.refresh(sample)

    record_audit_log(
        db=db,
        action="LAB_SAMPLE_RECEIVED",
        resource_type="LabSample",
        resource_id=str(sample.id),
        user_id=current_user.id,
        details={
            "accession_number": sample.accession_number,
            "order_id": sample.lab_order_id,
            "notes": receive_data.notes
        }
    )

    record_audit_log(
        db=db,
        action="LAB_PROCESSING_STARTED",
        resource_type="LabSample",
        resource_id=str(sample.id),
        user_id=current_user.id,
        details={
            "accession_number": sample.accession_number,
            "order_id": sample.lab_order_id,
            "status": "PROCESSING"
        }
    )

    return sample


def reject_sample(
    db: Session,
    sample_id: int,
    reject_data: SampleRejectIn,
    current_user: User
) -> LabSample:
    """
    Rejects an unsuitable specimen.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks clinical laboratory qualification to reject specimens."
        )

    sample = db.query(LabSample).filter(LabSample.id == sample_id).first()
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory sample with ID {sample_id} not found."
        )

    if sample.status == LabSampleStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sample is already rejected."
        )

    sample.status = LabSampleStatus.REJECTED
    sample.rejected_at = utc_now()
    sample.rejected_by_id = current_user.id
    sample.rejection_reason = reject_data.rejection_reason

    for item in sample.order_items:
        item.status = LabOrderItemStatus.PENDING
        item.sample_id = None
        item.instructions = f"Specimen {sample.accession_number} rejected: {reject_data.rejection_reason}"

    db.commit()
    db.refresh(sample)

    record_audit_log(
        db=db,
        action="LAB_SAMPLE_REJECTED",
        resource_type="LabSample",
        resource_id=str(sample.id),
        user_id=current_user.id,
        details={
            "accession_number": sample.accession_number,
            "order_id": sample.lab_order_id,
            "rejection_reason": reject_data.rejection_reason
        }
    )

    return sample


def enter_result(
    db: Session,
    item_id: int,
    entry_data: ResultEntryIn,
    current_user: User
) -> LabResult:
    """
    Enters a test result for a lab order item with point-in-time reference range snapshotting.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks clinical laboratory qualification to enter test results."
        )

    item = db.query(LabOrderItem).filter(LabOrderItem.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order item with ID {item_id} not found."
        )

    if item.status == LabOrderItemStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enter result for a cancelled order item."
        )

    if not item.sample or item.sample.status == LabSampleStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enter result without a valid, unrejected specimen."
        )

    existing = db.query(LabResult).filter(
        LabResult.lab_order_item_id == item_id,
        LabResult.status.in_([LabResultStatus.FINAL, LabResultStatus.AMENDED])
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A finalized result already exists for this order item. Direct modifications are forbidden. Use the amendment API."
        )

    test_def = item.test_definition
    unit_snapshot = entry_data.unit if entry_data.unit is not None else (test_def.default_unit if test_def else None)
    ref_range_snapshot = entry_data.reference_range if entry_data.reference_range is not None else (test_def.default_reference_range if test_def else None)

    entered_result = db.query(LabResult).filter(
        LabResult.lab_order_item_id == item_id,
        LabResult.status == LabResultStatus.ENTERED
    ).first()

    if entered_result:
        entered_result.value = entry_data.value
        entered_result.numeric_value = entry_data.numeric_value
        entered_result.unit = unit_snapshot
        entered_result.reference_range = ref_range_snapshot
        entered_result.abnormal_flag = entry_data.abnormal_flag
        entered_result.comments = entry_data.comments
        entered_result.entered_by_id = current_user.id
        entered_result.entered_at = utc_now()
        result = entered_result
    else:
        result = LabResult(
            lab_order_item_id=item.id,
            patient_id=item.lab_order.patient_id,
            value=entry_data.value,
            numeric_value=entry_data.numeric_value,
            unit=unit_snapshot,
            reference_range=ref_range_snapshot,
            abnormal_flag=entry_data.abnormal_flag,
            status=LabResultStatus.ENTERED,
            comments=entry_data.comments,
            entered_by_id=current_user.id,
            entered_at=utc_now()
        )
        db.add(result)

    item.status = LabOrderItemStatus.PROCESSING
    db.commit()
    db.refresh(result)

    record_audit_log(
        db=db,
        action="LAB_RESULT_ENTERED",
        resource_type="LabResult",
        resource_id=str(result.id),
        user_id=current_user.id,
        details={
            "lab_order_item_id": item.id,
            "patient_id": result.patient_id,
            "test_definition_id": item.test_definition_id,
            "abnormal_flag": result.abnormal_flag.value,
            "value": result.value
        }
    )

    return result


def verify_result(
    db: Session,
    result_id: int,
    verify_data: ResultVerifyIn,
    current_user: User
) -> LabResult:
    """
    Verifies and finalizes a laboratory result with strict row-level locking.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks qualification to verify laboratory results."
        )

    result = db.query(LabResult).filter(
        LabResult.id == result_id
    ).with_for_update().first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory result with ID {result_id} not found."
        )

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found.")
        doc_id = current_user.doctor_profile.id
        order = result.order_item.lab_order
        if order.ordered_by_doctor_id != doc_id and not (order.encounter and order.encounter.attending_doctor_id == doc_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the attending or ordering physician may verify this result."
            )

    if result.status in [LabResultStatus.VERIFIED, LabResultStatus.FINAL]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This laboratory result has already been verified and finalized."
        )

    if result.status != LabResultStatus.ENTERED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot verify result with current status '{result.status.value}'. Must be ENTERED."
        )

    result.status = LabResultStatus.FINAL
    result.verified_by_id = current_user.id
    result.verified_at = utc_now()
    if verify_data.comments:
        result.comments = f"{result.comments}\nVerification: {verify_data.comments}".strip() if result.comments else verify_data.comments

    item = result.order_item
    item.status = LabOrderItemStatus.COMPLETED

    order = item.lab_order
    all_completed = all(i.status in [LabOrderItemStatus.COMPLETED, LabOrderItemStatus.CANCELLED] for i in order.items)
    if all_completed:
        order.status = LabOrderStatus.COMPLETED

    db.commit()
    db.refresh(result)

    record_audit_log(
        db=db,
        action="LAB_RESULT_VERIFIED",
        resource_type="LabResult",
        resource_id=str(result.id),
        user_id=current_user.id,
        details={
            "lab_order_item_id": result.lab_order_item_id,
            "patient_id": result.patient_id,
            "verified_by_id": current_user.id
        }
    )

    record_audit_log(
        db=db,
        action="LAB_RESULT_FINALIZED",
        resource_type="LabResult",
        resource_id=str(result.id),
        user_id=current_user.id,
        details={
            "lab_order_item_id": result.lab_order_item_id,
            "patient_id": result.patient_id,
            "status": result.status.value
        }
    )

    return result


def amend_result(
    db: Session,
    result_id: int,
    amend_data: ResultAmendIn,
    current_user: User
) -> LabResult:
    """
    Amends an already finalized laboratory result:
    v1 preserved as AMENDED; v2 created as new immutable FINAL row referencing v1.
    """
    if not is_lab_qualified(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks qualification to amend laboratory results."
        )

    original = db.query(LabResult).filter(
        LabResult.id == result_id
    ).with_for_update().first()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory result with ID {result_id} not found."
        )

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found.")
        doc_id = current_user.doctor_profile.id
        order = original.order_item.lab_order
        if order.ordered_by_doctor_id != doc_id and not (order.encounter and order.encounter.attending_doctor_id == doc_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the attending or ordering physician may amend this result."
            )

    if original.status != LabResultStatus.FINAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only finalized results can be amended. Current status is {original.status.value}."
        )

    original.status = LabResultStatus.AMENDED
    original.amendment_reason = amend_data.amendment_reason
    original.amended_at = utc_now()

    v2 = LabResult(
        lab_order_item_id=original.lab_order_item_id,
        patient_id=original.patient_id,
        value=amend_data.value,
        numeric_value=amend_data.numeric_value,
        unit=amend_data.unit if amend_data.unit is not None else original.unit,
        reference_range=amend_data.reference_range if amend_data.reference_range is not None else original.reference_range,
        abnormal_flag=amend_data.abnormal_flag,
        status=LabResultStatus.FINAL,
        comments=amend_data.comments,
        parent_result_id=original.id,
        version=original.version + 1,
        entered_by_id=current_user.id,
        entered_at=utc_now(),
        verified_by_id=current_user.id,
        verified_at=utc_now(),
        amendment_reason=amend_data.amendment_reason
    )
    db.add(v2)
    db.commit()
    db.refresh(v2)

    record_audit_log(
        db=db,
        action="LAB_RESULT_AMENDED",
        resource_type="LabResult",
        resource_id=str(v2.id),
        user_id=current_user.id,
        details={
            "parent_result_id": original.id,
            "new_result_id": v2.id,
            "lab_order_item_id": original.lab_order_item_id,
            "patient_id": original.patient_id,
            "reason": amend_data.amendment_reason
        }
    )

    return v2


def get_patient_lab_results(
    db: Session,
    patient_id: int,
    current_user: User
) -> List[LabResult]:
    """
    Retrieves laboratory results for a patient.
    Shields unverified results from PATIENT role.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found."
        )

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot view another patient's laboratory results."
            )
        return db.query(LabResult).filter(
            LabResult.patient_id == patient_id,
            LabResult.status == LabResultStatus.FINAL
        ).order_by(LabResult.created_at.desc()).all()

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found."
            )
        doctor_id = current_user.doctor_profile.id
        has_encounter = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.attending_doctor_id == doctor_id
        ).first() is not None

        has_order = db.query(LabOrder).filter(
            LabOrder.patient_id == patient_id,
            LabOrder.ordered_by_doctor_id == doctor_id
        ).first() is not None

        if not (has_encounter or has_order):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have an active clinical relationship with this patient."
            )

    return db.query(LabResult).filter(
        LabResult.patient_id == patient_id
    ).order_by(LabResult.created_at.desc()).all()


def get_lab_orders(
    db: Session,
    current_user: User,
    patient_id: Optional[int] = None,
    encounter_id: Optional[int] = None,
    status: Optional[LabOrderStatus] = None
) -> List[LabOrder]:
    """Retrieves laboratory orders with role-based filtering."""
    query = db.query(LabOrder)

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            return []
        query = query.filter(LabOrder.patient_id == current_user.patient_profile.id)
    elif current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            return []
        doctor_id = current_user.doctor_profile.id
        query = query.filter(LabOrder.ordered_by_doctor_id == doctor_id)

    if patient_id:
        if current_user.role == UserRole.PATIENT and current_user.patient_profile and current_user.patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
        query = query.filter(LabOrder.patient_id == patient_id)

    if encounter_id:
        query = query.filter(LabOrder.encounter_id == encounter_id)

    if status:
        query = query.filter(LabOrder.status == status)

    return query.order_by(LabOrder.created_at.desc()).all()


def get_lab_order_by_id(
    db: Session,
    order_id: int,
    current_user: User
) -> LabOrder:
    """Retrieves a single lab order by ID."""
    order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Laboratory order with ID {order_id} not found."
        )

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile or current_user.patient_profile.id != order.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )

    if current_user.role == UserRole.DOCTOR:
        if not current_user.doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        doc_id = current_user.doctor_profile.id
        if order.ordered_by_doctor_id != doc_id:
            if not (order.encounter and order.encounter.attending_doctor_id == doc_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You are not the ordering or attending physician."
                )

    return order
