"""
Emergency Triage and NEWS2 Deterioration API Endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.triage_service import TriageEngine, VitalSigns

router = APIRouter(prefix="/triage", tags=["Clinical Triage & NEWS2"])

class VitalSignsSchema(BaseModel):
    respiration_rate: int = Field(..., ge=0, le=80, description="Breaths per minute")
    spo2: int = Field(..., ge=50, le=100, description="Oxygen saturation percentage")
    on_oxygen: bool = Field(default=False, description="Whether supplemental oxygen is active")
    systolic_bp: int = Field(..., ge=30, le=300, description="Systolic blood pressure in mmHg")
    heart_rate: int = Field(..., ge=20, le=250, description="Heart rate in bpm")
    consciousness: str = Field(default="ALERT", description="AVPU scale: ALERT, VOICE, PAIN, UNRESPONSIVE")
    temperature: float = Field(..., ge=25.0, le=45.0, description="Core temperature in Celsius")

class TriageAssessmentRequest(BaseModel):
    patient_id: Optional[int] = None
    chief_complaint: str = Field(..., min_length=2)
    anticipated_resources: int = Field(default=0, ge=0, le=10)
    vitals: VitalSignsSchema

@router.post("/calculate-news2")
def calculate_news2(vitals: VitalSignsSchema) -> Dict[str, Any]:
    """Calculates Royal College of Physicians NEWS2 score for clinical deterioration monitoring."""
    vital_obj = VitalSigns(
        respiration_rate=vitals.respiration_rate,
        spo2=vitals.spo2,
        on_oxygen=vitals.on_oxygen,
        systolic_bp=vitals.systolic_bp,
        heart_rate=vitals.heart_rate,
        consciousness=vitals.consciousness,
        temperature=vitals.temperature
    )
    return TriageEngine.evaluate_news2(vital_obj)

@router.post("/assess")
def assess_emergency_triage(req: TriageAssessmentRequest) -> Dict[str, Any]:
    """Evaluates both Emergency Severity Index (ESI Level 1-5) and NEWS2 score."""
    vital_obj = VitalSigns(
        respiration_rate=req.vitals.respiration_rate,
        spo2=req.vitals.spo2,
        on_oxygen=req.vitals.on_oxygen,
        systolic_bp=req.vitals.systolic_bp,
        heart_rate=req.vitals.heart_rate,
        consciousness=req.vitals.consciousness,
        temperature=req.vitals.temperature
    )
    news2_result = TriageEngine.evaluate_news2(vital_obj)
    esi_result = TriageEngine.evaluate_esi(vital_obj, req.chief_complaint, req.anticipated_resources)

    return {
        "patient_id": req.patient_id,
        "chief_complaint": req.chief_complaint,
        "esi": esi_result,
        "news2": news2_result,
        "requires_critical_care_alert": (news2_result["risk_level"] == "HIGH" or esi_result["esi_level"] == 1)
    }
