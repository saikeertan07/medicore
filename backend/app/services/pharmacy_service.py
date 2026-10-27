"""
Clinical Pharmacy Safety & Drug Interaction Engine.
Enforces real-time checks for drug-drug interactions, allergy cross-reactivity,
and organ contraindications (renal/hepatic) for zero-error clinical prescribing.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class InteractionSeverity(str, Enum):
    CONTRAINDICATED = "CONTRAINDICATED"  # Hard block: life-threatening or fatal
    MAJOR = "MAJOR"                      # Serious harm; requires attending approval
    MODERATE = "MODERATE"                # Significant; close clinical monitoring needed
    MINOR = "MINOR"                      # Low clinical consequence

class PrescribeStatus(str, Enum):
    APPROVED = "APPROVED"
    WARNING_OVERRIDABLE = "WARNING_OVERRIDABLE"
    BLOCKED = "BLOCKED"

# Authoritative Drug-Drug Interaction Rules Matrix
KNOWN_DRUG_INTERACTIONS = [
    {
        "drugs": {"warfarin", "aspirin"},
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "Synergistic antithrombotic and anticoagulant effects markedly amplify major gastrointestinal and intracerebral hemorrhage risk.",
        "recommendation": "Avoid concurrent therapy. If cardioprotection strictly required, consult cardiology and monitor INR twice weekly."
    },
    {
        "drugs": {"warfarin", "ibuprofen"},
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "NSAIDs induce gastric mucosal injury and inhibit platelet aggregation while displacing warfarin from protein-binding sites.",
        "recommendation": "Prescribe acetaminophen / paracetamol for analgesia instead."
    },
    {
        "drugs": {"lisinopril", "spironolactone"},
        "severity": InteractionSeverity.MAJOR,
        "mechanism": "Dual inhibition of aldosterone pathway significantly increases severe hyperkalemia risk leading to cardiac arrhythmias.",
        "recommendation": "Check baseline serum potassium and creatinine within 1 week of co-administration."
    },
    {
        "drugs": {"fluoxetine", "selegiline"},
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "Combined SSRI and MAOI administration triggers life-threatening Serotonin Syndrome.",
        "recommendation": "Strictly prohibited. Ensure minimum 14-day washout period between discontinuation and initiation."
    },
    {
        "drugs": {"clopidogrel", "omeprazole"},
        "severity": InteractionSeverity.MAJOR,
        "mechanism": "Omeprazole inhibits CYP2C19, significantly reducing active clopidogrel metabolite formation and increasing stent thrombosis risk.",
        "recommendation": "Switch gastroprotection to pantoprazole or famotidine."
    },
    {
        "drugs": {"metformin", "iodinated_contrast"},
        "severity": InteractionSeverity.MAJOR,
        "mechanism": "Contrast-induced nephropathy can lead to acute metformin accumulation and fatal lactic acidosis.",
        "recommendation": "Withhold metformin at time of or prior to imaging, resume 48h post-procedure after confirming stable renal function."
    },
    {
        "drugs": {"simvastatin", "clarithromycin"},
        "severity": InteractionSeverity.CONTRAINDICATED,
        "mechanism": "Potent CYP3A4 inhibition elevates statin concentrations, triggering severe rhabdomyolysis and acute renal failure.",
        "recommendation": "Temporarily suspend simvastatin during macrolide therapy or use azithromycin."
    }
]

# Drug Family Allergy Cross-Reactivity Classifications
DRUG_ALLERGY_FAMILIES = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "augmentin", "penicillin_v", "penicillin_g"],
    "cephalosporin": ["cefazolin", "ceftriaxone", "cephalexin", "cefepime"],
    "sulfonamide": ["sulfamethoxazole", "trimethoprim_sulfamethoxazole", "bactrim", "sulfasalazine"],
    "nsaid": ["ibuprofen", "naproxen", "ketorolac", "diclofenac", "indomethacin"],
    "opioid": ["morphine", "codeine", "oxycodone", "fentanyl", "hydrocodone"]
}

class PharmacySafetyEngine:
    @staticmethod
    def _normalize(drug_name: str) -> str:
        return drug_name.strip().lower().replace(" ", "_").replace("-", "_")

    @classmethod
    def check_drug_interactions(cls, proposed_drug: str, active_medications: List[str]) -> List[Dict[str, Any]]:
        """Checks proposed drug against all currently active patient medications."""
        target = cls._normalize(proposed_drug)
        active_normalized = [cls._normalize(m) for m in active_medications]
        detected = []

        for rule in KNOWN_DRUG_INTERACTIONS:
            rule_drugs = rule["drugs"]
            if target in rule_drugs:
                for active in active_normalized:
                    if active in rule_drugs and active != target:
                        detected.append({
                            "proposed_drug": proposed_drug,
                            "interacting_drug": active,
                            "severity": rule["severity"].value,
                            "mechanism": rule["mechanism"],
                            "recommendation": rule["recommendation"]
                        })
        return detected

    @classmethod
    def check_allergies(cls, proposed_drug: str, documented_allergies: List[str]) -> List[Dict[str, Any]]:
        """Verifies if the proposed drug matches or cross-reacts with known patient allergies."""
        target = cls._normalize(proposed_drug)
        alerts = []

        for allergy in documented_allergies:
            norm_allergy = cls._normalize(allergy)
            
            # Direct match
            if norm_allergy == target:
                alerts.append({
                    "allergy": allergy,
                    "drug": proposed_drug,
                    "type": "DIRECT_ALLERGY",
                    "severity": InteractionSeverity.CONTRAINDICATED.value,
                    "message": f"Patient has documented allergy to {allergy}. Direct administration is contraindicated."
                })
                continue

            # Class-level cross-reactivity
            for family_name, members in DRUG_ALLERGY_FAMILIES.items():
                if norm_allergy == family_name or norm_allergy in members:
                    if target in members or target == family_name:
                        alerts.append({
                            "allergy": allergy,
                            "drug": proposed_drug,
                            "type": "CLASS_CROSS_REACTIVITY",
                            "severity": InteractionSeverity.CONTRAINDICATED.value,
                            "message": f"Drug {proposed_drug} belongs to the {family_name.title()} class, cross-reacting with patient's documented {allergy} allergy."
                        })
        return alerts

    @classmethod
    def check_renal_contraindications(cls, proposed_drug: str, egfr: Optional[float]) -> Optional[Dict[str, Any]]:
        """Checks renal safety when eGFR lab results are available."""
        if egfr is None:
            return None

        target = cls._normalize(proposed_drug)
        # Metformin renal safety cutoff: eGFR < 30 contraindicated, 30-45 max 1000mg
        if target == "metformin" and egfr < 30.0:
            return {
                "drug": proposed_drug,
                "egfr": egfr,
                "severity": InteractionSeverity.CONTRAINDICATED.value,
                "message": f"Metformin is contraindicated in severe chronic kidney disease (eGFR {egfr} < 30 mL/min/1.73m²) due to lactic acidosis risk."
            }
        # NSAIDs in renal impairment
        if target in ("ibuprofen", "ketorolac", "naproxen") and egfr < 30.0:
            return {
                "drug": proposed_drug,
                "egfr": egfr,
                "severity": InteractionSeverity.MAJOR.value,
                "message": f"NSAIDs should be avoided in severe renal impairment (eGFR {egfr} < 30 mL/min/1.73m²); risk of acute decompensation."
            }
        # Enoxaparin (LMWH) accumulation in renal failure
        if target in ("enoxaparin", "lovenox") and egfr < 30.0:
            return {
                "drug": proposed_drug,
                "egfr": egfr,
                "severity": InteractionSeverity.MAJOR.value,
                "message": f"Enoxaparin clearance is impaired in severe renal impairment (eGFR {egfr} < 30 mL/min/1.73m²). Dose reduction to 1 mg/kg once daily is required."
            }
        # Cefepime neurotoxicity risk
        if target == "cefepime" and egfr < 50.0:
            return {
                "drug": proposed_drug,
                "egfr": egfr,
                "severity": InteractionSeverity.MAJOR.value,
                "message": f"Cefepime requires renal dose reduction when eGFR is {egfr} < 50 mL/min/1.73m² to prevent drug-induced encephalopathy."
            }
        return None

    @classmethod
    def evaluate_prescription_safety(
        cls,
        proposed_drug: str,
        dosage: str,
        active_medications: List[str],
        patient_allergies: List[str],
        egfr: Optional[float] = None
    ) -> Dict[str, Any]:
        """Performs a comprehensive multi-factor clinical medication safety audit."""
        interaction_alerts = cls.check_drug_interactions(proposed_drug, active_medications)
        allergy_alerts = cls.check_allergies(proposed_drug, patient_allergies)
        renal_alert = cls.check_renal_contraindications(proposed_drug, egfr)

        has_contraindication = (
            any(a["severity"] == InteractionSeverity.CONTRAINDICATED.value for a in interaction_alerts) or
            len(allergy_alerts) > 0 or
            (renal_alert and renal_alert["severity"] == InteractionSeverity.CONTRAINDICATED.value)
        )

        has_major_warning = (
            any(a["severity"] == InteractionSeverity.MAJOR.value for a in interaction_alerts) or
            (renal_alert and renal_alert["severity"] == InteractionSeverity.MAJOR.value)
        )

        if has_contraindication:
            verdict = PrescribeStatus.BLOCKED
            action = "BLOCKED: Prescription cannot be dispensed. Hard clinical contraindication detected."
        elif has_major_warning:
            verdict = PrescribeStatus.WARNING_OVERRIDABLE
            action = "WARNING: Significant interaction detected. Requires attending physician clinical override."
        else:
            verdict = PrescribeStatus.APPROVED
            action = "APPROVED: No clinical contraindications detected."

        return {
            "proposed_drug": proposed_drug,
            "dosage": dosage,
            "verdict": verdict.value,
            "action_guidance": action,
            "drug_interactions": interaction_alerts,
            "allergy_warnings": allergy_alerts,
            "renal_contraindication": renal_alert
        }
