"""
Sepsis Early Warning & Surviving Sepsis Campaign 1-Hour Bundle Protocol Engine.
Calculates qSOFA scores, SIRS criteria, and activates standardized sepsis bundles.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class SepsisRiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE_SUSPECTED = "MODERATE_SUSPECTED"
    CRITICAL_SEPSIS_ALERT = "CRITICAL_SEPSIS_ALERT"
    SEPTIC_SHOCK = "SEPTIC_SHOCK"

class SepsisProtocolEngine:
    @staticmethod
    def calculate_qsofa(systolic_bp: int, respiration_rate: int, altered_mentation: bool) -> Dict[str, Any]:
        """
        Calculates quick SOFA (qSOFA) score (0 to 3).
        Score >= 2 indicates high risk of poor clinical outcomes and ICU admission.
        """
        sbp_point = 1 if systolic_bp <= 100 else 0
        rr_point = 1 if respiration_rate >= 22 else 0
        gcs_point = 1 if altered_mentation else 0

        score = sbp_point + rr_point + gcs_point
        is_positive = (score >= 2)

        return {
            "qsofa_score": score,
            "is_positive": is_positive,
            "criteria": {
                "hypotension_sbp_le_100": {"value": systolic_bp, "met": bool(sbp_point)},
                "tachypnea_rr_ge_22": {"value": respiration_rate, "met": bool(rr_point)},
                "altered_mentation": {"met": bool(gcs_point)}
            },
            "clinical_significance": "High probability of sepsis-related in-hospital mortality or ICU stay >3 days." if is_positive else "qSOFA negative; continue standard clinical observation."
        }

    @classmethod
    def evaluate_sepsis_protocol(
        cls,
        patient_id: int,
        systolic_bp: int,
        heart_rate: int,
        respiration_rate: int,
        temperature: float,
        altered_mentation: bool,
        suspected_infection_source: Optional[str] = None,
        serum_lactate: Optional[float] = None
    ) -> Dict[str, Any]:
        """Full Sepsis 3.0 Clinical Diagnostic and Escalation Bundle Generator."""
        qsofa = cls.calculate_qsofa(systolic_bp, respiration_rate, altered_mentation)

        # SIRS criteria calculation
        sirs_temp = (temperature > 38.0 or temperature < 36.0)
        sirs_hr = (heart_rate > 90)
        sirs_rr = (respiration_rate > 20)
        sirs_count = sum([sirs_temp, sirs_hr, sirs_rr])

        has_suspected_infection = bool(suspected_infection_source)

        # Risk Stratification
        if serum_lactate and serum_lactate >= 4.0 and systolic_bp < 90:
            risk = SepsisRiskLevel.SEPTIC_SHOCK
        elif qsofa["is_positive"] or (sirs_count >= 2 and has_suspected_infection):
            risk = SepsisRiskLevel.CRITICAL_SEPSIS_ALERT
        elif sirs_count >= 2 or has_suspected_infection:
            risk = SepsisRiskLevel.MODERATE_SUSPECTED
        else:
            risk = SepsisRiskLevel.LOW

        # 1-Hour Surviving Sepsis Bundle Checklist
        bundle_checklist = []
        if risk in (SepsisRiskLevel.CRITICAL_SEPSIS_ALERT, SepsisRiskLevel.SEPTIC_SHOCK):
            bundle_checklist = [
                {"step": 1, "action": "STAT Serum Lactate Draw", "status": "PENDING" if not serum_lactate else "COMPLETED", "target_time": "< 30 mins"},
                {"step": 2, "action": "Obtain Blood Cultures x 2 Sets Prior to Antibiotics", "status": "PENDING", "target_time": "< 45 mins"},
                {"step": 3, "action": "Administer Broad-Spectrum Empiric IV Antibiotics", "status": "PENDING", "target_time": "< 60 mins"},
                {"step": 4, "action": "Administer 30 mL/kg IV Crystalloid Fluid Bolus for Hypotension or Lactate >= 4.0", "status": "PENDING", "target_time": "< 60 mins"},
                {"step": 5, "action": "Initiate Vasopressor (Norepinephrine) if MAP < 65 mmHg Refractory to Fluids", "status": "PENDING", "target_time": "Immediate on failure"}
            ]

        return {
            "patient_id": patient_id,
            "risk_level": risk.value,
            "requires_emergency_code_sepsis": risk in (SepsisRiskLevel.CRITICAL_SEPSIS_ALERT, SepsisRiskLevel.SEPTIC_SHOCK),
            "qsofa": qsofa,
            "sirs_criteria_count": sirs_count,
            "infection_source": suspected_infection_source or "Unspecified / Under Investigation",
            "serum_lactate_mmol_L": serum_lactate,
            "one_hour_sepsis_bundle": bundle_checklist,
            "clinical_escalation_protocol": (
                "CODE SEPSIS ACTIVATED: Immediate bedside response by Attending Physician, ICU Fellow, and Rapid Response Nurse."
                if risk in (SepsisRiskLevel.CRITICAL_SEPSIS_ALERT, SepsisRiskLevel.SEPTIC_SHOCK)
                else "Routine sepsis monitoring: re-evaluate vitals in 2 hours."
            )
        }
