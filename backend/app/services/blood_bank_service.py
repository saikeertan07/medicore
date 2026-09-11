"""
Blood Bank Compatibility, Crossmatching & Massive Transfusion Protocol (MTP) Engine.
Enforces strict immunohematology compatibility rules and manages emergency life-saving MTP coolers.
"""

from typing import Dict, Any, List, Optional
from enum import Enum

class BloodType(str, Enum):
    O_NEG = "O_NEG"
    O_POS = "O_POS"
    A_NEG = "A_NEG"
    A_POS = "A_POS"
    B_NEG = "B_NEG"
    B_POS = "B_POS"
    AB_NEG = "AB_NEG"
    AB_POS = "AB_POS"

# Packed Red Blood Cell (pRBC) Compatibility Table (Recipient -> Compatible Donors)
RBC_COMPATIBILITY = {
    BloodType.O_NEG: [BloodType.O_NEG],
    BloodType.O_POS: [BloodType.O_NEG, BloodType.O_POS],
    BloodType.A_NEG: [BloodType.O_NEG, BloodType.A_NEG],
    BloodType.A_POS: [BloodType.O_NEG, BloodType.O_POS, BloodType.A_NEG, BloodType.A_POS],
    BloodType.B_NEG: [BloodType.O_NEG, BloodType.B_NEG],
    BloodType.B_POS: [BloodType.O_NEG, BloodType.O_POS, BloodType.B_NEG, BloodType.B_POS],
    BloodType.AB_NEG: [BloodType.O_NEG, BloodType.A_NEG, BloodType.B_NEG, BloodType.AB_NEG],
    BloodType.AB_POS: [
        BloodType.O_NEG, BloodType.O_POS, BloodType.A_NEG, BloodType.A_POS,
        BloodType.B_NEG, BloodType.B_POS, BloodType.AB_NEG, BloodType.AB_POS
    ]
}

class BloodBankEngine:
    @classmethod
    def check_rbc_compatibility(cls, recipient_type: str, donor_unit_type: str) -> Dict[str, Any]:
        """Checks if a donor pRBC unit is immunologically safe to transfuse to recipient."""
        rec = BloodType(recipient_type.strip().upper())
        donor = BloodType(donor_unit_type.strip().upper())

        is_compatible = (donor in RBC_COMPATIBILITY[rec])
        return {
            "recipient_blood_type": rec.value,
            "donor_unit_blood_type": donor.value,
            "is_compatible": is_compatible,
            "action": "APPROVED_FOR_CROSSMATCH" if is_compatible else "CONTRAINDICATED_HEMOLYTIC_TRANSFUSION_RISK",
            "warning": None if is_compatible else f"FATAL ERROR: Transfusing {donor.value} to {rec.value} will cause acute hemolytic transfusion reaction."
        }

    @classmethod
    def generate_emergency_uncrossmatched_release(cls, patient_gender: str, patient_age: int) -> Dict[str, Any]:
        """Releases emergency uncrossmatched pRBCs in hemorrhagic shock before type & screen is complete."""
        # Females of childbearing potential (<50 yo) strictly receive O-Negative to prevent RhD alloimmunization
        is_female_childbearing = (patient_gender.lower() == "female" and patient_age < 50)
        recommended_type = BloodType.O_NEG if is_female_childbearing else BloodType.O_POS

        return {
            "emergency_release": True,
            "recommended_blood_type": recommended_type.value,
            "units_to_release": 2,
            "rationale": (
                "O-Negative mandatory for females of childbearing potential (<50 yo) to prevent anti-D hemolytic disease of the fetus."
                if is_female_childbearing
                else "O-Positive acceptable for adult males / non-childbearing females to conserve critical O-Negative emergency reserves."
            )
        }

    @classmethod
    def activate_massive_transfusion_cooler(cls, mtp_round: int, fibrinogen_mg_dl: Optional[float] = None) -> Dict[str, Any]:
        """
        Generates 1:1:1 balanced resuscitation cooler pack (pRBC : FFP : Platelets).
        Follows trauma critical care damage-control resuscitation guidelines.
        """
        prbc_units = 4
        ffp_units = 4
        platelets_apheresis = 1 if mtp_round % 2 == 1 else 0
        cryo_units = 10 if (fibrinogen_mg_dl and fibrinogen_mg_dl < 150) else 0

        return {
            "mtp_round": mtp_round,
            "cooler_contents": {
                "packed_red_blood_cells_units": prbc_units,
                "fresh_frozen_plasma_units": ffp_units,
                "platelets_apheresis_dose": platelets_apheresis,
                "cryoprecipitate_units": cryo_units
            },
            "adjunctive_hemostatics": [
                "Tranexamic Acid (TXA): Administer 1g IV over 10 minutes within 3 hours of trauma injury.",
                "Calcium Gluconate / Chloride: 1g IV for every 4 units of blood products to counter citrate toxicity."
            ],
            "laboratory_targets": {
                "temperature": "> 36.0 C (prevent hypothermic coagulopathy)",
                "pH": "> 7.20",
                "calcium_ionized": "> 1.1 mmol/L",
                "platelets": "> 50,000 /uL (> 100,000 for neurotrauma)",
                "fibrinogen": "> 150-200 mg/dL"
            }
        }
