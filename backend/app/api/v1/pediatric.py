"""
Pediatric and Neonatal Emergency API Router.
Endpoints:
- POST /api/v1/pediatric/apgar: Calculates 1-min / 5-min APGAR score & resuscitation protocol
- POST /api/v1/pediatric/broselow-dosing: Computes Broselow emergency zone, weight-based drug doses, defib Joules & ETT sizes
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.pediatric_safety_service import (
    PediatricSafetyService,
    APGARAssessment,
    PediatricEmergencyRequest
)
from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/pediatric", tags=["Pediatric & Neonatal Safety"])

@router.post("/apgar")
def score_apgar(
    assessment: APGARAssessment,
    current_user: User = Depends(get_current_user)
):
    """Calculates APGAR score and provides neonatal resuscitation recommendations."""
    try:
        result = PediatricSafetyService.calculate_apgar(assessment)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/broselow-dosing")
def calculate_broselow(
    req: PediatricEmergencyRequest,
    current_user: User = Depends(get_current_user)
):
    """Calculates Broselow color zone, emergency medication doses, ETT sizes and defib Joules."""
    try:
        result = PediatricSafetyService.calculate_pediatric_dosing(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
