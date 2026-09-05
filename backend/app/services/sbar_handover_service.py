"""
Clinical SBAR (Situation, Background, Assessment, Recommendation) Shift Handover Engine.
Enforces standardized clinical communication between nursing shifts and doctor escalations.
Follows Joint Commission and WHO patient safety guidelines.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class SBARHandoverEngine:
    @classmethod
    def generate_sbar_handover(
        cls,
        patient_id: int,
        patient_name: str,
        room_number: str,
        attending_doctor: str,
        primary_diagnosis: str,
        admission_date: str,
        allergies: List[str],
        vitals: Dict[str, Any],
        active_medications: List[str],
        abnormal_labs: Optional[List[str]] = None,
        pending_orders: Optional[List[str]] = None,
        nurse_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synthesizes structured SBAR shift handover report for incoming clinical staff."""
        
        # 1. Situation (S)
        situation = {
            "patient_identification": f"{patient_name} (ID: {patient_id})",
            "room_location": room_number,
            "attending_physician": attending_doctor,
            "current_status_summary": f"Patient admitted with {primary_diagnosis} under care of {attending_doctor} in Room {room_number}."
        }

        # 2. Background (B)
        background = {
            "admission_date": admission_date,
            "primary_diagnosis": primary_diagnosis,
            "documented_allergies": allergies if allergies else ["No known drug allergies (NKDA)"],
            "surgical_or_clinical_history": "Full medical history accessible in electronic health record (EHR)."
        }

        # 3. Assessment (A)
        # Assess vital status
        news2_score = vitals.get("news2_score", 0)
        risk_level = "CRITICAL" if news2_score >= 7 else "URGENT" if news2_score >= 5 else "STABLE"

        assessment = {
            "current_vitals": vitals,
            "news2_deterioration_score": news2_score,
            "clinical_stability_risk": risk_level,
            "active_medication_regimen": active_medications,
            "flagged_abnormal_labs": abnormal_labs or ["All completed lab values within baseline limits."],
            "clinical_impression": nurse_notes or "Patient stable during current shift with active monitoring."
        }

        # 4. Recommendation (R)
        recommendations = []
        if news2_score >= 5:
            recommendations.append("Prioritize vital checks every 1 hour; escalate to attending if systolic BP < 90 or HR > 120.")
        else:
            recommendations.append("Continue routine vital telemetry every 4 to 6 hours as ordered.")

        if pending_orders:
            for order in pending_orders:
                recommendations.append(f"Follow up on pending clinical order: {order}")
        else:
            recommendations.append("No pending stat orders for next shift.")

        recommendations.append("Review morning metabolic panel and electrolytes once finalized by lab.")

        recommendation = {
            "action_items_for_incoming_shift": recommendations,
            "escalation_triggers": "Contact Medical Emergency Team (MET) if acute neurological change (AVPU deviation) or persistent hypoxia SpO2 < 92%."
        }

        return {
            "patient_id": patient_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sbar": {
                "situation": situation,
                "background": background,
                "assessment": assessment,
                "recommendation": recommendation
            },
            "handover_completed": False
        }
