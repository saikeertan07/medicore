"""
Feature 12 — AI Governance and Evaluation Dashboard Service
Monitors AI reliability, latency, token consumption, cost estimates, prompt injection blocks, and kill-switch control.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User, UserRole, AIGovernanceMetric, AuditLog
from app.ai.gateway import ai_gateway


class GovernanceService:
    def get_governance_telemetry(self, db: Session, admin_user: User) -> Dict[str, Any]:
        # Aggregate totals
        total_requests = db.query(AIGovernanceMetric).count()
        
        # Token metrics
        total_tokens = db.query(func.sum(AIGovernanceMetric.total_tokens)).scalar() or 0
        total_cost = float(db.query(func.sum(AIGovernanceMetric.estimated_cost_usd)).scalar() or 0.0)
        avg_latency = float(db.query(func.avg(AIGovernanceMetric.latency_ms)).scalar() or 0.0)

        # Security flags
        security_flagged_count = db.query(AIGovernanceMetric).filter(
            AIGovernanceMetric.flagged_security == True
        ).count()

        # By feature distribution
        feature_breakdown = db.query(
            AIGovernanceMetric.feature_name,
            func.count(AIGovernanceMetric.id).label("calls"),
            func.avg(AIGovernanceMetric.latency_ms).label("avg_lat")
        ).group_by(AIGovernanceMetric.feature_name).all()

        features_summary = [
            {"feature": name, "invocations": count, "avg_latency_ms": round(float(lat or 0), 1)}
            for name, count, lat in feature_breakdown
        ]

        # Recent security flagged logs
        recent_security_events = db.query(AIGovernanceMetric).filter(
            AIGovernanceMetric.flagged_security == True
        ).order_by(AIGovernanceMetric.created_at.desc()).limit(10).all()

        security_logs = [{
            "id": m.id,
            "feature": m.feature_name,
            "reason": m.security_reason,
            "timestamp": m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for m in recent_security_events]

        return {
            "kill_switch_active": ai_gateway.is_kill_switch_active(),
            "provider": ai_gateway.provider,
            "model": ai_gateway.model_name,
            "total_ai_requests": total_requests,
            "total_tokens_consumed": int(total_tokens),
            "estimated_cost_usd": round(total_cost, 4),
            "average_latency_ms": round(avg_latency, 2),
            "security_alerts_intercepted": security_flagged_count,
            "feature_breakdown": features_summary,
            "recent_security_events": security_logs,
            "compliance_status": "MONITORED_AND_AUDITED"
        }

    def toggle_kill_switch(self, db: Session, admin_user: User, enabled: bool, reason: str) -> Dict[str, Any]:
        ai_gateway.set_kill_switch(enabled=enabled, reason=reason, admin_user=admin_user, db=db)
        return {
            "kill_switch_active": ai_gateway.is_kill_switch_active(),
            "reason": reason,
            "toggled_by": admin_user.full_name,
            "message": f"AI Kill Switch has been {'ACTIVATED' if enabled else 'DEACTIVATED'} successfully."
        }


governance_service = GovernanceService()
