"""
Ambient Clinical AI Scribe & Automated SOAP Note Generation Service.
Converts conversational encounter dialogues into structured clinical documentation
with ICD-10-CM diagnostic and CPT procedure coding suggestions.
"""

import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class ScribeNoteStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEWED_BY_NURSE = "REVIEWED_BY_NURSE"
    PHYSICIAN_SIGNED = "PHYSICIAN_SIGNED"

# Common ICD-10 Clinical Terminology Mapping
COMMON_ICD10_MAP = [
    {"keyword": "hypertension", "code": "I10", "description": "Essential (primary) hypertension"},
    {"keyword": "diabetes", "code": "E11.9", "description": "Type 2 diabetes mellitus without complications"},
    {"keyword": "chest pain", "code": "R07.9", "description": "Chest pain, unspecified"},
    {"keyword": "pneumonia", "code": "J18.9", "description": "Pneumonia, unspecified organism"},
    {"keyword": "asthma", "code": "J45.909", "description": "Unspecified asthma, uncomplicated"},
    {"keyword": "urinary tract infection", "code": "N39.0", "description": "Urinary tract infection, site not specified"},
    {"keyword": "headache", "code": "R51.9", "description": "Headache, unspecified"},
    {"keyword": "fever", "code": "R50.9", "description": "Fever, unspecified"},
    {"keyword": "copd", "code": "J44.9", "description": "Chronic obstructive pulmonary disease, unspecified"},
    {"keyword": "atrial fibrillation", "code": "I48.91", "description": "Unspecified atrial fibrillation"}
]

# Standard CPT Coding Logic Based on Complexity
CPT_CODES = {
    "outpatient_low": {"code": "99213", "description": "Office or other outpatient visit, low complexity (20-29 mins)"},
    "outpatient_moderate": {"code": "99214", "description": "Office or other outpatient visit, moderate complexity (30-39 mins)"},
    "outpatient_high": {"code": "99215", "description": "Office or other outpatient visit, high complexity (40-54 mins)"}
}

class AmbientScribeEngine:
    @staticmethod
    def match_icd10_codes(text: str) -> List[Dict[str, str]]:
        """Scans clinical text for diagnostic conditions and maps them to standard ICD-10 codes."""
        text_lower = text.lower()
        matched = []
        for item in COMMON_ICD10_MAP:
            if item["keyword"] in text_lower:
                matched.append({
                    "code": item["code"],
                    "description": item["description"],
                    "trigger_term": item["keyword"]
                })
        return matched

    @classmethod
    def generate_soap_note(
        cls,
        patient_id: int,
        encounter_id: int,
        raw_transcript: str,
        vitals_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Structures ambient conversational transcript into clinical SOAP documentation.
        Extracts Subjective, Objective, Assessment, Plan, and suggests billing codes.
        """
        lines = [l.strip() for l in raw_transcript.splitlines() if l.strip()]
        
        # Clinical pattern heuristics
        symptoms = []
        med_mentions = []
        exam_findings = []
        
        for line in lines:
            line_lower = line.lower()
            if any(term in line_lower for term in ["pain", "cough", "shortness of breath", "fever", "fatigue", "dizzy"]):
                symptoms.append(line)
            if any(term in line_lower for term in ["mg", "tablet", "prescribe", "started on", "daily", "bid", "tid"]):
                med_mentions.append(line)
            if any(term in line_lower for term in ["exam", "lungs", "heart", "abdomen", "clear", "murmur", "tender"]):
                exam_findings.append(line)

        # Subjective (S)
        subjective = {
            "chief_complaint": symptoms[0] if symptoms else "Patient presents for routine clinical consultation.",
            "history_of_present_illness": "\n".join(symptoms) if symptoms else "Patient reports ongoing symptoms as documented in audio transcript.",
            "patient_narrative": raw_transcript[:300] + ("..." if len(raw_transcript) > 300 else "")
        }

        # Objective (O)
        objective = {
            "vital_signs": vitals_summary or "Vitals reviewed and recorded in patient telemetry chart.",
            "physical_examination": "\n".join(exam_findings) if exam_findings else "General: Alert and oriented x3, in no acute distress."
        }

        # Assessment (A)
        icd_matches = cls.match_icd10_codes(raw_transcript)
        primary_dx = icd_matches[0]["description"] if icd_matches else "Clinical evaluation in progress"
        assessment = {
            "primary_diagnosis": primary_dx,
            "differential_diagnoses": [m["description"] for m in icd_matches[1:4]],
            "clinical_impression": "Clinical findings consistent with primary assessment. Patient stable for outpatient management."
        }

        # Plan (P)
        cpt = CPT_CODES["outpatient_moderate"] if len(symptoms) >= 2 else CPT_CODES["outpatient_low"]
        plan = {
            "pharmacotherapy": med_mentions if med_mentions else ["Continue current baseline medications as tolerated."],
            "diagnostics_ordered": ["Routine complete metabolic panel (CMP)", "Complete blood count (CBC)"] if len(symptoms) >= 2 else [],
            "patient_instructions": "Return to emergency department immediately if experiencing severe chest pain, shortness of breath, or sudden neurological deficits.",
            "follow_up": "Follow up in clinic in 2 to 4 weeks or as clinically indicated."
        }

        return {
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "status": ScribeNoteStatus.DRAFT.value,
            "soap": {
                "subjective": subjective,
                "objective": objective,
                "assessment": assessment,
                "plan": plan
            },
            "coding": {
                "suggested_icd10": icd_matches,
                "suggested_cpt": cpt
            },
            "compliance": {
                "is_physician_signed": False,
                "requires_physician_attestation": True,
                "legal_disclaimer": "AI-generated clinical draft. Must be reviewed, edited, and authenticated by a licensed attending physician prior to inclusion in the permanent medical record."
            }
        }
