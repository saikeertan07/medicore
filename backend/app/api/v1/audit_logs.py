from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.models import AuditLog, User, UserRole
from app.schemas.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])

def audit_to_out(log: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        id=log.id,
        user_id=log.user_id,
        user_email=log.user.email if log.user else "System",
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=log.details,
        ip_address=log.ip_address,
        created_at=log.created_at
    )

@router.get("", response_model=List[AuditLogOut])
def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_roles([UserRole.ADMIN]))
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [audit_to_out(log) for log in logs]
