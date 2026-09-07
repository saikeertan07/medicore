"""
Code Blue & Cardiac Arrest Resuscitation Engine (AHA ACLS 2025/2026 Guidelines).
Automates resuscitation algorithms: rhythm classification (Shockable vs Non-Shockable),
Epinephrine/Amiodarone drug timers, 2-minute CPR cycle cadence, and reversible H's & T's differential diagnosis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum

class CardiacRhythm(str, Enum):
    VF = "VENTRICULAR_FIBRILLATION"
    PVT = "PULSELESS_VENTRICULAR_TACHYCARDIA"
    ASYSTOLE = "ASYSTOLE"
    PEA = "PULSELESS_ELECTRICAL_ACTIVITY"

class RhythmCategory(str, Enum):
    SHOCKABLE = "SHOCKABLE"
    NON_SHOCKABLE = "NON_SHOCKABLE"

REVERSIBLE_CAUSES_H_AND_T = {
    "Hs": [
        {"cause": "Hypovolemia", "intervention": "Rapid IV/IO crystalloid infusion, check for hidden hemorrhage"},
        {"cause": "Hypoxia", "intervention": "Ensure 100% FiO2, bag-valve-mask or endotracheal tube placement, check chest rise"},
        {"cause": "Hydrogen ion (Acidosis)", "intervention": "Adequate ventilation, consider sodium bicarbonate for pre-existing acidosis"},
        {"cause": "Hypo/Hyperkalemia", "intervention": "Calcium chloride/gluconate for hyperkalemia, potassium infusion for hypokalemia"},
        {"cause": "Hypothermia", "intervention": "Active internal/external rewarming protocol"}
    ],
    "Ts": [
        {"cause": "Tension pneumothorax", "intervention": "Immediate needle thoracostomy (2nd intercostal midclavicular or 5th anterior axillary)"},
        {"cause": "Tamponade (Cardiac)", "intervention": "Emergency ultrasound-guided pericardiocentesis"},
        {"cause": "Toxins", "intervention": "Review medication history, administer specific antidotes (e.g. Naloxone for opioids)"},
        {"cause": "Thrombosis (Pulmonary)", "intervention": "Consider emergency systemic thrombolysis or surgical embolectomy"},
        {"cause": "Thrombosis (Coronary)", "intervention": "Post-ROSC emergent coronary angiography / cath lab transfer"}
    ]
}

class ACLSResuscitationEngine:
    @staticmethod
    def classify_rhythm(rhythm: str) -> RhythmCategory:
        r = rhythm.strip().upper()
        if r in [CardiacRhythm.VF.value, CardiacRhythm.PVT.value, "VF", "PVT", "V-FIB", "V-TACH"]:
            return RhythmCategory.SHOCKABLE
        return RhythmCategory.NON_SHOCKABLE

    @classmethod
    def evaluate_resuscitation_step(
        cls,
        current_rhythm: str,
        cpr_cycle_number: int,
        total_shocks_delivered: int,
        epinephrine_doses_given: int,
        amiodarone_doses_given: int
    ) -> Dict[str, Any]:
        """Calculates immediate next clinical actions based on AHA ACLS algorithmic state machine."""
        category = cls.classify_rhythm(current_rhythm)
        actions = []
        medications_due = []

        if category == RhythmCategory.SHOCKABLE:
            actions.append(f"SHOCK RECOMMENDED: Deliver defibrillation shock #{total_shocks_delivered + 1} (120-200J Biphasic).")
            actions.append("Immediately resume high-quality CPR (100-120 bpm, 2-2.4 in depth) for 2 minutes without checking pulse.")

            # Epinephrine given every 3-5 minutes (typically after 2nd shock)
            if cpr_cycle_number >= 2 and (cpr_cycle_number % 2 == 0):
                medications_due.append({
                    "drug": "Epinephrine",
                    "dose": "1 mg IV/IO",
                    "frequency": "Every 3-5 minutes",
                    "instructions": "Follow with 20 mL normal saline flush and elevate extremity."
                })

            # Amiodarone for refractory VF/pVT after 3rd shock
            if total_shocks_delivered >= 2:
                if amiodarone_doses_given == 0:
                    medications_due.append({
                        "drug": "Amiodarone (First Dose)",
                        "dose": "300 mg IV/IO bolus",
                        "instructions": "Administer rapid IV bolus for shock-refractory VF/pVT."
                    })
                elif amiodarone_doses_given == 1:
                    medications_due.append({
                        "drug": "Amiodarone (Second Dose)",
                        "dose": "150 mg IV/IO bolus",
                        "instructions": "Final 150 mg bolus for persistent refractory shockable rhythm."
                    })

        else: # NON_SHOCKABLE (Asystole / PEA)
            actions.append("NO SHOCK: Asystole/PEA rhythm is not shockable. Resume immediate continuous CPR.")
            # Epinephrine ASAP for non-shockable rhythms
            medications_due.append({
                "drug": "Epinephrine",
                "dose": "1 mg IV/IO STAT",
                "frequency": "Every 3-5 minutes",
                "instructions": "Administer immediately as early epinephrine dramatically improves survival in non-shockable rhythms."
            })

        return {
            "rhythm_evaluated": current_rhythm,
            "category": category.value,
            "is_shockable": (category == RhythmCategory.SHOCKABLE),
            "cpr_cycle": cpr_cycle_number,
            "next_cycle_countdown_seconds": 120,
            "immediate_actions": actions,
            "medications_due": medications_due,
            "reversible_causes": REVERSIBLE_CAUSES_H_AND_T
        }
