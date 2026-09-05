"""
Clinical Emergency Triage and NEWS2 Deterioration Engine.
Follows Royal College of Physicians (RCP) National Early Warning Score 2 (NEWS2) standards
and Emergency Severity Index (ESI Level 1-5) algorithms.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum

class NEWS2RiskLevel(str, Enum):
    LOW = "LOW"
    LOW_MEDIUM = "LOW_MEDIUM"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ESILevel(int, Enum):
    RESUSCITATION = 1
    EMERGENT = 2
    URGENT = 3
    LESS_URGENT = 4
    NON_URGENT = 5

@dataclass
class VitalSigns:
    respiration_rate: int          # breaths per minute
    spo2: int                      # percentage (Scale 1)
    on_oxygen: bool                # True if supplemental oxygen administered
    systolic_bp: int               # mmHg
    heart_rate: int                # beats per minute
    consciousness: str             # "ALERT", "VOICE", "PAIN", "UNRESPONSIVE"
    temperature: float             # Celsius

class TriageEngine:
    @staticmethod
    def calculate_respiration_score(rate: int) -> int:
        if rate <= 8 or rate >= 25:
            return 3
        if 21 <= rate <= 24:
            return 2
        if 9 <= rate <= 11:
            return 1
        return 0

    @staticmethod
    def calculate_spo2_score(spo2: int) -> int:
        if spo2 <= 91:
            return 3
        if 92 <= spo2 <= 93:
            return 2
        if 94 <= spo2 <= 95:
            return 1
        return 0

    @staticmethod
    def calculate_systolic_bp_score(sbp: int) -> int:
        if sbp <= 90 or sbp >= 220:
            return 3
        if 91 <= sbp <= 100:
            return 2
        if 101 <= sbp <= 110:
            return 1
        return 0

    @staticmethod
    def calculate_heart_rate_score(hr: int) -> int:
        if hr <= 40 or hr >= 131:
            return 3
        if 111 <= hr <= 130:
            return 2
        if (41 <= hr <= 50) or (91 <= hr <= 110):
            return 1
        return 0

    @staticmethod
    def calculate_consciousness_score(avpu: str) -> int:
        norm = avpu.strip().upper()
        if norm in ("A", "ALERT"):
            return 0
        return 3  # V, P, or U indicates acute neurological deviation

    @staticmethod
    def calculate_temperature_score(temp: float) -> int:
        if temp <= 35.0:
            return 3
        if temp >= 39.1:
            return 2
        if (35.1 <= temp <= 36.0) or (38.1 <= temp <= 39.0):
            return 1
        return 0

    @classmethod
    def evaluate_news2(cls, vitals: VitalSigns) -> Dict[str, Any]:
        """Calculates total NEWS2 score, component breakdowns, and clinical escalation guidance."""
        resp_score = cls.calculate_respiration_score(vitals.respiration_rate)
        spo2_score = cls.calculate_spo2_score(vitals.spo2)
        o2_score = 2 if vitals.on_oxygen else 0
        sbp_score = cls.calculate_systolic_bp_score(vitals.systolic_bp)
        hr_score = cls.calculate_heart_rate_score(vitals.heart_rate)
        avpu_score = cls.calculate_consciousness_score(vitals.consciousness)
        temp_score = cls.calculate_temperature_score(vitals.temperature)

        total_score = resp_score + spo2_score + o2_score + sbp_score + hr_score + avpu_score + temp_score
        has_extreme_single = any(s == 3 for s in [resp_score, spo2_score, sbp_score, hr_score, avpu_score, temp_score])

        # Clinical Risk Stratification
        if total_score >= 7:
            risk = NEWS2RiskLevel.HIGH
            response = "EMERGENCY: Immediate assessment by Medical Emergency Team (MET) / Critical Care Team. Continuous monitoring and ICU transfer consultation required."
        elif total_score in (5, 6) or has_extreme_single:
            risk = NEWS2RiskLevel.MEDIUM
            response = "URGENT: Urgent clinical review by attending physician within 30 minutes. Increase vital telemetry frequency to hourly."
        elif total_score >= 1:
            risk = NEWS2RiskLevel.LOW
            response = "LOW RISK: Nurse-led clinical review. Vital telemetry every 4 to 6 hours."
        else:
            risk = NEWS2RiskLevel.LOW
            response = "STABLE: Standard ward monitoring every 12 hours."

        return {
            "total_score": total_score,
            "risk_level": risk.value,
            "has_extreme_single_trigger": has_extreme_single,
            "clinical_escalation_protocol": response,
            "components": {
                "respiration": {"value": vitals.respiration_rate, "score": resp_score},
                "spo2": {"value": vitals.spo2, "score": spo2_score},
                "oxygen_therapy": {"on_oxygen": vitals.on_oxygen, "score": o2_score},
                "systolic_bp": {"value": vitals.systolic_bp, "score": sbp_score},
                "heart_rate": {"value": vitals.heart_rate, "score": hr_score},
                "consciousness": {"value": vitals.consciousness, "score": avpu_score},
                "temperature": {"value": vitals.temperature, "score": temp_score}
            }
        }

    @classmethod
    def evaluate_esi(cls, vitals: VitalSigns, chief_complaint: str, resources_needed: int) -> Dict[str, Any]:
        """Calculates Emergency Severity Index (ESI 1-5)."""
        avpu = vitals.consciousness.strip().upper()
        
        # Decision Point A: Is patient dying or in immediate arrest?
        if avpu == "UNRESPONSIVE" or vitals.respiration_rate <= 6 or vitals.heart_rate <= 30:
            return {
                "esi_level": ESILevel.RESUSCITATION.value,
                "category": "Resuscitation (Immediate)",
                "action": "Immediate physician intervention and resuscitation bay admission."
            }

        # Decision Point B: Is this a high-risk situation, confusion, lethargy, or severe distress?
        if avpu in ("VOICE", "PAIN") or "severe chest pain" in chief_complaint.lower() or "anaphylaxis" in chief_complaint.lower():
            return {
                "esi_level": ESILevel.EMERGENT.value,
                "category": "Emergent (Wait < 10 mins)",
                "action": "Urgent placement, rapid clinical assessment, and continuous monitoring."
            }

        # Decision Point C: Number of resources anticipated
        if resources_needed >= 2:
            # Check danger vitals
            if vitals.heart_rate > 100 or vitals.respiration_rate > 20 or vitals.spo2 < 92:
                return {
                    "esi_level": ESILevel.EMERGENT.value,
                    "category": "Emergent (Abnormal Vitals)",
                    "action": "Escalate to Level 2 due to abnormal physiological vitals."
                }
            return {
                "esi_level": ESILevel.URGENT.value,
                "category": "Urgent (Wait < 1 hour)",
                "action": "Allocate 2+ clinical resources (labs, imaging, IV medications)."
            }
        elif resources_needed == 1:
            return {
                "esi_level": ESILevel.LESS_URGENT.value,
                "category": "Less Urgent",
                "action": "Single resource procedure (e.g., standard X-ray or simple sutures)."
            }
        else:
            return {
                "esi_level": ESILevel.NON_URGENT.value,
                "category": "Non-Urgent",
                "action": "Routine examination and prescription renewal."
            }
