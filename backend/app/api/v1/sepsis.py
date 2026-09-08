"""
FastAPI Router for Sepsis Protocol & Code Sepsis Escalations.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sepsis_engine import SepsisProtocolEngine

router = APIRouter(prefix="/sepsis", tags=["Sepsis 3.0 & Surviving Sepsis Campaign"])

class SepsisEvaluationRequest(BaseModel):
    patient_id: int
    systolic_bp: int = Field(..., ge=30, le=300)
    heart_rate: int = Field(..., ge=20, le=250)
    respiration_rate: int = Field(..., ge=4, le=80)
    temperature: float = Field(..., ge=25.0, le=45.0)
    altered_mentation: bool = Field(default=False)
    suspected_infection_source: Optional[str] = Field(default=None, description="e.g. Urinary tract, Pulmonary, Abdominal, Wound")
    serum_lactate: Optional[float] = Field(default=None, description="Lactate in mmol/L")

@router.post("/evaluate")
def evaluate_sepsis_risk(req: SepsisEvaluationRequest) -> Dict[str, Any]:
    """Calculates qSOFA, SIRS criteria, and triggers Code Sepsis 1-Hour Bundle."""
    return SepsisProtocolEngine.evaluate_sepsis_protocol(
        patient_id=req.patient_id,
        systolic_bp=req.systolic_bp,
        heart_rate=req.heart_rate,
        respiration_rate=req.respiration_rate,
        temperature=req.temperature,
        altered_mentation=req.altered_mentation,
        suspected_infection_source=req.suspected_infection_source,
        serum_lactate=req.serum_lactate
    )
