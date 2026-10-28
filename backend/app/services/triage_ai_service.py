"""
Feature 11 — AI Triage Support Service
Computes National Early Warning Score 2 (NEWS2), determines Emergency Severity Index (ESI) acuity,
and applies deterministic override escalation rules for acute emergencies.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Encounter, 
    TriageAssessment, TriageAcuity, AuditLog
)
from app.ai.gateway import ai_gateway


class TriageAIService:
    def calculate_news2(self, vitals: Dict[str, Any]) -> int:
        score = 0

        # Respiratory rate (/min)
        rr = vitals.get("respiratory_rate")
        if rr is not None:
            if rr <= 8 or rr >= 25:
                score += 3
            elif 21 <= rr <= 24:
                score += 2
            elif 9 <= rr <= 11:
                score += 1

        # Supplemental Oxygen (Air or Oxygen?) - RCP NEWS2 standard (+2 if receiving supplemental O2)
        on_oxygen = bool(vitals.get("supplemental_oxygen", vitals.get("on_oxygen", False)))
        if on_oxygen:
            score += 2

        # SpO2 Scoring: Standard Scale 1 vs Hypercapnic Respiratory Failure Scale 2 (e.g. COPD)
        spo2 = vitals.get("oxygen_saturation")
        is_hypercapnic = bool(vitals.get("hypercapnic_failure", vitals.get("copd_scale_2", False)))

        if spo2 is not None:
            if is_hypercapnic:
                # Scale 2: Target 88-92%
                if spo2 <= 83:
                    score += 3
                elif 84 <= spo2 <= 85:
                    score += 2
                elif 86 <= spo2 <= 87:
                    score += 1
                elif 88 <= spo2 <= 92:
                    score += 0
                elif 93 <= spo2 <= 94:
                    if on_oxygen:
                        score += 1
                elif 95 <= spo2 <= 96:
                    if on_oxygen:
                        score += 2
                elif spo2 >= 97:
                    if on_oxygen:
                        score += 3
            else:
                # Standard Scale 1
                if spo2 <= 91:
                    score += 3
                elif 92 <= spo2 <= 93:
                    score += 2
                elif 94 <= spo2 <= 95:
                    score += 1

        # Systolic BP (mmHg)
        sbp = vitals.get("blood_pressure_systolic")
        if sbp is not None:
            if sbp <= 90 or sbp >= 220:
                score += 3
            elif 91 <= sbp <= 100:
                score += 2
            elif 101 <= sbp <= 110:
                score += 1

        # Pulse / Heart rate (bpm)
        hr = vitals.get("heart_rate")
        if hr is not None:
            if hr <= 40 or hr >= 131:
                score += 3
            elif 111 <= hr <= 130:
                score += 2
            elif 41 <= hr <= 50 or 91 <= hr <= 110:
                score += 1

        # Temperature (°C)
        temp = vitals.get("temperature_celsius")
        if temp is not None:
            if temp <= 35.0:
                score += 3
            elif temp >= 39.1:
                score += 2
            elif 35.1 <= temp <= 36.0 or 38.1 <= temp <= 39.0:
                score += 1

        # Consciousness (AVPU)
        consciousness = vitals.get("consciousness", "ALERT").upper()
        if consciousness != "ALERT":
            score += 3

        return score

    def evaluate_triage(
        self,
        db: Session,
        triage_staff: User,
        patient_id: int,
        chief_complaint: str,
        vitals: Dict[str, Any],
        encounter_id: Optional[int] = None
    ) -> TriageAssessment:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        # 1. Compute NEWS2 Score
        news2 = self.calculate_news2(vitals)

        # 2. Deterministic Escalation Overrides
        escalation_reason = None
        acuity = TriageAcuity.LEVEL_4_LESS_URGENT

        spo2 = vitals.get("oxygen_saturation")
        sbp = vitals.get("blood_pressure_systolic")
        hr = vitals.get("heart_rate")
        consciousness = vitals.get("consciousness", "ALERT").upper()

        cc_lower = chief_complaint.lower()

        # Level 1 Override: Immediate Life Threat
        if (
            consciousness in ["UNRESPONSIVE", "PAIN"] or
            (spo2 is not None and spo2 < 85) or
            (sbp is not None and sbp < 70) or
            any(w in cc_lower for w in ["cardiac arrest", "unresponsive", "severe anaphylaxis", "cyanosis", "agonal"])
        ):
            acuity = TriageAcuity.LEVEL_1_RESUSCITATION
            escalation_reason = "Deterministic Trigger: Severe hemodynamic compromise, profound hypoxemia, or altered mental status."
        # Level 2 Override: Emergent High Risk
        elif (
            news2 >= 7 or
            (spo2 is not None and spo2 < 92) or
            (sbp is not None and sbp < 90) or
            (hr is not None and hr > 130) or
            any(w in cc_lower for w in ["crushing chest pain", "severe asthma", "stroke", "slurred speech", "active gastrointestinal bleed"])
        ):
            acuity = TriageAcuity.LEVEL_2_EMERGENT
            escalation_reason = f"Deterministic Trigger: NEWS2 Score ({news2}) >= 7 or critical vital parameters indicating organ hypoperfusion."
        elif news2 >= 5:
            acuity = TriageAcuity.LEVEL_3_URGENT
            escalation_reason = f"NEWS2 Score ({news2}) >= 5: Urgent clinician bedside review required within 30 minutes."
        elif news2 >= 1:
            acuity = TriageAcuity.LEVEL_4_LESS_URGENT
            escalation_reason = f"NEWS2 Score ({news2}): Low clinical risk. Standard ward observation protocol."
        else:
            acuity = TriageAcuity.LEVEL_5_NON_URGENT
            escalation_reason = "All vital parameters within physiological baseline."

        # Save Assessment Record
        triage_record = TriageAssessment(
            patient_id=patient_id,
            encounter_id=encounter_id,
            assessed_by_id=triage_staff.id,
            news2_score=news2,
            acuity_level=acuity,
            chief_complaint=chief_complaint,
            vitals_snapshot=vitals,
            escalation_reason=escalation_reason,
            is_clinician_approved=False
        )
        db.add(triage_record)
        db.commit()
        db.refresh(triage_record)

        audit = AuditLog(
            user_id=triage_staff.id,
            action="TRIAGE_ASSESSMENT_RECORDED",
            resource_type="TriageAssessment",
            resource_id=str(triage_record.id),
            details={"patient_id": patient_id, "news2": news2, "acuity": acuity.value}
        )
        db.add(audit)
        db.commit()

        return triage_record


triage_ai_service = TriageAIService()
