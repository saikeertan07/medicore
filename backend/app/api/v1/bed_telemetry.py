"""
FastAPI Router for Real-Time Bed Telemetry and Ambulance Intake.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.bed_telemetry_service import BedTelemetryEngine, WardCapacity, WardType

router = APIRouter(prefix="/bed-telemetry", tags=["Real-time Bed Telemetry & Ambulance Intake"])

class WardCapacityInput(BaseModel):
    ward_type: str = Field(..., description="ICU, CCU, EMERGENCY, SURGICAL, GENERAL")
    total_beds: int = Field(..., ge=1)
    occupied_beds: int = Field(..., ge=0)
    isolation_beds: int = Field(default=0, ge=0)

class CensusEvaluationRequest(BaseModel):
    wards: List[WardCapacityInput]

class StepDownEvaluationRequest(BaseModel):
    patient_id: int
    hours_in_icu: int
    current_news2_score: int
    is_hemodynamically_stable: bool
    on_vasopressors: bool

class AmbulanceIntakeRequest(BaseModel):
    ambulance_id: str
    triage_severity: str
    requires_icu: bool
    wards: List[WardCapacityInput]

@router.post("/census")
def evaluate_hospital_census(req: CensusEvaluationRequest) -> Dict[str, Any]:
    """Calculates overall bed utilization and checks ICU divert status."""
    ward_objs = [
        WardCapacity(
            ward_type=WardType(w.ward_type.upper()),
            total_beds=w.total_beds,
            occupied_beds=w.occupied_beds,
            isolation_beds=w.isolation_beds
        )
        for w in req.wards
    ]
    return BedTelemetryEngine.evaluate_hospital_census(ward_objs)

@router.post("/step-down-readiness")
def check_icu_step_down(req: StepDownEvaluationRequest) -> Dict[str, Any]:
    """Evaluates whether an ICU patient is clinically safe to step down to general ward."""
    return BedTelemetryEngine.evaluate_icu_discharge_readiness(
        patient_id=req.patient_id,
        hours_in_icu=req.hours_in_icu,
        current_news2_score=req.current_news2_score,
        is_hemodynamically_stable=req.is_hemodynamically_stable,
        on_vasopressors=req.on_vasopressors
    )

@router.post("/ambulance-intake")
def route_ambulance_intake(req: AmbulanceIntakeRequest) -> Dict[str, Any]:
    """Routes incoming emergency ambulances based on current real-time ICU/ED capacity."""
    ward_objs = [
        WardCapacity(
            ward_type=WardType(w.ward_type.upper()),
            total_beds=w.total_beds,
            occupied_beds=w.occupied_beds,
            isolation_beds=w.isolation_beds
        )
        for w in req.wards
    ]
    census = BedTelemetryEngine.evaluate_hospital_census(ward_objs)
    return BedTelemetryEngine.route_incoming_ambulance(
        ambulance_id=req.ambulance_id,
        triage_severity=req.triage_severity,
        requires_icu=req.requires_icu,
        hospital_census=census
    )
