"""
FastAPI Router for Tamper-Evident Audit Vault & Break-Glass Protocol.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.audit_vault_service import AuditVault

router = APIRouter(prefix="/audit-vault", tags=["Tamper-Evident Cryptographic Audit Vault"])

# Global singleton in-memory vault ledger (persisted across sessions)
global_vault = AuditVault()

class BreakGlassRequest(BaseModel):
    user_id: int
    user_role: str
    patient_id: int
    emergency_justification: str = Field(..., min_length=10)

class RecordEventRequest(BaseModel):
    user_id: int
    user_role: str
    action: str
    resource: str
    resource_id: str
    details: Optional[Dict[str, Any]] = None

@router.post("/record")
def record_audit_event(req: RecordEventRequest) -> Dict[str, Any]:
    """Records an immutable audit event in the cryptographic hash-chained ledger."""
    entry = global_vault.record_event(
        user_id=req.user_id,
        user_role=req.user_role,
        action=req.action,
        resource=req.resource,
        resource_id=req.resource_id,
        details=req.details
    )
    return {
        "entry_id": entry.entry_id,
        "entry_hash": entry.entry_hash,
        "timestamp": entry.timestamp,
        "status": "COMMITTED"
    }

@router.post("/break-glass")
def trigger_break_glass_access(req: BreakGlassRequest) -> Dict[str, Any]:
    """Emergency break-glass access authorization and immediate compliance audit logging."""
    entry = global_vault.record_break_glass_access(
        user_id=req.user_id,
        user_role=req.user_role,
        patient_id=req.patient_id,
        emergency_justification=req.emergency_justification
    )
    return {
        "status": "BREAK_GLASS_GRANTED",
        "entry_id": entry.entry_id,
        "entry_hash": entry.entry_hash,
        "warning": "Emergency override recorded in permanent immutable ledger. Hospital compliance notified."
    }

@router.get("/verify-integrity")
def verify_audit_vault_integrity() -> Dict[str, Any]:
    """Cryptographically verifies the entire historical audit ledger."""
    return global_vault.verify_ledger_integrity()
