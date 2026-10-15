"""
Unified API Routers for the 12 Advanced MediCore AI Clinical & Operational Features.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.models import User, UserRole

# Import the 12 AI Services
from app.services.clinical_assistant_service import clinical_assistant_service
from app.services.patient_health_assistant_service import patient_health_assistant_service
from app.services.clinical_rag_service import clinical_rag_service
from app.services.clinical_decision_support_service import clinical_decision_support_service
from app.services.documentation_copilot_service import documentation_copilot_service
from app.services.operations_assistant_service import operations_assistant_service
from app.services.lab_explainer_service import lab_report_explainer_service
from app.services.pharmacy_safety_service import pharmacy_safety_service
from app.services.multilingual_assistant_service import multilingual_assistant_service
from app.services.hospital_analytics_service import hospital_analytics_service
from app.services.triage_ai_service import triage_ai_service
from app.services.governance_service import governance_service

router = APIRouter(prefix="/ai", tags=["MediCore AI Suite (12 Production Features)"])


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class SynthesizeRequest(BaseModel):
    patient_id: int

class PatientChatRequest(BaseModel):
    query: str

class RAGQueryRequest(BaseModel):
    patient_id: int
    query: str
    limit: Optional[int] = 5

class CDSEvaluationRequest(BaseModel):
    patient_id: int
    candidate_medication: Optional[str] = None

class CopilotDraftRequest(BaseModel):
    patient_id: int
    draft_type: str  # SOAP_NOTE, DISCHARGE_SUMMARY, REFERRAL_LETTER, CLINICAL_HANDOFF
    clinical_inputs: Dict[str, Any]

class CopilotReviewRequest(BaseModel):
    approved: bool
    amended_content: Optional[str] = None

class AppointmentSearchRequest(BaseModel):
    query: str
    preferred_date: Optional[date] = None
    department_name: Optional[str] = None

class TranslationRequest(BaseModel):
    text_content: str
    target_language_code: str  # es, hi, fr, ar, en

class TriageEvaluationRequest(BaseModel):
    patient_id: int
    chief_complaint: str
    vitals: Dict[str, Any]
    encounter_id: Optional[int] = None

class KillSwitchRequest(BaseModel):
    enabled: bool
    reason: str = "Administrative Security Action"


# ------------------------------------------------------------------------------
# Feature 1: Unified AI Clinical Assistant
# ------------------------------------------------------------------------------
@router.post("/clinical-assistant/synthesize")
def synthesize_patient_record(
    req: SynthesizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN]))
):
    return clinical_assistant_service.synthesize_patient_record(
        db=db,
        clinician=current_user,
        patient_id=req.patient_id
    )


# ------------------------------------------------------------------------------
# Feature 2: Patient AI Health Assistant
# ------------------------------------------------------------------------------
@router.post("/patient-assistant/chat")
def patient_health_chat(
    req: PatientChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.PATIENT]))
):
    return patient_health_assistant_service.answer_patient_query(
        db=db,
        current_user=current_user,
        query=req.query
    )


# ------------------------------------------------------------------------------
# Feature 3: Medical Record Intelligence & RAG
# ------------------------------------------------------------------------------
@router.post("/rag/query")
def search_clinical_records(
    req: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return clinical_rag_service.search_patient_records(
        db=db,
        current_user=current_user,
        patient_id=req.patient_id,
        query=req.query,
        limit=req.limit or 5
    )

@router.post("/rag/reindex/{document_id}")
def reindex_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.STAFF]))
):
    count = clinical_rag_service.index_patient_document(db=db, document_id=document_id)
    return {"document_id": document_id, "chunks_indexed": count, "status": "COMPLETED"}


# ------------------------------------------------------------------------------
# Feature 4: AI Clinical Decision Support (CDS)
# ------------------------------------------------------------------------------
@router.post("/cds/evaluate")
def evaluate_clinical_decision_support(
    req: CDSEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN, UserRole.PHARMACIST]))
):
    return clinical_decision_support_service.evaluate_clinical_safety(
        db=db,
        clinician=current_user,
        patient_id=req.patient_id,
        candidate_medication=req.candidate_medication
    )


# ------------------------------------------------------------------------------
# Feature 5: AI Medical Documentation Copilot
# ------------------------------------------------------------------------------
@router.post("/copilot/draft")
def draft_medical_document(
    req: CopilotDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.NURSE, UserRole.ADMIN]))
):
    draft = documentation_copilot_service.draft_document(
        db=db,
        clinician=current_user,
        patient_id=req.patient_id,
        draft_type=req.draft_type,
        clinical_inputs=req.clinical_inputs
    )
    return {
        "draft_id": draft.id,
        "patient_id": draft.patient_id,
        "draft_type": draft.draft_type,
        "title": draft.title,
        "content": draft.content,
        "status": draft.status.value,
        "created_at": draft.created_at
    }

@router.post("/copilot/drafts/{draft_id}/review")
def review_copilot_draft(
    draft_id: int,
    req: CopilotReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN]))
):
    draft = documentation_copilot_service.review_and_approve_draft(
        db=db,
        clinician=current_user,
        draft_id=draft_id,
        approved=req.approved,
        amended_content=req.amended_content
    )
    return {
        "draft_id": draft.id,
        "status": draft.status.value,
        "approved_by_id": draft.approved_by_id,
        "approved_at": draft.approved_at,
        "content": draft.content
    }


# ------------------------------------------------------------------------------
# Feature 6: AI Appointment and Operations Assistant
# ------------------------------------------------------------------------------
@router.post("/operations/search-appointments")
def search_appointment_openings(
    req: AppointmentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return operations_assistant_service.search_available_appointments(
        db=db,
        current_user=current_user,
        query=req.query,
        preferred_date=req.preferred_date,
        department_name=req.department_name
    )

@router.get("/operations/no-show-trends")
def get_no_show_trends(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN, UserRole.STAFF]))
):
    return operations_assistant_service.compute_no_show_trends(db=db, admin_user=current_admin)


# ------------------------------------------------------------------------------
# Feature 7: AI Laboratory Report Explainer
# ------------------------------------------------------------------------------
@router.get("/lab-explainer/{lab_result_id}")
def explain_laboratory_result(
    lab_result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return lab_report_explainer_service.explain_lab_result(
        db=db,
        current_user=current_user,
        lab_result_id=lab_result_id
    )


# ------------------------------------------------------------------------------
# Feature 8: AI Pharmacy Safety Assistant
# ------------------------------------------------------------------------------
@router.post("/pharmacy-safety/evaluate/{patient_id}")
def evaluate_pharmacy_safety(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.PHARMACIST, UserRole.ADMIN, UserRole.NURSE]))
):
    return pharmacy_safety_service.evaluate_prescriptions_safety(
        db=db,
        clinician=current_user,
        patient_id=patient_id
    )


# ------------------------------------------------------------------------------
# Feature 9: Multilingual Patient Assistant
# ------------------------------------------------------------------------------
@router.post("/multilingual/translate")
def translate_clinical_text(
    req: TranslationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return multilingual_assistant_service.translate_patient_instructions(
        db=db,
        current_user=current_user,
        text_content=req.text_content,
        target_language_code=req.target_language_code
    )


# ------------------------------------------------------------------------------
# Feature 10: AI Hospital Analytics
# ------------------------------------------------------------------------------
@router.get("/hospital-analytics/executive-summary")
def get_executive_analytics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    return hospital_analytics_service.get_operational_analytics_summary(
        db=db,
        admin_user=current_admin
    )


# ------------------------------------------------------------------------------
# Feature 11: AI Triage Support
# ------------------------------------------------------------------------------
@router.post("/triage/evaluate")
def evaluate_patient_triage(
    req: TriageEvaluationRequest,
    db: Session = Depends(get_db),
    current_staff: User = Depends(require_roles([UserRole.NURSE, UserRole.DOCTOR, UserRole.ADMIN]))
):
    assessment = triage_ai_service.evaluate_triage(
        db=db,
        triage_staff=current_staff,
        patient_id=req.patient_id,
        chief_complaint=req.chief_complaint,
        vitals=req.vitals,
        encounter_id=req.encounter_id
    )
    return {
        "assessment_id": assessment.id,
        "patient_id": assessment.patient_id,
        "news2_score": assessment.news2_score,
        "acuity_level": assessment.acuity_level.value,
        "escalation_reason": assessment.escalation_reason,
        "chief_complaint": assessment.chief_complaint,
        "is_clinician_approved": assessment.is_clinician_approved,
        "created_at": assessment.created_at
    }


# ------------------------------------------------------------------------------
# Feature 12: AI Governance and Evaluation Dashboard
# ------------------------------------------------------------------------------
@router.get("/governance/telemetry")
def get_ai_governance_telemetry(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    return governance_service.get_governance_telemetry(db=db, admin_user=current_admin)

@router.post("/governance/kill-switch")
def toggle_ai_kill_switch(
    req: KillSwitchRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    return governance_service.toggle_kill_switch(
        db=db,
        admin_user=current_admin,
        enabled=req.enabled,
        reason=req.reason
    )
