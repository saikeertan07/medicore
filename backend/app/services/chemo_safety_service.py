"""
Chemotherapy & High-Alert Medication Safety Verification Engine.
Enforces Body Surface Area (BSA) dosing calculations, cumulative lifetime dose ceilings,
and dual-independent nursing sign-off verification to prevent catastrophic medication errors.
"""

import math
from typing import Dict, Any, List, Optional
from enum import Enum

class HighAlertVerificationStatus(str, Enum):
    APPROVED = "APPROVED"
    VARIANCE_EXCEEDED = "VARIANCE_EXCEEDED"
    LIFETIME_CEILING_BREACH = "LIFETIME_CEILING_BREACH"
    PENDING_SECOND_NURSE_CHECK = "PENDING_SECOND_NURSE_CHECK"

# Cumulative Lifetime Toxicity Ceilings
CUMULATIVE_LIFETIME_LIMITS_MG_M2 = {
    "doxorubicin": {"max_lifetime_mg_m2": 450.0, "toxicity": "Irreversible cardiomyopathy and congestive heart failure"},
    "daunorubicin": {"max_lifetime_mg_m2": 550.0, "toxicity": "Dose-dependent cardiotoxicity"},
    "bleomycin": {"max_lifetime_units": 400.0, "toxicity": "Fatal pulmonary fibrosis"}
}

class ChemotherapySafetyEngine:
    @staticmethod
    def calculate_bsa_mosteller(height_cm: float, weight_kg: float) -> float:
        """Calculates Body Surface Area (BSA) in m² using Mosteller formula."""
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Height and weight must be positive non-zero numbers.")
        bsa = math.sqrt((height_cm * weight_kg) / 3600.0)
        return round(bsa, 2)

    @classmethod
    def calculate_chemo_dose(
        cls,
        height_cm: float,
        weight_kg: float,
        dose_per_m2_mg: float,
        drug_name: str,
        prior_cumulative_dose_mg: float = 0.0
    ) -> Dict[str, Any]:
        """Calculates precise patient-specific chemotherapy dosage and checks lifetime toxicity limits."""
        bsa = cls.calculate_bsa_mosteller(height_cm, weight_kg)
        calculated_dose_mg = round(dose_per_m2_mg * bsa, 1)

        norm_drug = drug_name.strip().lower()
        ceiling_alert = None
        is_blocked = False

        if norm_drug in CUMULATIVE_LIFETIME_LIMITS_MG_M2:
            limit_info = CUMULATIVE_LIFETIME_LIMITS_MG_M2[norm_drug]
            if "max_lifetime_mg_m2" in limit_info:
                max_total_allowed_mg = limit_info["max_lifetime_mg_m2"] * bsa
                projected_total = prior_cumulative_dose_mg + calculated_dose_mg
                if projected_total > max_total_allowed_mg:
                    is_blocked = True
                    ceiling_alert = {
                        "is_exceeded": True,
                        "projected_total_mg": projected_total,
                        "max_allowed_mg": max_total_allowed_mg,
                        "toxicity_warning": limit_info["toxicity"],
                        "action": "BLOCKED: Proposed dose exceeds maximum lifetime cumulative limit. Severe organ toxicity hazard."
                    }

        return {
            "drug_name": drug_name,
            "patient_height_cm": height_cm,
            "patient_weight_kg": weight_kg,
            "calculated_bsa_m2": bsa,
            "ordered_dose_per_m2": dose_per_m2_mg,
            "calculated_total_dose_mg": calculated_dose_mg,
            "is_blocked_by_lifetime_limit": is_blocked,
            "lifetime_toxicity_alert": ceiling_alert
        }

    @classmethod
    def verify_dual_nursing_signoff(
        cls,
        calculated_dose_mg: float,
        prepared_dose_mg: float,
        nurse_1_id: int,
        nurse_2_id: int
    ) -> Dict[str, Any]:
        """Independent dual-nurse double check verification for high-alert medications."""
        if nurse_1_id == nurse_2_id:
            return {
                "status": "REJECTED",
                "message": "FATAL SAFETY VIOLATION: Independent double-check requires two distinct licensed nurses. Same ID provided for both sign-offs."
            }

        # Variance threshold (+/- 5% allowable margin)
        variance_pct = abs((prepared_dose_mg - calculated_dose_mg) / calculated_dose_mg) * 100.0
        if variance_pct > 5.0:
            return {
                "status": HighAlertVerificationStatus.VARIANCE_EXCEEDED.value,
                "variance_pct": round(variance_pct, 2),
                "message": f"Dose variance of {variance_pct:.1f}% exceeds strict 5.0% hospital safety threshold. Infusion blocked."
            }

        return {
            "status": HighAlertVerificationStatus.APPROVED.value,
            "variance_pct": round(variance_pct, 2),
            "nurse_1_verified": True,
            "nurse_2_verified": True,
            "message": "Dual independent verification satisfied. Medication released for administration."
        }
