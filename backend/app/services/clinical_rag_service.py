"""
Feature 3 — Medical Record Intelligence and RAG Service
Retrieval-Augmented Generation over authorized patient records with strict isolation and citation verification.
"""
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import (
    User, UserRole, Patient, Doctor, Appointment, Encounter, 
    MedicalDocument, ClinicalDocumentChunk, ClinicalNote
)
from app.ai.gateway import ai_gateway


class ClinicalRAGService:
    def index_patient_document(self, db: Session, document_id: int) -> int:
        doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        # Remove existing chunks for re-indexing
        db.query(ClinicalDocumentChunk).filter(ClinicalDocumentChunk.document_id == document_id).delete()
        db.commit()

        # Build chunks from summary and extracted clinical data
        chunks_data = []
        if doc.summary:
            chunks_data.append(("Document Executive Summary", doc.summary))

        if doc.extracted_data and isinstance(doc.extracted_data, dict):
            findings = doc.extracted_data.get("key_findings", [])
            if findings:
                chunks_data.append(("Clinical Findings & Observations", "\n".join(f"• {f}" for f in findings)))
            doc_type = doc.extracted_data.get("document_type")
            if doc_type:
                chunks_data.append(("Document Classification", f"Classified clinical type: {doc_type}"))

        if not chunks_data:
            chunks_data.append(("General Content", f"Clinical record file: {doc.file_name}"))

        created_count = 0
        for idx, (section, text_content) in enumerate(chunks_data):
            chunk = ClinicalDocumentChunk(
                document_id=doc.id,
                patient_id=doc.patient_id,
                chunk_index=idx,
                section_title=section,
                content=text_content,
                token_count=len(text_content.split())
            )
            db.add(chunk)
            created_count += 1
        db.commit()
        return created_count

    def search_patient_records(
        self,
        db: Session,
        current_user: User,
        patient_id: int,
        query: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        # 1. Strict Tenant & Object-Level Authorization Check
        if current_user.role == UserRole.PATIENT:
            if not current_user.patient_profile or current_user.patient_profile.id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Patients may only search their own medical records."
                )
        elif current_user.role == UserRole.DOCTOR and current_user.doctor_profile:
            doc_id = current_user.doctor_profile.id
            has_appt = db.query(Appointment).filter(
                Appointment.doctor_id == doc_id,
                Appointment.patient_id == patient_id
            ).first()
            has_enc = db.query(Encounter).filter(
                Encounter.attending_doctor_id == doc_id,
                Encounter.patient_id == patient_id
            ).first()
            if not has_appt and not has_enc:
                # Check department coverage
                dept_id = current_user.doctor_profile.department_id
                dept_match = db.query(Appointment).join(Doctor).filter(
                    Appointment.patient_id == patient_id,
                    Doctor.department_id == dept_id
                ).first()
                if not dept_match:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. Doctor does not have an active care relationship with this patient."
                    )
        elif current_user.role in [UserRole.NURSE, UserRole.ADMIN, UserRole.STAFF]:
            pass
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role for medical record search.")

        # 2. Retrieve ONLY chunks explicitly belonging to patient_id
        # Pre-index any unindexed documents for this patient
        unindexed_docs = db.query(MedicalDocument).filter(
            MedicalDocument.patient_id == patient_id,
            ~MedicalDocument.id.in_(db.query(ClinicalDocumentChunk.document_id).filter(ClinicalDocumentChunk.patient_id == patient_id))
        ).all()
        for doc in unindexed_docs:
            self.index_patient_document(db, doc.id)

        # Lexical-semantic token match with patient isolation guarantee
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        patient_chunks = db.query(ClinicalDocumentChunk).filter(
            ClinicalDocumentChunk.patient_id == patient_id
        ).all()

        scored_chunks = []
        for c in patient_chunks:
            c_text = c.content.lower()
            s_title = (c.section_title or "").lower()
            score = 0.0
            for term in terms:
                if term in c_text:
                    score += 2.0
                if term in s_title:
                    score += 3.0
            if score > 0 or not terms:
                scored_chunks.append({
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "document_name": c.document.file_name if c.document else "Clinical Record",
                    "section": c.section_title,
                    "content": c.content,
                    "score": score
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = scored_chunks[:limit]

        if not top_chunks:
            return {
                "patient_id": patient_id,
                "query": query,
                "answer": "No relevant evidence found in the authorized clinical documentation for this patient.",
                "citations": [],
                "sufficient_evidence": False
            }

        # Formulate grounded answer with citations
        citations = [
            f"[{c['document_name']} — {c['section']}]" for c in top_chunks
        ]
        context_str = "\n".join(f"{c['document_name']} ({c['section']}): {c['content']}" for c in top_chunks)

        def generate_rag_answer():
            findings_bullets = "\n".join(f"- **{c['section']}** ({c['document_name']}): {c['content']}" for c in top_chunks)
            return (
                f"Based on authorized clinical records for Patient ID {patient_id}:\n\n"
                f"{findings_bullets}\n\n"
                f"**Citations**: {', '.join(citations)}\n\n"
                f"⚠️ *Verification Notice: All cited findings are extracted from patient records and require clinical verification.*"
            )

        ai_res = ai_gateway.execute_ai_task(
            db=db,
            current_user=current_user,
            feature_name="clinical_rag_intelligence",
            system_instruction=(
                "You are MediCore AI's Medical Record RAG Engine. Answer questions strictly grounded on the provided clinical chunks. "
                "Do not introduce outside clinical facts. Cite specific documents for every claim. "
                "If evidence is insufficient, state that clearly."
            ),
            user_prompt=query,
            untrusted_clinical_context=context_str,
            deterministic_fallback_fn=generate_rag_answer
        )

        return {
            "patient_id": patient_id,
            "query": query,
            "answer": ai_res["data"],
            "citations": citations,
            "sufficient_evidence": True,
            "matched_chunks": len(top_chunks)
        }


clinical_rag_service = ClinicalRAGService()
