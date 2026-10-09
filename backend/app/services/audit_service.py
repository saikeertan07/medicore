import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import AuditLog

logger = logging.getLogger("medicore.audit")

def record_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    # Filter out sensitive information like passwords, auth tokens, secret keys
    sanitized_details = {}
    if details:
        for k, v in details.items():
            if any(sensitive in k.lower() for sensitive in ["password", "token", "secret", "key", "authorization"]):
                sanitized_details[k] = "[REDACTED]"
            else:
                sanitized_details[k] = v

    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=sanitized_details if sanitized_details else None,
            ip_address=ip_address
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record audit log: {e}")
        return None
