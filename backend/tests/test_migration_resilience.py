"""
Comprehensive Database Migration Reliability & Readiness Tests.
Verifies Phase 7 requirements:
  - Idempotent and transaction-safe schema migrations.
  - Failure injection and explicit recording of FAILED status.
  - Schema completeness verification against engine tables.
  - /health/ready probe returns HTTP 503 on unmigrated or failed schemas in production.
"""

import pytest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient

from app.core.migrations import (
    run_all_migrations,
    check_migrations,
    is_schema_ready,
    ensure_schema_migrations_table,
    record_migration_failure,
    MIGRATION_STEPS
)
from app.core.config import settings
from app.main import app


def test_fresh_database_migrations_and_verification():
    """Test running all versioned migrations on a clean in-memory database."""
    engine = create_engine("sqlite:///:memory:")
    
    # 1. Run all migrations
    run_all_migrations(engine)
    
    # 2. Check migrations registry
    status_map = check_migrations(engine)
    for step_name, _ in MIGRATION_STEPS:
        assert step_name in status_map
        assert status_map[step_name]["status"] == "APPLIED"
        assert status_map[step_name]["error"] is None

    # 3. Check schema readiness
    ready, reason = is_schema_ready(engine)
    assert ready is True
    assert reason is None


def test_idempotent_migration_re_execution():
    """Test that migrations can be executed repeatedly on existing databases without error."""
    engine = create_engine("sqlite:///:memory:")
    run_all_migrations(engine)
    
    # Re-run a second time
    run_all_migrations(engine)
    
    status_map = check_migrations(engine)
    for step_name, _ in MIGRATION_STEPS:
        assert status_map[step_name]["status"] == "APPLIED"


def test_migration_failure_injection_and_unready_state():
    """
    Test failure injection into a migration step:
    Verifies that failed migration records 'FAILED' status and is_schema_ready returns False.
    """
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        ensure_schema_migrations_table(conn)
        from app.core.migrations import record_migration_success
        record_migration_success(conn, "step2_core_ops")
        record_migration_failure(conn, "step3_clinical_emr", "Simulated disk corruption or constraint error")

    status_map = check_migrations(engine)
    assert status_map["step3_clinical_emr"]["status"] == "FAILED"
    assert "Simulated disk corruption" in status_map["step3_clinical_emr"]["error"]

    ready, reason = is_schema_ready(engine)
    assert ready is False
    assert "FAILED" in reason


def test_health_ready_probe_in_production_fails_on_unmigrated_schema(monkeypatch):
    """
    Test that /api/v1/health/ready probe in production returns HTTP 503
    if required database migrations are not applied.
    """
    client = TestClient(app)
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    # Mock is_schema_ready to simulate an incomplete or unapplied schema
    from app.core import migrations
    monkeypatch.setattr(migrations, "is_schema_ready", lambda target_engine=None: (False, "Missing migration step5"))

    res = client.get("/api/v1/health/ready")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "not_ready"
    assert "Database schema incomplete" in data["error"]
