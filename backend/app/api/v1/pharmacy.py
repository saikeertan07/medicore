"""
Pharmacy Safety & Clinical Drug Verification Endpoints.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.pharmacy_service import PharmacySafetyEngine

router = APIRouter(prefix="/pharmacy", tags=["Clinical Pharmacy & Medication Safety"])

class PrescriptionCheckRequest(BaseModel):
    proposed_drug: str = Field(..., min_length=2, description="Name of medication to be prescribed")
    dosage: str = Field(..., description="Dosage and route, e.g. '500mg PO BID'")
    active_medications: List[str] = Field(default=[], description="List of current active medications")
    patient_allergies: List[str] = Field(default=[], description="Documented drug allergies")
    patient_egfr: Optional[float] = Field(default=None, description="Current renal eGFR in mL/min/1.73m²")

@router.post("/verify-prescription")
def verify_prescription_safety(req: PrescriptionCheckRequest) -> Dict[str, Any]:
    """
    Performs real-time clinical safety verification for a proposed prescription.
    Checks drug-drug interactions, allergy cross-reactivity, and renal contraindications.
    """
    return PharmacySafetyEngine.evaluate_prescription_safety(
        proposed_drug=req.proposed_drug,
        dosage=req.dosage,
        active_medications=req.active_medications,
        patient_allergies=req.patient_allergies,
        egfr=req.patient_egfr
    )
