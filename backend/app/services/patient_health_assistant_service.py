"""
Feature 2 — Patient AI Health Assistant Service
Empathetic, plain-language health explanations strictly bound to the authenticated patient's records.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User, UserRole, Patient, Appointment, Prescription, LabResult
from app.ai.gateway import ai_gateway

EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "cannot breathe", "difficulty breathing",
    "severe bleeding", "unconscious", "stroke", "facial droop", "slurred speech",
    "overdose", "suicide", "emergency", "crushing pressure", "anaphylaxis"
]


class PatientHealthAssistantService:
    def answer_patient_query(self, db: Session, current_user: User, query: str) -> Dict[str, Any]:
        if current_user.role != UserRole.PATIENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can access the Patient Health Assistant.")
        
        patient = current_user.patient_profile
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found.")

        # 1. Emergency Safety Intercept
        q_lower = query.lower()
        if any(kw in q_lower for kw in EMERGENCY_KEYWORDS):
            return {
                "message": (
                    "⚠️ **URGENT MEDICAL EMERGENCY WARNING**\n\n"
                    "Your message indicates symptoms that could be life-threatening or require urgent medical evaluation. "
                    "**Do not wait for an online response.**\n\n"
                    "- Call **911** or your local emergency emergency services immediately.\n"
                    "- Go to the nearest hospital Emergency Department.\n"
                    "- MediCore Emergency Unit: Ground Floor, 24/7 Hotline: (555) 911-CORE."
                ),
                "is_emergency_alert": True,
                "references": []
            }

        # 2. Gather Patient's Own Verified Context
        prescriptions = db.query(Prescription).filter(Prescription.patient_id == patient.id).all()
        meds_summary = []
        for p in prescriptions:
            if isinstance(p.medications, list):
                for m in p.medications:
                    if isinstance(m, dict):
                        meds_summary.append(f"{m.get('name', 'Medication')} ({m.get('dosage', '')}, {m.get('frequency', '')}): {m.get('instructions') or p.instructions or 'Take as prescribed'}")
                    else:
                        meds_summary.append(f"{m}: {p.instructions or 'Take as prescribed'}")
            elif p.medication_name:
                meds_summary.append(f"{p.medication_name} ({p.dosage}, {p.frequency}): {p.instructions or 'Take as prescribed'}")

        upcoming_appts = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status.in_(["SCHEDULED", "CONFIRMED"])
        ).all()
        appts_summary = [f"Appointment with Dr. {a.doctor.user.full_name} ({a.doctor.department.name}) on {a.date} at {a.start_time}" for a in upcoming_appts if a.doctor and a.doctor.user and a.doctor.department]

        recent_labs = db.query(LabResult).filter(LabResult.patient_id == patient.id).order_by(LabResult.created_at.desc()).limit(5).all()
        labs_summary = [f"{r.order_item.test_definition.name}: {r.value} {r.unit or ''} ({r.abnormal_flag.value if r.abnormal_flag else 'Normal'})" for r in recent_labs if r.order_item and r.order_item.test_definition]

        clinical_context = (
            f"Patient: {patient.display_name}\n"
            f"Active Medications: {meds_summary}\n"
            f"Upcoming Appointments: {appts_summary}\n"
            f"Recent Laboratory Results: {labs_summary}\n"
        )

        def generate_patient_reply():
            if "medication" in q_lower or "medicine" in q_lower or "drug" in q_lower or "prescription" in q_lower:
                if meds_summary:
                    med_list = "\n".join(f"• **{m}**" for m in meds_summary)
                    return (
                        f"Here is information about your current prescribed medications:\n\n{med_list}\n\n"
                        "💡 *Always take your medications as directed by your doctor. Never adjust or stop medications on your own.*"
                    )
                return "You currently have no active prescription medications on file with MediCore."

            if "appointment" in q_lower or "visit" in q_lower:
                if appts_summary:
                    appt_list = "\n".join(f"• {a}" for a in appts_summary)
                    return f"Here are your upcoming appointments:\n\n{appt_list}\n\nPreparation tip: Please bring your photo ID, insurance card, and a list of questions for your doctor."
                return "You have no upcoming appointments scheduled. You can book an appointment in the Appointments tab."

            if "lab" in q_lower or "test" in q_lower or "result" in q_lower:
                if labs_summary:
                    lab_list = "\n".join(f"• {l}" for l in labs_summary)
                    return f"Here are your recent laboratory findings:\n\n{lab_list}\n\nIf you have questions about what these results mean for your health, your doctor will discuss them with you during your next visit."
                return "You have no recent laboratory results on record."

            return (
                f"Hello {patient.display_name}! I can help explain your prescribed medications, appointment schedules, "
                f"or general medical terminology in plain language. Please let me know how I can help today."
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=current_user,
            feature_name="patient_health_assistant",
            system_instruction=(
                "You are MediCore AI's Patient Health Assistant. Explain medical concepts, verified medications, "
                "and appointment preparation in warm, empathetic, plain language. "
                "Never diagnose conditions or tell patients to alter prescription dosages. "
                "Emphasize discussing questions with their doctor."
            ),
            user_prompt=query,
            untrusted_clinical_context=clinical_context,
            deterministic_fallback_fn=generate_patient_reply
        )

        return {
            "message": ai_res.get("data") or ai_res.get("error", "AI service unavailable"),
            "is_emergency_alert": False,
            "patient_id": patient.id,
            "disclaimer": "Informational assistant only. Not a medical diagnosis or medical directive."
        }


patient_health_assistant_service = PatientHealthAssistantService()
