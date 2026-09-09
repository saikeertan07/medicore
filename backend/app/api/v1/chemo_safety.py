"""
FastAPI Router for Chemotherapy and High-Alert Medication Double-Checks.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chemo_safety_service import ChemotherapySafetyEngine

router = APIRouter(prefix="/chemo-safety", tags=["Chemotherapy & High-Alert Medication Safety"])

class ChemoDoseCalculationRequest(BaseModel):
    drug_name: str
    height_cm: float = Field(..., gt=0)
    weight_kg: float = Field(..., gt=0)
    dose_per_m2_mg: float = Field(..., gt=0)
    prior_cumulative_dose_mg: float = Field(default=0.0, ge=0)

class DualSignoffRequest(BaseModel):
    calculated_dose_mg: float
    prepared_dose_mg: float
    nurse_1_id: int
    nurse_2_id: int

@router.post("/calculate-dose")
def calculate_bsa_chemo_dose(req: ChemoDoseCalculationRequest) -> Dict[str, Any]:
    """Calculates BSA and chemotherapy dose, checking cumulative lifetime toxicity limits."""
    return ChemotherapySafetyEngine.calculate_chemo_dose(
        height_cm=req.height_cm,
        weight_kg=req.weight_kg,
        dose_per_m2_mg=req.dose_per_m2_mg,
        drug_name=req.drug_name,
        prior_cumulative_dose_mg=req.prior_cumulative_dose_mg
    )

@router.post("/verify-dual-signoff")
def verify_high_alert_dual_signoff(req: DualSignoffRequest) -> Dict[str, Any]:
    """Verifies independent double-check by two distinct registered nurses."""
    return ChemotherapySafetyEngine.verify_dual_nursing_signoff(
        calculated_dose_mg=req.calculated_dose_mg,
        prepared_dose_mg=req.prepared_dose_mg,
        nurse_1_id=req.nurse_1_id,
        nurse_2_id=req.nurse_2_id
    )
