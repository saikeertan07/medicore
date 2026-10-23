"""
Real-Time ICU Telemetry, Capacity Optimization & Emergency Ambulance Intake Routing.
Prevents hospital overflow, manages high-dependency ICU transfers,
and calculates step-down discharge readiness.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class WardType(str, Enum):
    ICU = "ICU"
    CCU = "CCU"
    EMERGENCY = "EMERGENCY"
    SURGICAL = "SURGICAL"
    GENERAL = "GENERAL"

class BedStatus(str, Enum):
    OCCUPIED = "OCCUPIED"
    AVAILABLE = "AVAILABLE"
    ISOLATION = "ISOLATION"
    MAINTENANCE = "MAINTENANCE"

@dataclass
class WardCapacity:
    ward_type: WardType
    total_beds: int
    occupied_beds: int
    isolation_beds: int

class BedTelemetryEngine:
    @staticmethod
    def calculate_utilization(total: int, occupied: int) -> float:
        if total <= 0:
            return 0.0
        return round((occupied / total) * 100.0, 1)

    @classmethod
    def evaluate_hospital_census(cls, wards: List[WardCapacity]) -> Dict[str, Any]:
        """Calculates hospital-wide bed occupancy and emergency divert telemetry."""
        total_beds = sum(w.total_beds for w in wards)
        total_occupied = sum(w.occupied_beds for w in wards)
        overall_utilization = cls.calculate_utilization(total_beds, total_occupied)

        ward_breakdown = {}
        icu_divert_required = False

        for w in wards:
            util = cls.calculate_utilization(w.total_beds, w.occupied_beds)
            avail = max(0, w.total_beds - w.occupied_beds)
            ward_breakdown[w.ward_type.value] = {
                "total": w.total_beds,
                "occupied": w.occupied_beds,
                "available": avail,
                "utilization_pct": util,
                "is_critical_capacity": (util >= 90.0)
            }
            if w.ward_type == WardType.ICU and util >= 90.0:
                icu_divert_required = True

        return {
            "overall_total_beds": total_beds,
            "overall_occupied": total_occupied,
            "overall_available": max(0, total_beds - total_occupied),
            "overall_utilization_pct": overall_utilization,
            "icu_divert_active": icu_divert_required,
            "emergency_status": "CRITICAL_DIVERT" if icu_divert_required else "NORMAL_OPERATIONS",
            "wards": ward_breakdown
        }

    @classmethod
    def evaluate_icu_discharge_readiness(
        cls,
        patient_id: int,
        hours_in_icu: int,
        current_news2_score: int,
        is_hemodynamically_stable: bool,
        on_vasopressors: bool
    ) -> Dict[str, Any]:
        """Determines if an ICU patient is clinically safe to step-down to a general ward."""
        if on_vasopressors:
            return {
                "patient_id": patient_id,
                "ready_for_step_down": False,
                "reason": "Active vasopressor / inotropic infusion requires continuous arterial line and ICU monitoring."
            }

        if current_news2_score >= 5 or not is_hemodynamically_stable:
            return {
                "patient_id": patient_id,
                "ready_for_step_down": False,
                "reason": f"Elevated NEWS2 score ({current_news2_score}) indicates active physiological deterioration risk."
            }

        if hours_in_icu >= 24 and current_news2_score <= 2 and is_hemodynamically_stable:
            return {
                "patient_id": patient_id,
                "ready_for_step_down": True,
                "target_ward": "GENERAL_STEP_DOWN",
                "reason": "Patient stable >24 hours with normalized NEWS2 score. Approved for bed transfer."
            }

        return {
            "patient_id": patient_id,
            "ready_for_step_down": False,
            "reason": "Continue ICU clinical observation until minimum 24-hour stability window is verified."
        }

    @classmethod
    def route_incoming_ambulance(
        cls,
        ambulance_id: str,
        triage_severity: str,
        requires_icu: bool,
        hospital_census: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluates whether to accept an emergency incoming ambulance or redirect."""
        icu_divert = hospital_census.get("icu_divert_active", False)
        ed_available = hospital_census.get("wards", {}).get("EMERGENCY", {}).get("available", 0)

        if requires_icu and icu_divert:
            return {
                "ambulance_id": ambulance_id,
                "status": "DIVERT",
                "recommended_action": "Divert ambulance to nearest regional trauma center. Local ICU at 90%+ saturation."
            }

        if ed_available <= 0:
            return {
                "ambulance_id": ambulance_id,
                "status": "HOLD_TRAUMA_BAY",
                "recommended_action": "Emergency bay full. Prepare hallway triage and activate rapid discharge protocol."
            }

        return {
            "ambulance_id": ambulance_id,
            "status": "ACCEPT",
            "assigned_bay": f"ED-RESUS-BAY-{(hash(ambulance_id) % 8) + 1}",
            "recommended_action": "Inbound accepted. Trauma / Resuscitation team notified."
        }
