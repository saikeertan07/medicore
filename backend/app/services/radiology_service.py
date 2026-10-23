"""
Radiology DICOM AI Critical Finding Alerting & Diagnostic Urgency Engine.
Detects life-threatening imaging findings (Tension Pneumothorax, Intracranial Bleed,
Aortic Dissection, Pulmonary Embolism) and enforces statutory verbal notification protocols.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum

class CriticalFindingSeverity(str, Enum):
    RED_ALERT_LIFE_THREATENING = "RED_ALERT_LIFE_THREATENING"   # Verbal notice < 15 mins
    ORANGE_ALERT_URGENT = "ORANGE_ALERT_URGENT"                 # Verbal notice < 60 mins
    ROUTINE = "ROUTINE"

CRITICAL_FINDINGS_CATALOG = [
    {
        "trigger": "pneumothorax",
        "condition": "Tension Pneumothorax",
        "severity": CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING,
        "required_action": "Stat verbal notification to attending physician. Immediate needle decompression / tube thoracostomy.",
        "statutory_time_limit_mins": 15
    },
    {
        "trigger": "intracranial hemorrhage",
        "condition": "Acute Intracranial Hemorrhage",
        "severity": CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING,
        "required_action": "Stat neurosurgical consultation. Reverse anticoagulation and prepare emergency CT angiogram.",
        "statutory_time_limit_mins": 15
    },
    {
        "trigger": "aortic dissection",
        "condition": "Acute Aortic Dissection",
        "severity": CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING,
        "required_action": "Stat cardiothoracic surgery consult. Tight blood pressure control with IV beta-blockers.",
        "statutory_time_limit_mins": 15
    },
    {
        "trigger": "pulmonary embolism",
        "condition": "Acute Pulmonary Embolism (Saddle / Lobar)",
        "severity": CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING,
        "required_action": "Evaluate for right ventricular strain; initiate therapeutic anticoagulation or thrombolysis.",
        "statutory_time_limit_mins": 30
    },
    {
        "trigger": "pneumoperitoneum",
        "condition": "Free Intraperitoneal Air (Perforated Viscus)",
        "severity": CriticalFindingSeverity.ORANGE_ALERT_URGENT,
        "required_action": "Stat general surgery consult for emergency exploratory laparotomy.",
        "statutory_time_limit_mins": 60
    }
]

class RadiologyAIEngine:
    @staticmethod
    def inspect_radiology_report(
        study_id: str,
        patient_id: int,
        modality: str,
        body_part: str,
        preliminary_radiologist_report: str
    ) -> Dict[str, Any]:
        """Analyzes imaging report for statutory critical findings requiring emergency communication."""
        report_lower = preliminary_radiologist_report.lower()
        sentences = re.split(r"[.\n;]", report_lower)
        flagged_alerts = []

        negation_prefixes = ["no ", "no acute ", "without ", "negative for ", "no evidence of ", "ruled out "]

        for item in CRITICAL_FINDINGS_CATALOG:
            trigger = item["trigger"]
            for sent in sentences:
                sent = sent.strip()
                if trigger in sent:
                    # Check if negated in this clause
                    is_negated = any(sent.startswith(neg) or f" {neg}" in sent for neg in negation_prefixes)
                    if not is_negated:
                        flagged_alerts.append({
                            "condition": item["condition"],
                            "severity": item["severity"].value,
                            "action_required": item["required_action"],
                            "statutory_time_limit_mins": item["statutory_time_limit_mins"]
                        })
                        break

        has_critical = any(a["severity"] == CriticalFindingSeverity.RED_ALERT_LIFE_THREATENING.value for a in flagged_alerts)

        return {
            "study_id": study_id,
            "patient_id": patient_id,
            "modality": modality.upper(),
            "body_part": body_part,
            "has_critical_findings": len(flagged_alerts) > 0,
            "requires_verbal_callback": has_critical,
            "flagged_findings": flagged_alerts,
            "communication_audit": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "verbal_read_back_completed": False,
                "attending_notified": False
            }
        }
