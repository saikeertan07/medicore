"""
FastAPI Router for Clinical SBAR Shift Handover.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.sbar_handover_service import SBARHandoverEngine

router = APIRouter(prefix="/handover", tags=["SBAR Clinical Shift Handover"])

class SBARGenerateRequest(BaseModel):
    patient_id: int
    patient_name: str
    room_number: str
    attending_doctor: str
    primary_diagnosis: str
    admission_date: str
    allergies: List[str] = []
    vitals: Dict[str, Any]
    active_medications: List[str] = []
    abnormal_labs: Optional[List[str]] = None
    pending_orders: Optional[List[str]] = None
    nurse_notes: Optional[str] = None

@router.post("/generate-sbar")
def generate_sbar_report(req: SBARGenerateRequest) -> Dict[str, Any]:
    """Generates structured SBAR handover report for nursing shift transitions."""
    return SBARHandoverEngine.generate_sbar_handover(
        patient_id=req.patient_id,
        patient_name=req.patient_name,
        room_number=req.room_number,
        attending_doctor=req.attending_doctor,
        primary_diagnosis=req.primary_diagnosis,
        admission_date=req.admission_date,
        allergies=req.allergies,
        vitals=req.vitals,
        active_medications=req.active_medications,
        abnormal_labs=req.abnormal_labs,
        pending_orders=req.pending_orders,
        nurse_notes=req.nurse_notes
    )
