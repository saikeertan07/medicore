import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user
from app.models.models import User, UserRole

logger = logging.getLogger("medicore.health")

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])


@router.get("", summary="Minimal Liveness Check")
@router.get("/live", summary="Liveness Probe")
def liveness_check():
    """
    Minimal public liveness probe for load balancers and orchestrators.
    Never exposes internal system architecture, connection strings, or error traces.
    """
    return {"status": "ok", "service": "MediCore AI"}


@router.get("/ready", summary="Readiness Probe")
def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes/Docker readiness probe confirming critical service dependencies.
    Returns HTTP 200 when ready to accept clinical traffic, or HTTP 503 when dependencies fail.
    Safe error reporting: logs details privately to server logs, returns generic public message.
    """
    try:
        db.execute(text("SELECT 1"))

        # In production, enforce that all database migrations are APPLIED and verified
        if settings.ENVIRONMENT == "production":
            from app.core.migrations import is_schema_ready
            ready, reason = is_schema_ready(db.get_bind())
            if not ready:
                logger.error(f"Readiness probe failed - Incomplete schema migration: {reason}")
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "not_ready",
                        "error": "Database schema incomplete or unmigrated."
                    }
                )

        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Readiness probe failed - Database unreachable: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": "Required database dependency is currently unreachable."
            }
        )


@router.get("/diagnostics", summary="Authorized System Diagnostics")
def system_diagnostics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Restricted diagnostic endpoint for hospital system administrators only.
    Requires authenticated user with ADMIN role.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to System Administrators."
        )

    t0 = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
        db_ok = True
    except Exception:
        db_ok = False
        db_latency_ms = None

    return {
        "status": "operational" if db_ok else "degraded",
        "database": {
            "connected": db_ok,
            "engine": settings.DATABASE_ENGINE,
            "latency_ms": db_latency_ms
        },
        "environment": settings.ENVIRONMENT,
        "ai_provider": settings.AI_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "version": "1.0.0"
    }
