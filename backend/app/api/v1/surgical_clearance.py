"""
Surgical Pre-Op Clearance API Router.
Endpoints:
- POST /api/v1/surgical/rcri-clearance: Computes Lee's Revised Cardiac Risk Index (RCRI), ASA status & perioperative clearance decision
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.surgical_clearance_service import (
    SurgicalClearanceService,
    PreOpClearanceRequest
)
from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/surgical", tags=["Surgical Pre-Op & Perioperative Risk"])

@router.post("/rcri-clearance")
def calculate_surgical_clearance(
    req: PreOpClearanceRequest,
    current_user: User = Depends(get_current_user)
):
    """Evaluates surgical patient for perioperative cardiac risk (RCRI), ASA class, and clearance."""
    try:
        result = SurgicalClearanceService.evaluate_preop_risk(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
