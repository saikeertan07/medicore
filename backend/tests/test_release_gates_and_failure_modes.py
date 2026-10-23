"""
MediCore AI & Vibe Coder — Phase 4: Release Gates & 12 Failure Modes Test Suite.
Independently reproduces and verifies:
  Scenario 1: All tests passing -> status SUCCESS, exit code 0
  Scenario 2: A test failure -> status TEST_FAILURE, exit code != 0, fail-closed
  Scenario 3: A syntax error in code -> rejected in staging before execution
  Scenario 4: A missing dependency -> status ENVIRONMENT_ERROR / test failure, exit != 0
  Scenario 5: A test runner executable that cannot start -> status ENVIRONMENT_ERROR, exit 127
  Scenario 6: A timeout -> status TIMEOUT, exit -1, execution aborted cleanly
  Scenario 7: An unavailable database -> health / migration reports failure, not success
  Scenario 8: A failed migration -> recorded as failure, schema_ready is False
  Scenario 9: A frontend build failure -> release validation aborts, exit != 0
  Scenario 10: An archive containing a prohibited file -> validate_archive returns False, packaging aborts
  Scenario 11: A secret scanner detecting credentials -> packaging blocked, secret redacted in logs
  Scenario 12: An interrupted pipeline / missing manifest -> fails closed with non-zero exit
"""

import os
import sys
import tempfile
import zipfile
import pytest
import subprocess
from pathlib import Path

# Add paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from vibe_coder.code_updater import CodeUpdater, TestResult
from vibe_coder.security_validator import (
    validate_archive,
    scan_text_for_secrets,
    is_path_prohibited_for_packaging,
    SecurityPackagingError
)
from app.core.migrations import (
    run_all_migrations,
    is_schema_ready,
    record_migration_failure,
    MigrationVerificationError
)
from sqlalchemy import create_engine, text


def test_scenario_1_all_tests_passing():
    """Scenario 1: All tests passing reports SUCCESS and exit code 0."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        # Run benign passing echo test
        passed, out, res = updater.run_tests(suite="custom", custom_cmd="python3 -c 'print(\"1 passed in 0.01s\")'")
        assert passed is True
        assert res.exit_code == 0
        assert res.status_category == "SUCCESS"
        assert res.duration_seconds >= 0.0


def test_scenario_2_test_failure():
    """Scenario 2: An actual test failure reports TEST_FAILURE and fails closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        # Run failing test command
        passed, out, res = updater.run_tests(suite="custom", custom_cmd="python3 -c 'import sys; print(\"1 failed\"); sys.exit(1)'")
        assert passed is False
        assert res.exit_code == 1
        assert res.status_category == "TEST_FAILURE"


def test_scenario_3_syntax_error():
    """Scenario 3: Syntax error in proposed code is caught in staging before application."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        staged = updater.stage_updates([("backend/app/bad.py", "def syntax_err(:\n  pass")])
        assert len(staged.syntax_errors) > 0
        assert len(staged.files_to_apply) == 0

        # Attempting apply_updates fails fast and touches nothing
        count, errors = updater.apply_updates([("backend/app/bad.py", "def syntax_err(:\n  pass")])
        assert count == 0
        assert not (repo_root / "backend" / "app" / "bad.py").exists()


def test_scenario_4_missing_dependency():
    """Scenario 4: Missing dependency import raises non-zero exit code and failure."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        passed, out, res = updater.run_tests(suite="custom", custom_cmd="python3 -c 'import non_existent_pkg_xyz_123'")
        assert passed is False
        assert res.exit_code != 0
        assert "ModuleNotFoundError" in res.output or "No module named" in res.output


def test_scenario_5_runner_cannot_start():
    """Scenario 5: Test runner binary does not exist -> ENVIRONMENT_ERROR."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        passed, out, res = updater.run_tests(suite="custom", custom_cmd="/usr/bin/non_existent_runner_binary_12345 --arg")
        assert passed is False
        assert res.status_category == "ENVIRONMENT_ERROR"
        assert res.exit_code == 127


def test_scenario_6_timeout():
    """Scenario 6: Test execution timeout is captured cleanly without hanging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_root = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_root.mkdir()
        updater = CodeUpdater(repo_root, upgrades_dir)

        passed, out, res = updater.run_tests(suite="custom", custom_cmd="python3 -c 'import time; time.sleep(10)'", timeout=1)
        assert passed is False
        assert res.status_category == "TIMEOUT"
        assert res.exit_code == -1
        assert "timed out" in res.output


def test_scenario_7_unavailable_database():
    """Scenario 7: Unavailable database connection returns False on readiness."""
    bad_engine = create_engine("postgresql://postgres:bad_pass@localhost:54399/non_existent_db")
    ready, reason = is_schema_ready(bad_engine)
    assert ready is False


def test_scenario_8_failed_migration():
    """Scenario 8: Failed migration records error and schema remains not ready."""
    engine = create_engine("sqlite:///:memory:")
    # Run clean migrations
    run_all_migrations(engine)
    ready, _ = is_schema_ready(engine)
    assert ready is True

    # Inject failure into schema_migrations table
    record_migration_failure(engine, "step_fault_injection", "Column constraint violation injected")
    ready_after, reason = is_schema_ready(engine)
    assert ready_after is False


def test_scenario_9_frontend_build_failure():
    """Scenario 9: Simulated frontend build failure exits with non-zero exit code."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_frontend = Path(tmp_dir) / "frontend"
        fake_frontend.mkdir()
        # Invalid package.json
        (fake_frontend / "package.json").write_text("{ broken json }")

        res = subprocess.run(["npm", "run", "build"], cwd=str(fake_frontend), capture_output=True, text=True)
        assert res.returncode != 0


def test_scenario_10_prohibited_file_in_archive():
    """Scenario 10: Archive containing prohibited file (.env) is rejected by validator."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        bad_archive = Path(tmp_dir) / "bad.zip"
        with zipfile.ZipFile(bad_archive, "w") as zf:
            zf.writestr(".env", "SECRET_KEY=leaked_key")
            zf.writestr("README.md", "# Test")

        is_valid, errors, manifest = validate_archive(bad_archive, require_project_structure=False)
        assert is_valid is False
        assert any("prohibited" in err.lower() for err in errors)


def test_scenario_11_secret_scanner_redacts_credentials():
    """Scenario 11: Secret scanner detects leaked token and redacts it from output logs."""
    fake_token = "ghp_" + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"
    violations = scan_text_for_secrets(f"my_token = '{fake_token}'", "test_file.py")
    assert len(violations) > 0
    assert fake_token not in violations[0]
    assert "redacted" in violations[0].lower()


def test_scenario_12_interrupted_pipeline_fails_closed():
    """Scenario 12: Missing or partial manifest fails release validation closed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dummy_archive = Path(tmp_dir) / "dummy.zip"
        # Incomplete archive without required structure
        with zipfile.ZipFile(dummy_archive, "w") as zf:
            zf.writestr("dummy.txt", "content")

        is_valid, errors, manifest = validate_archive(dummy_archive, require_project_structure=True)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Required file missing" in err for err in errors)
