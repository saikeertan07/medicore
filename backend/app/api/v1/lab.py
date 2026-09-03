from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    User, UserRole, LabOrder, LabOrderItem, LabSample, LabResult,
    LabOrderStatus, LabOrderItemStatus, LabSampleStatus, LabResultStatus
)
from app.schemas.schemas import (
    LabTestDefinitionOut, LabOrderCreate, LabOrderCancel, LabOrderOut,
    LabOrderItemOut, LabSampleOut, LabResultOut, SampleCollectIn,
    SampleReceiveIn, SampleRejectIn, ResultEntryIn, ResultVerifyIn, ResultAmendIn
)
from app.services.lab_service import (
    get_lab_test_catalog, create_lab_order, cancel_lab_order,
    collect_sample, receive_sample, reject_sample,
    enter_result, verify_result, amend_result,
    get_patient_lab_results, get_lab_orders, get_lab_order_by_id
)

router = APIRouter(tags=["Laboratory & Diagnostics"])


def result_to_out(res: LabResult) -> LabResultOut:
    test_def = res.order_item.test_definition if res.order_item else None
    return LabResultOut(
        id=res.id,
        order_item_id=res.lab_order_item_id,
        patient_id=res.patient_id,
        test_id=test_def.id if test_def else 0,
        test_name=test_def.name if test_def else None,
        test_code=test_def.code if test_def else None,
        value=res.value,
        numeric_value=float(res.numeric_value) if res.numeric_value is not None else None,
        unit=res.unit,
        reference_range=res.reference_range,
        abnormal_flag=res.abnormal_flag,
        status=res.status,
        comments=res.comments,
        parent_result_id=res.parent_result_id,
        entered_by_id=res.entered_by_id,
        entered_by_name=res.entered_by.full_name if res.entered_by else None,
        entered_at=res.entered_at,
        verified_by_id=res.verified_by_id,
        verified_by_name=res.verified_by.full_name if res.verified_by else None,
        verified_at=res.verified_at,
        amendment_reason=res.amendment_reason,
        amended_by_id=res.verified_by_id,  # doctor/staff who amended
        amended_at=res.amended_at,
        created_at=res.created_at,
        updated_at=res.updated_at
    )


def sample_to_out(sample: LabSample) -> LabSampleOut:
    return LabSampleOut(
        id=sample.id,
        accession_number=sample.accession_number,
        order_id=sample.lab_order_id,
        specimen_type=sample.sample_type,
        status=sample.status,
        collected_at=sample.collected_at,
        collected_by_id=sample.collected_by_id,
        collected_by_name=sample.collected_by.full_name if sample.collected_by else None,
        received_at=sample.received_at,
        received_by_id=sample.received_by_id,
        received_by_name=sample.received_by.full_name if sample.received_by else None,
        rejected_at=sample.rejected_at,
        rejected_by_id=sample.rejected_by_id,
        rejection_reason=sample.rejection_reason,
        created_at=sample.created_at,
        updated_at=sample.updated_at
    )


def item_to_out(item: LabOrderItem, shield_unverified: bool = False) -> LabOrderItemOut:
    result_out = None
    results = sorted(item.results, key=lambda r: r.created_at, reverse=True) if item.results else []
    if results:
        latest = results[0]
        if not (shield_unverified and latest.status == LabResultStatus.ENTERED):
            result_out = result_to_out(latest)

    return LabOrderItemOut(
        id=item.id,
        order_id=item.lab_order_id,
        test_id=item.test_definition_id,
        test_name=item.test_definition.name if item.test_definition else None,
        test_code=item.test_definition.code if item.test_definition else None,
        sample_id=item.sample_id,
        sample_accession=item.sample.accession_number if item.sample else None,
        status=item.status,
        notes=item.instructions,
        result=result_out,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


def order_to_out(order: LabOrder, shield_unverified: bool = False) -> LabOrderOut:
    return LabOrderOut(
        id=order.id,
        order_number=order.order_number,
        patient_id=order.patient_id,
        patient_name=order.patient.user.full_name if order.patient and order.patient.user else None,
        ordering_doctor_id=order.ordered_by_doctor_id,
        doctor_name=order.ordered_by_doctor.user.full_name if order.ordered_by_doctor and order.ordered_by_doctor.user else None,
        encounter_id=order.encounter_id,
        encounter_number=order.encounter.encounter_number if order.encounter else None,
        status=order.status,
        priority=order.priority,
        clinical_indication=order.clinical_indication,
        notes=order.clinical_indication,
        ordered_at=order.ordered_at,
        cancelled_at=order.cancelled_at,
        cancellation_reason=order.cancellation_reason,
        items=[item_to_out(i, shield_unverified) for i in order.items],
        samples=[sample_to_out(s) for s in order.samples],
        created_at=order.created_at,
        updated_at=order.updated_at
    )


@router.get("/tests", response_model=List[LabTestDefinitionOut])
def list_lab_tests(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve laboratory test catalog."""
    return get_lab_test_catalog(db=db, category=category, active_only=active_only)


@router.post("/orders", response_model=LabOrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: LabOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new laboratory order. Restricted to licensed physicians."""
    order = create_lab_order(db=db, order_data=order_data, current_user=current_user)
    return order_to_out(order)


@router.get("/orders", response_model=List[LabOrderOut])
def list_orders(
    patient_id: Optional[int] = None,
    encounter_id: Optional[int] = None,
    status: Optional[LabOrderStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List laboratory orders matching criteria."""
    orders = get_lab_orders(
        db=db,
        current_user=current_user,
        patient_id=patient_id,
        encounter_id=encounter_id,
        status=status
    )
    shield = (current_user.role == UserRole.PATIENT)
    return [order_to_out(o, shield_unverified=shield) for o in orders]


@router.get("/orders/{order_id}", response_model=LabOrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get laboratory order by ID."""
    order = get_lab_order_by_id(db=db, order_id=order_id, current_user=current_user)
    shield = (current_user.role == UserRole.PATIENT)
    return order_to_out(order, shield_unverified=shield)


@router.post("/orders/{order_id}/cancel", response_model=LabOrderOut)
def cancel_order(
    order_id: int,
    cancel_data: LabOrderCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel an active laboratory order."""
    order = cancel_lab_order(db=db, order_id=order_id, cancel_data=cancel_data, current_user=current_user)
    return order_to_out(order)


@router.post("/orders/{order_id}/samples", response_model=LabSampleOut, status_code=status.HTTP_201_CREATED)
def collect_order_sample(
    order_id: int,
    collect_data: SampleCollectIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Collect a specimen sample for laboratory order items."""
    sample = collect_sample(db=db, order_id=order_id, collect_data=collect_data, current_user=current_user)
    return sample_to_out(sample)


@router.post("/samples/{sample_id}/receive", response_model=LabSampleOut)
def receive_lab_sample(
    sample_id: int,
    receive_data: Optional[SampleReceiveIn] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a collected specimen as received by laboratory."""
    if receive_data is None:
        receive_data = SampleReceiveIn()
    sample = receive_sample(db=db, sample_id=sample_id, receive_data=receive_data, current_user=current_user)
    return sample_to_out(sample)


@router.post("/samples/{sample_id}/reject", response_model=LabSampleOut)
def reject_lab_sample(
    sample_id: int,
    reject_data: SampleRejectIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject an unsuitable specimen."""
    sample = reject_sample(db=db, sample_id=sample_id, reject_data=reject_data, current_user=current_user)
    return sample_to_out(sample)


@router.post("/order-items/{item_id}/results", response_model=LabResultOut, status_code=status.HTTP_201_CREATED)
def enter_item_result(
    item_id: int,
    entry_data: ResultEntryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enter a test result for an order item."""
    result = enter_result(db=db, item_id=item_id, entry_data=entry_data, current_user=current_user)
    return result_to_out(result)


@router.post("/results/{result_id}/verify", response_model=LabResultOut)
def verify_lab_result(
    result_id: int,
    verify_data: Optional[ResultVerifyIn] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Verify and finalize a laboratory result."""
    if verify_data is None:
        verify_data = ResultVerifyIn()
    result = verify_result(db=db, result_id=result_id, verify_data=verify_data, current_user=current_user)
    return result_to_out(result)


@router.post("/results/{result_id}/amend", response_model=LabResultOut)
def amend_lab_result(
    result_id: int,
    amend_data: ResultAmendIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Amend an already finalized laboratory result."""
    new_result = amend_result(db=db, result_id=result_id, amend_data=amend_data, current_user=current_user)
    return result_to_out(new_result)


@router.get("/patients/{patient_id}/results", response_model=List[LabResultOut])
def get_patient_results(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve laboratory results for a patient with patient confidentiality protection."""
    results = get_patient_lab_results(db=db, patient_id=patient_id, current_user=current_user)
    return [result_to_out(r) for r in results]
