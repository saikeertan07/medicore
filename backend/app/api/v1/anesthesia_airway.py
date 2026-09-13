"""
Anesthesia Airway Evaluation API Router.
Endpoints:
- POST /api/v1/anesthesia/airway-assessment: Predicts difficult airway risk (Mallampati & LEMON score) & generates rescue airway plan
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.anesthesia_airway_service import (
    AnesthesiaAirwayService,
    AirwayEvaluationRequest
)
from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/anesthesia", tags=["Anesthesia Pre-Evaluation & Airway Safety"])

@router.post("/airway-assessment")
def evaluate_airway(
    req: AirwayEvaluationRequest,
    current_user: User = Depends(get_current_user)
):
    """Evaluates Mallampati and LEMON score to determine difficult airway risk."""
    try:
        result = AnesthesiaAirwayService.evaluate_airway(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
