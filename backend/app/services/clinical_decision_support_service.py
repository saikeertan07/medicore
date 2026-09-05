"""
Feature 4 — AI Clinical Decision Support (CDS) Service
Bounded, deterministic safety rules + clinical AI reasoning for healthcare professionals.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Doctor, Appointment, Encounter, 
    EncounterVitals, Prescription, LabResult, AbnormalFlag
)
from app.ai.gateway import ai_gateway

# Validated Authoritative Drug-Drug Interaction Rules
KNOWN_DRUG_INTERACTIONS = [
    {
        "drugs": ("warfarin", "aspirin"),
        "severity": "CRITICAL",
        "description": "Concurrent use significantly elevates major hemorrhage and gastrointestinal bleeding risk.",
        "management": "Avoid combination unless specifically indicated (e.g. mechanical valve); monitor INR closely."
    },
    {
        "drugs": ("lisinopril", "spironolactone"),
        "severity": "HIGH",
        "description": "Potassium-sparing diuretic combined with ACE inhibitor risks severe hyperkalemia and fatal arrhythmias.",
        "management": "Monitor serum potassium and renal function closely."
    },
    {
        "drugs": ("metformin", "contrast"),
        "severity": "HIGH",
        "description": "Iodinated radiocontrast combined with metformin risks acute renal impairment and lactic acidosis.",
        "management": "Withhold metformin 48 hours prior to contrast and resume only after renal function verified."
    },
    {
        "drugs": ("tramadol", "fluoxetine"),
        "severity": "HIGH",
        "description": "Serotonin syndrome risk and lowered seizure threshold due to CYP2D6 inhibition.",
        "management": "Avoid concurrent use or monitor for neuromuscular and autonomic hyperactivity."
    },
    {
        "drugs": ("ciprofloxacin", "theophylline"),
        "severity": "HIGH",
        "description": "Ciprofloxacin inhibits theophylline clearance, risking theophylline toxicity and seizures.",
        "management": "Reduce theophylline dosage by 30-50% and monitor serum levels."
    }
]

# Validated Allergy Cross-Reactivity Rules
ALLERGY_CROSS_REACTIVITY = {
    "penicillin": ["amoxicillin", "ampicillin", "piperacillin", "augmentin", "unasyn"],
    "sulfa": ["bactrim", "septra", "sulfamethoxazole", "sulfadiazine"],
    "nsaid": ["ibuprofen", "naproxen", "ketorolac", "diclofenac", "celecoxib", "aspirin"],
    "aspirin": ["ibuprofen", "naproxen", "ketorolac", "diclofenac"],
    "cephalosporin": ["cefazolin", "ceftriaxone", "cephalexin", "cefepime"]
}


class ClinicalDecisionSupportService:
    def evaluate_clinical_safety(
        self,
        db: Session,
        clinician: User,
        patient_id: int,
        candidate_medication: Optional[str] = None
    ) -> Dict[str, Any]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        deterministic_alerts = []
        probabilistic_suggestions = []

        # 1. Fetch active prescriptions
        active_prescriptions = db.query(Prescription).filter(
            Prescription.patient_id == patient_id
        ).all()
        med_names = []
        for p in active_prescriptions:
            if isinstance(p.medications, list):
                for m in p.medications:
                    if isinstance(m, dict) and "name" in m:
                        med_names.append(m["name"].lower().strip())
                    elif isinstance(m, str):
                        med_names.append(m.lower().strip())
            elif p.medication_name:
                med_names.append(p.medication_name.lower().strip())
        if candidate_medication:
            med_names.append(candidate_medication.lower().strip())

        # 2. Check Drug-Drug Interactions
        for rule in KNOWN_DRUG_INTERACTIONS:
            d1, d2 = rule["drugs"]
            has_d1 = any(d1 in m for m in med_names)
            has_d2 = any(d2 in m for m in med_names)
            if has_d1 and has_d2:
                deterministic_alerts.append({
                    "category": "DRUG_DRUG_INTERACTION",
                    "severity": rule["severity"],
                    "title": f"Interaction Alert: {d1.capitalize()} + {d2.capitalize()}",
                    "description": rule["description"],
                    "recommendation": rule["management"],
                    "rule_type": "DETERMINISTIC_EVIDENCE_BASED"
                })

        # 3. Check Drug-Allergy Conflicts
        history_text = (patient.medical_history_summary or "").lower() + " " + (patient.emergency_contact or "").lower()
        for allergen, contra_drugs in ALLERGY_CROSS_REACTIVITY.items():
            if allergen in history_text:
                for candidate in med_names:
                    if any(contra in candidate for contra in contra_drugs):
                        deterministic_alerts.append({
                            "category": "DRUG_ALLERGY_CONFLICT",
                            "severity": "CRITICAL",
                            "title": f"Allergy Conflict: {candidate.capitalize()} vs Known {allergen.capitalize()} Allergy",
                            "description": f"Patient has documented {allergen} sensitivity. Prescribing {candidate} risks severe anaphylaxis or hypersensitivity.",
                            "recommendation": "Select alternative therapeutic class with zero beta-lactam or cross-reactive overlap.",
                            "rule_type": "DETERMINISTIC_EVIDENCE_BASED"
                        })

        # 4. Check Abnormal Laboratory Biomarkers
        critical_labs = db.query(LabResult).filter(
            LabResult.patient_id == patient_id,
            LabResult.abnormal_flag.in_([AbnormalFlag.CRITICAL, AbnormalFlag.HIGH, AbnormalFlag.LOW])
        ).order_by(LabResult.created_at.desc()).limit(10).all()

        for lab in critical_labs:
            test_name = lab.order_item.test_definition.name if lab.order_item and lab.order_item.test_definition else "Lab Test"
            deterministic_alerts.append({
                "category": "ABNORMAL_LABORATORY_BIOMARKER",
                "severity": "CRITICAL" if lab.abnormal_flag == AbnormalFlag.CRITICAL else "HIGH",
                "title": f"Abnormal Lab: {test_name} ({lab.abnormal_flag.value})",
                "description": f"Measured value: {lab.value} {lab.unit or ''} (Normal Range: {lab.reference_range or 'N/A'}).",
                "recommendation": "Perform immediate clinical correlation and verify patient electrolyte/organ status.",
                "rule_type": "DETERMINISTIC_EVIDENCE_BASED"
            })

        # 5. Missing Intake Information
        if not patient.blood_group:
            probabilistic_suggestions.append("Blood group is unverified. Consider ordering type & screen if surgical intervention planned.")
        if not active_prescriptions:
            probabilistic_suggestions.append("No active medications documented. Confirm medication reconciliation was completed upon intake.")

        context_str = f"Patient: {patient.display_name}\nAlerts: {deterministic_alerts}\nSuggestions: {probabilistic_suggestions}"

        def generate_cds_summary():
            alert_count = len(deterministic_alerts)
            crit_count = sum(1 for a in deterministic_alerts if a["severity"] == "CRITICAL")
            return (
                f"**Clinical Decision Support Evaluation for {patient.display_name}**\n\n"
                f"- **Deterministic Safety Alerts**: {alert_count} active ({crit_count} Critical)\n"
                f"- **Documentation Notes**: {len(probabilistic_suggestions)}\n\n"
                f"All alerts must be clinically evaluated and overridden with legitimate medical justification if treatment continues."
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=clinician,
            feature_name="clinical_decision_support",
            system_instruction=(
                "You are MediCore AI's Clinical Decision Support module. Review deterministic safety flags. "
                "Synthesize clinical priorities without inventing new guidelines. "
                "Clearly distinguish rule-based safety flags from probabilistic suggestions."
            ),
            user_prompt=f"Evaluate clinical safety profile for patient {patient.display_name}.",
            untrusted_clinical_context=context_str,
            deterministic_fallback_fn=generate_cds_summary
        )

        return {
            "patient_id": patient.id,
            "deterministic_alerts": deterministic_alerts,
            "probabilistic_suggestions": probabilistic_suggestions,
            "total_alerts": len(deterministic_alerts),
            "critical_alerts": sum(1 for a in deterministic_alerts if a["severity"] == "CRITICAL"),
            "synthesis": ai_res["data"],
            "requires_clinician_acknowledgment": len(deterministic_alerts) > 0,
            "disclaimer": "Clinical Decision Support alerts are assistive safety checks. They do not replace physician judgment."
        }


clinical_decision_support_service = ClinicalDecisionSupportService()
