"""
FastAPI Router for Blood Bank & Massive Transfusion Protocols.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.blood_bank_service import BloodBankEngine

router = APIRouter(prefix="/blood-bank", tags=["Blood Bank & Massive Transfusion Protocol"])

class CompatibilityCheckRequest(BaseModel):
    recipient_type: str = Field(..., description="e.g. O_POS, A_NEG, B_POS, AB_POS")
    donor_unit_type: str = Field(..., description="e.g. O_NEG, O_POS, A_POS")

class EmergencyUncrossmatchedRequest(BaseModel):
    patient_id: int
    gender: str
    age: int

class MTPCoolerRequest(BaseModel):
    patient_id: int
    trauma_bay: str
    mtp_round: int = Field(default=1, ge=1)
    fibrinogen_mg_dl: Optional[float] = None

@router.post("/check-compatibility")
def check_transfusion_compatibility(req: CompatibilityCheckRequest) -> Dict[str, Any]:
    """Verifies immunohematology compatibility between donor unit and recipient."""
    return BloodBankEngine.check_rbc_compatibility(req.recipient_type, req.donor_unit_type)

@router.post("/emergency-release")
def request_emergency_uncrossmatched_blood(req: EmergencyUncrossmatchedRequest) -> Dict[str, Any]:
    """Authorizes immediate uncrossmatched O-negative or O-positive blood release for hemorrhagic shock."""
    return BloodBankEngine.generate_emergency_uncrossmatched_release(req.gender, req.age)

@router.post("/activate-mtp")
def activate_mtp_round(req: MTPCoolerRequest) -> Dict[str, Any]:
    """Activates Massive Transfusion Protocol 1:1:1 cooler bundle."""
    return BloodBankEngine.activate_massive_transfusion_cooler(req.mtp_round, req.fibrinogen_mg_dl)
