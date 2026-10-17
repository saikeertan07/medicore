"""
FastAPI Endpoints for HL7 FHIR R4 Interoperability.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.fhir_service import FHIRConverter

router = APIRouter(prefix="/fhir", tags=["HL7 FHIR R4 Interoperability"])

class FHIRPatientExportRequest(BaseModel):
    patient_id: int
    mrn: str
    first_name: str
    last_name: str
    dob: str = Field(..., description="YYYY-MM-DD")
    gender: str = Field(..., description="male, female, other")
    phone: Optional[str] = None
    email: Optional[str] = None

class FHIRObservationExportRequest(BaseModel):
    observation_id: str
    patient_id: int
    vital_name: str
    value: float

@router.post("/patient")
def export_fhir_patient(req: FHIRPatientExportRequest) -> Dict[str, Any]:
    """Generates a standard HL7 FHIR R4 Patient Resource."""
    return FHIRConverter.to_fhir_patient(
        patient_id=req.patient_id,
        mrn=req.mrn,
        first_name=req.first_name,
        last_name=req.last_name,
        dob=req.dob,
        gender=req.gender,
        phone=req.phone,
        email=req.email
    )

@router.post("/observation")
def export_fhir_observation(req: FHIRObservationExportRequest) -> Dict[str, Any]:
    """Generates a standard HL7 FHIR R4 Observation Resource with LOINC coding."""
    return FHIRConverter.to_fhir_observation(
        observation_id=req.observation_id,
        patient_id=req.patient_id,
        vital_name=req.vital_name,
        value=req.value
    )
