import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import MedicalDocument, User, UserRole, Appointment, Doctor, Encounter
from app.schemas.schemas import MedicalDocumentOut
from app.services.document_service import validate_and_save_upload, query_document
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/documents", tags=["Medical Documents"])

def verify_document_access(doc: MedicalDocument, user: User, db: Session) -> None:
    if user.role == UserRole.PATIENT:
        if not user.patient_profile or doc.patient_id != user.patient_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Access denied. Patients may only access their own documents."
            )
    elif user.role in [UserRole.RECEPTIONIST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied. Reception staff are not authorized to view clinical medical documents."
        )
    elif user.role == UserRole.DOCTOR and user.doctor_profile:
        doc_id = user.doctor_profile.id
        has_appointment = db.query(Appointment).filter(
            Appointment.doctor_id == doc_id,
            Appointment.patient_id == doc.patient_id
        ).first()
        has_encounter = db.query(Encounter).filter(
            Encounter.attending_doctor_id == doc_id,
            Encounter.patient_id == doc.patient_id
        ).first()
        if not has_appointment and not has_encounter:
            # Check department clinical coverage match
            dept_id = user.doctor_profile.department_id
            dept_match = db.query(Appointment).join(Doctor).filter(
                Appointment.patient_id == doc.patient_id,
                Doctor.department_id == dept_id
            ).first()
            if not dept_match:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Doctor does not have an active care relationship with this patient."
                )
    elif user.role in [UserRole.NURSE, UserRole.ADMIN, UserRole.STAFF]:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

def doc_to_out(doc: MedicalDocument) -> MedicalDocumentOut:
    return MedicalDocumentOut(
        id=doc.id,
        patient_id=doc.patient_id,
        patient_name=doc.patient.user.full_name if doc.patient and doc.patient.user else "Unknown",
        file_name=doc.file_name,
        file_type=doc.file_type,
        file_size=doc.file_size,
        status=doc.status,
        summary=doc.summary,
        extracted_data=doc.extracted_data,
        tags=doc.tags,
        created_at=doc.created_at
    )

@router.post("/upload", response_model=MedicalDocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    patient_id: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Strict Authorization Check:
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient profile not found.")
        target_patient_id = current_user.patient_profile.id
    elif current_user.role in [UserRole.DOCTOR, UserRole.ADMIN, UserRole.STAFF]:
        if not patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="patient_id is required for clinical upload.")
        target_patient_id = patient_id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized.")

    doc = validate_and_save_upload(
        db=db,
        patient_id=target_patient_id,
        file=file,
        current_user=current_user,
        tags=tags
    )
    return doc_to_out(doc)

@router.get("", response_model=List[MedicalDocumentOut])
def list_documents(
    patient_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(MedicalDocument)

    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_profile:
            return []
        query = query.filter(MedicalDocument.patient_id == current_user.patient_profile.id)
    else:
        if patient_id:
            query = query.filter(MedicalDocument.patient_id == patient_id)

    if search:
        pattern = f"%{search}%"
        query = query.filter((MedicalDocument.file_name.ilike(pattern)) | (MedicalDocument.tags.ilike(pattern)))

    docs = query.order_by(MedicalDocument.created_at.desc()).all()
    return [doc_to_out(d) for d in docs]

@router.get("/{document_id}", response_model=MedicalDocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    verify_document_access(doc, current_user, db)
    return doc_to_out(doc)

@router.post("/{document_id}/query")
def ask_document_question(
    document_id: int,
    question: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    verify_document_access(doc, current_user, db)
    answer = query_document(doc=doc, question=question)
    return {"document_id": doc.id, "question": question, "answer": answer}

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    verify_document_access(doc, current_user, db)

    # Strict containment check against upload directory to prevent LFI
    from pathlib import Path
    from app.core.config import settings

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    file_target = Path(doc.file_path).resolve()
    if not file_target.is_relative_to(upload_root):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid file storage location."
        )

    if not file_target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File on disk not found.")

    client_ip = request.client.host if request.client else None
    record_audit_log(
        db=db,
        action="DOCUMENT_DOWNLOAD",
        resource_type="MedicalDocument",
        resource_id=str(doc.id),
        user_id=current_user.id,
        details={"file_name": doc.file_name},
        ip_address=client_ip
    )

    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type=doc.file_type
    )
