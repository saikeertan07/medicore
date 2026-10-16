"""
Feature 5 — AI Medical Documentation Copilot Service
Drafts structured SOAP notes, discharge summaries, and referral letters with human-in-the-loop sign-off.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.datetime_utils import utc_now
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Doctor, Encounter, 
    AIDocumentDraft, DraftStatus, AuditLog
)
from app.ai.gateway import ai_gateway


class DocumentationCopilotService:
    def draft_document(
        self,
        db: Session,
        clinician: User,
        patient_id: int,
        draft_type: str,  # SOAP_NOTE, DISCHARGE_SUMMARY, REFERRAL_LETTER, CLINICAL_HANDOFF
        clinical_inputs: Dict[str, Any]
    ) -> AIDocumentDraft:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        doctor_id = clinician.doctor_profile.id if clinician.doctor_profile else None

        title = f"{draft_type.replace('_', ' ').title()} Draft - {patient.display_name} ({utc_now().strftime('%Y-%m-%d')})"

        def generate_draft_content():
            if draft_type == "SOAP_NOTE":
                subjective = clinical_inputs.get("subjective", "Patient presents for consultation. Chief complaint: Follow-up.")
                objective = clinical_inputs.get("objective", "Vitals stable. Physical examination unremarkable.")
                assessment = clinical_inputs.get("assessment", "Clinical status stable.")
                plan = clinical_inputs.get("plan", "Continue current treatment plan. Follow up in 4 weeks.")
                return (
                    f"### SOAP NOTE — CLINICAL DRAFT (UNREVIEWED)\n\n"
                    f"**SUBJECTIVE**:\n{subjective}\n\n"
                    f"**OBJECTIVE**:\n{objective}\n\n"
                    f"**ASSESSMENT**:\n{assessment}\n\n"
                    f"**PLAN**:\n{plan}\n\n"
                    f"---\n"
                    f"⚠️ *DRAFT DOCUMENT — Created by MediCore AI Copilot. Requires clinician sign-off prior to archiving.*"
                )
            elif draft_type == "DISCHARGE_SUMMARY":
                diagnosis = clinical_inputs.get("admission_diagnosis", "Acute medical care admission")
                course = clinical_inputs.get("hospital_course", "Patient responded favorably to therapy with resolution of acute symptoms.")
                discharge_meds = clinical_inputs.get("discharge_medications", "Resume pre-admission medications as tolerated.")
                instructions = clinical_inputs.get("patient_instructions", "Follow up with primary care physician in 7 to 10 days.")
                return (
                    f"### HOSPITAL DISCHARGE SUMMARY — CLINICAL DRAFT\n\n"
                    f"**PATIENT**: {patient.display_name} | **DOB**: {patient.date_of_birth or 'N/A'}\n"
                    f"**PRIMARY DIAGNOSIS**: {diagnosis}\n"
                    f"**HOSPITAL COURSE**: {course}\n"
                    f"**DISCHARGE MEDICATIONS**: {discharge_meds}\n"
                    f"**FOLLOW-UP INSTRUCTIONS**: {instructions}\n\n"
                    f"---\n"
                    f"⚠️ *DRAFT ONLY — Not an official discharge summary until electronically signed by attending physician.*"
                )
            elif draft_type == "REFERRAL_LETTER":
                specialty = clinical_inputs.get("target_specialty", "Specialist Consultation")
                reason = clinical_inputs.get("referral_reason", "Further evaluation and specialized diagnostic workup.")
                return (
                    f"### CLINICAL REFERRAL LETTER — DRAFT\n\n"
                    f"**TO**: Department of {specialty}\n"
                    f"**RE**: Consultation for {patient.display_name} (DOB: {patient.date_of_birth or 'N/A'})\n\n"
                    f"Dear Colleague,\n\n"
                    f"Thank you for evaluating this patient regarding: {reason}.\n\n"
                    f"Relevant Medical Background: {patient.medical_history_summary or 'See attached records'}.\n\n"
                    f"Sincerely,\n"
                    f"Dr. {clinician.full_name}\n"
                    f"MediCore Health System"
                )
            else:
                return f"### CLINICAL HANDOFF SUMMARY\n\nPatient: {patient.display_name}\nSummary: {clinical_inputs.get('notes', 'Routine handoff notes')}"

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=clinician,
            feature_name="documentation_copilot",
            system_instruction=(
                f"You are MediCore AI's Documentation Copilot. Draft a professional {draft_type}. "
                "Structure output with clinical precision. Do not fabricate vitals or unmentioned symptoms. "
                "Always affix a draft review disclaimer."
            ),
            user_prompt=f"Draft a {draft_type} for patient {patient.display_name}.",
            untrusted_clinical_context=str(clinical_inputs),
            deterministic_fallback_fn=generate_draft_content
        )

        draft = AIDocumentDraft(
            patient_id=patient_id,
            doctor_id=doctor_id,
            draft_type=draft_type,
            title=title,
            content=ai_res["data"],
            structured_data=clinical_inputs,
            status=DraftStatus.DRAFT
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)

        return draft

    def review_and_approve_draft(
        self,
        db: Session,
        clinician: User,
        draft_id: int,
        approved: bool,
        amended_content: Optional[str] = None
    ) -> AIDocumentDraft:
        draft = db.query(AIDocumentDraft).filter(AIDocumentDraft.id == draft_id).first()
        if not draft:
            raise HTTPException(status_code=404, detail="Document draft not found.")

        if approved:
            draft.status = DraftStatus.APPROVED
            draft.approved_by_id = clinician.id
            draft.approved_at = utc_now()
            if amended_content:
                draft.content = amended_content
        else:
            draft.status = DraftStatus.REJECTED

        db.commit()
        db.refresh(draft)

        audit = AuditLog(
            user_id=clinician.id,
            action="AI_DRAFT_REVIEW",
            resource_type="AIDocumentDraft",
            resource_id=str(draft.id),
            details={"status": draft.status.value, "approved": approved}
        )
        db.add(audit)
        db.commit()

        return draft


documentation_copilot_service = DocumentationCopilotService()
