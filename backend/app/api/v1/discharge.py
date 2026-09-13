"""
Hospital Discharge & Readmission Risk API Router.
Endpoints:
- POST /api/v1/discharge/lace-score: Computes LACE 30-day readmission risk index
- POST /api/v1/discharge/generate-summary: Produces structured inpatient discharge summary packet with transition care plan
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.discharge_lace_service import (
    DischargeLACEService,
    LACEAssessmentInput,
    DischargeSummaryInput
)
from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/discharge", tags=["Discharge & Readmission Planning"])

@router.post("/lace-score")
def calculate_lace(
    req: LACEAssessmentInput,
    current_user: User = Depends(get_current_user)
):
    """Calculates LACE readmission risk score and recommended transition interventions."""
    try:
        result = DischargeLACEService.calculate_lace_score(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate-summary")
def generate_summary(
    req: DischargeSummaryInput,
    current_user: User = Depends(get_current_user)
):
    """Generates official hospital discharge summary packet."""
    try:
        result = DischargeLACEService.generate_discharge_packet(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
