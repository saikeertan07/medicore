"""
Total Parenteral Nutrition (TPN) API Router.
Endpoints:
- POST /api/v1/tpn/calculate-prescription: Generates full parenteral nutrition formulation with BEE, GIR, and Ca/Phos precipitation safety check
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.tpn_nutrition_service import (
    TPNNutritionService,
    TPNOrderRequest
)
from app.api.v1.auth import get_current_user
from app.models.models import User

router = APIRouter(prefix="/tpn", tags=["Total Parenteral Nutrition (TPN) & Electrolytes"])

@router.post("/calculate-prescription")
def calculate_tpn(
    req: TPNOrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Calculates TPN caloric, macronutrient, fluid and electrolyte composition with safety verification."""
    try:
        result = TPNNutritionService.calculate_tpn_prescription(req)
        return {
            "status": "success",
            "evaluator_id": str(current_user.id),
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
