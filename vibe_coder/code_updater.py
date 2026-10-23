"""
MediCore AI & Vibe Coder — Code Updater, Staging & Test Execution Engine.
Features:
  - Robust path containment & traversal defense (security_validator).
  - Isolated staging workspace before touching working branch.
  - Atomic file writes (tempfile + os.replace) with automatic rollback checkpoint.
  - Multi-tier test suite execution (backend all/focused, frontend build, security).
  - Secure release packaging with pre-publication archive validation & manifest generation.
"""

import os
import ast
import re
import sys
import shutil
import zipfile
import logging
import tempfile
import subprocess
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

from vibe_coder.security_validator import (
    validate_and_resolve_path,
    validate_archive,
    is_path_prohibited_for_packaging,
    SecurityPathTraversalError,
    SecurityPackagingError,
    SecurityStagingError
)

logger = logging.getLogger("vibe_coder.updater")


@dataclass
class TestResult:
    __test__ = False
    passed: bool
    exit_code: int
    status_category: str  # "SUCCESS", "TEST_FAILURE", "TIMEOUT", "ENVIRONMENT_ERROR"
    command: str
    output: str
    duration_seconds: float
    total_tests: Optional[int] = None
    passed_tests: Optional[int] = None
    failed_tests: Optional[int] = None
    skipped_tests: Optional[int] = None


@dataclass
class StagedUpdateContext:
    staging_dir: Path
    files_to_apply: List[Tuple[str, str, Path]]  # (rel_path, content, staged_path)
    syntax_errors: List[str] = field(default_factory=list)
    security_violations: List[str] = field(default_factory=list)
    diff_summary: List[str] = field(default_factory=list)


class CodeUpdater:
    def __init__(self, repo_root: Path, upgrades_dir: Path):
        self.repo_root = repo_root.resolve()
        self.upgrades_dir = upgrades_dir.resolve()
        self.upgrades_dir.mkdir(parents=True, exist_ok=True)
        self._rollback_stack: List[Dict[Path, Optional[str]]] = []

    def extract_file_blocks(self, text: str) -> List[Tuple[str, str]]:
        """
        Parses AI markdown output to locate file paths and associated code blocks.
        Supports patterns:
          ```filepath:path/to/file.ext
          ```python:path/to/file.py
          ### File: path/to/file.ext
        """
        results = []
        if not text:
            return results

        # Pattern 1: ```(?:filepath|filename|file):([^\n]+)\n(.*?)\n```
        p1 = re.compile(r"```(?:filepath|filename|file):([^\n\r]+)[\r\n]+(.*?)[\r\n]+```", re.DOTALL)
        for match in p1.finditer(text):
            path_str = match.group(1).strip()
            code_str = match.group(2)
            results.append((path_str, code_str))

        # Pattern 2: ```[a-zA-Z0-9_-]+:([^\n]+)\n(.*?)\n```
        p2 = re.compile(r"```(?:python|ts|tsx|js|jsx|json|yaml|sql):([a-zA-Z0-9_./\\]+)[\r\n]+(.*?)[\r\n]+```", re.DOTALL)
        for match in p2.finditer(text):
            path_str = match.group(1).strip()
            code_str = match.group(2)
            if not any(r[0] == path_str for r in results):
                results.append((path_str, code_str))

        # Pattern 3: Header with File: path followed by ```code```
        p3 = re.compile(r"(?:###|##|\*\*|File:)\s*`?([a-zA-Z0-9_./\-]+\.(?:py|tsx|ts|js|jsx|json|sql))`?.*?\n```[a-zA-Z0-9_-]*[\r\n]+(.*?)[\r\n]+```", re.DOTALL)
        for match in p3.finditer(text):
            path_str = match.group(1).strip()
            code_str = match.group(2)
            if not any(r[0] == path_str for r in results):
                results.append((path_str, code_str))

        return results

    def stage_updates(self, files: List[Tuple[str, str]]) -> StagedUpdateContext:
        """
        Stages proposed AI code changes in an isolated temporary workspace.
        Validates path containment, checks Python syntax with ast.parse,
        verifies security invariants, and computes the pending diff.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="medicore_stage_"))
        context = StagedUpdateContext(staging_dir=temp_dir, files_to_apply=[])

        DANGEROUS_CALLS = [
            re.compile(r"\brm\s+-rf\s+[/~]", re.IGNORECASE),
            re.compile(r"\bcurl\b.*\|\s*(?:bash|sh)\b", re.IGNORECASE),
            re.compile(r"\bwget\b.*\|\s*(?:bash|sh)\b", re.IGNORECASE),
            re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
        ]

        for rel_path, code in files:
            # 1. Path containment validation
            try:
                target_path = validate_and_resolve_path(self.repo_root, rel_path)
            except SecurityPathTraversalError as e:
                context.security_violations.append(str(e))
                continue

            # 2. Syntax pre-compilation check for Python
            if target_path.suffix == ".py":
                try:
                    ast.parse(code, filename=rel_path)
                except SyntaxError as se:
                    context.syntax_errors.append(f"Syntax error in {rel_path}: {se.msg} (line {se.lineno})")
                    continue

            # 3. Static security scan on generated code
            for dang in DANGEROUS_CALLS:
                if dang.search(code):
                    context.security_violations.append(f"Dangerous command pattern detected in {rel_path}")
                    break

            # 4. Write to staging directory
            staged_file = temp_dir / rel_path
            staged_file.parent.mkdir(parents=True, exist_ok=True)
            staged_file.write_text(code, encoding="utf-8")
            context.files_to_apply.append((rel_path, code, staged_file))

            # Compute diff summary
            if target_path.exists():
                orig_len = len(target_path.read_text(encoding="utf-8", errors="ignore").splitlines())
                new_len = len(code.splitlines())
                context.diff_summary.append(f"MODIFIED: {rel_path} ({orig_len} -> {new_len} lines)")
            else:
                context.diff_summary.append(f"CREATED: {rel_path} ({len(code.splitlines())} lines)")

        return context

    def apply_updates(self, files: List[Tuple[str, str]], auto_stage: bool = True) -> Tuple[int, List[str]]:
        """
        Applies code updates with isolated staging, atomic file replacement, and rollback capability.
        Returns (applied_count, errors_list).
        """
        errors: List[str] = []
        if not files:
            return 0, ["No files provided to update."]

        # 1. Staging Step
        staged_ctx = self.stage_updates(files)
        if staged_ctx.security_violations:
            for viol in staged_ctx.security_violations:
                errors.append(f"Security Rejection: {viol}")
                logger.error(f"❌ Security violation: {viol}")
            shutil.rmtree(staged_ctx.staging_dir, ignore_errors=True)
            return 0, errors

        if staged_ctx.syntax_errors:
            for syn in staged_ctx.syntax_errors:
                errors.append(f"Syntax Rejection: {syn}")
                logger.error(f"❌ Syntax error: {syn}")
            shutil.rmtree(staged_ctx.staging_dir, ignore_errors=True)
            return 0, errors

        # 2. Record Rollback Checkpoint
        checkpoint: Dict[Path, Optional[str]] = {}
        for rel_path, _, _ in staged_ctx.files_to_apply:
            target = self.repo_root / rel_path
            if target.exists():
                try:
                    checkpoint[target] = target.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    checkpoint[target] = None
            else:
                checkpoint[target] = None  # Did not exist prior to update

        self._rollback_stack.append(checkpoint)

        # 3. Atomic Replacement onto Working Tree
        applied = 0
        try:
            for rel_path, code, _ in staged_ctx.files_to_apply:
                target_path = validate_and_resolve_path(self.repo_root, rel_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Write to temp file in same directory for atomic os.replace
                temp_target = None
                try:
                    with tempfile.NamedTemporaryFile("w", dir=str(target_path.parent), delete=False, encoding="utf-8") as tf:
                        tf.write(code)
                        temp_target = Path(tf.name)
                    temp_target.replace(target_path)
                    logger.info(f"✅ Atomically applied: {rel_path}")
                    applied += 1
                except Exception as ex:
                    if temp_target and temp_target.exists():
                        temp_target.unlink(missing_ok=True)
                    raise ex

        except Exception as e:
            logger.error(f"Failed applying updates: {e}. Executing atomic rollback...")
            self.rollback_last_update()
            errors.append(f"Update failed and rolled back: {e}")
            return 0, errors
        finally:
            shutil.rmtree(staged_ctx.staging_dir, ignore_errors=True)

        return applied, errors

    def rollback_last_update(self) -> bool:
        """Restores the repository files to the state prior to the most recent applied update."""
        if not self._rollback_stack:
            logger.warning("No rollback checkpoints available.")
            return False

        checkpoint = self._rollback_stack.pop()
        logger.info(f"🔄 Rolling back {len(checkpoint)} file modifications...")
        for target_path, orig_content in checkpoint.items():
            try:
                if orig_content is None:
                    if target_path.exists():
                        target_path.unlink()
                        logger.info(f"  Removed created file: {target_path}")
                else:
                    target_path.write_text(orig_content, encoding="utf-8")
                    logger.info(f"  Restored original content: {target_path}")
            except Exception as e:
                logger.error(f"Rollback error on {target_path}: {e}")
        return True

    def run_tests(
        self,
        suite: str = "all",
        test_file: Optional[str] = None,
        timeout: int = 120,
        custom_cmd: Optional[str] = None
    ) -> Tuple[bool, str, TestResult]:
        """
        Executes honest, multi-tier testing.
        Supported suites:
          - 'all': Runs complete discovered backend test suite.
          - 'focused': Runs targeted test file matching the current change.
          - 'frontend': Runs Next.js production build / lint.
          - 'security': Runs auth, rbac, and security tests.
          - 'custom': Runs user-supplied custom command string.
        Returns (passed, formatted_output, test_result_obj).
        """
        start_time = time.time()
        env = os.environ.copy()
        env["ENVIRONMENT"] = "testing"
        env["PYTHONPATH"] = f"{self.repo_root}:{self.repo_root / 'backend'}"

        venv_python = self.repo_root / "backend" / "venv" / "bin" / "python"
        if not venv_python.exists():
            venv_python = Path(sys.executable)

        cmd: List[str] = []
        cwd = str(self.repo_root)

        if custom_cmd:
            import shlex
            cmd = shlex.split(custom_cmd)
            cwd = str(self.repo_root)
        elif suite == "frontend":
            frontend_dir = self.repo_root / "frontend"
            cwd = str(frontend_dir)
            cmd = ["npm", "run", "build"]
        elif suite == "focused" and test_file:
            cmd = [str(venv_python), "-m", "pytest", test_file, "-q"]
            cwd = str(self.repo_root / "backend")
            env["PYTHONPATH"] = f".:{self.repo_root}"
        elif suite == "security":
            cmd = [
                str(venv_python), "-m", "pytest",
                "tests/test_auth.py",
                "tests/test_rbac.py",
                "tests/test_ai_features_and_security.py",
                "tests/test_phase2_fixes.py",
                "-q"
            ]
            cwd = str(self.repo_root / "backend")
            env["PYTHONPATH"] = f".:{self.repo_root}"
        else:
            # Default 'all': Discover all test modules in backend/tests
            cmd = [str(venv_python), "-m", "pytest", "tests/", "-q"]
            cwd = str(self.repo_root / "backend")
            env["PYTHONPATH"] = f".:{self.repo_root}"

        cmd_str = " ".join(cmd)
        logger.info(f"🧪 Running test suite [{suite}]: {cmd_str}")

        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = time.time() - start_time
            passed = (res.returncode == 0)
            status_cat = "SUCCESS" if passed else "TEST_FAILURE"
            output = res.stdout if passed else (res.stdout + "\n" + res.stderr)

            # Parse test counts from pytest output
            passed_count = None
            failed_count = None
            skipped_count = None
            total_count = None

            for line in output.splitlines():
                if "passed" in line or "failed" in line:
                    p_match = re.search(r"(\d+)\s+passed", line)
                    f_match = re.search(r"(\d+)\s+failed", line)
                    s_match = re.search(r"(\d+)\s+skipped", line)
                    if p_match:
                        passed_count = int(p_match.group(1))
                    if f_match:
                        failed_count = int(f_match.group(1))
                    if s_match:
                        skipped_count = int(s_match.group(1))

            test_result = TestResult(
                passed=passed,
                exit_code=res.returncode,
                status_category=status_cat,
                command=cmd_str,
                output=output,
                duration_seconds=duration,
                passed_tests=passed_count,
                failed_tests=failed_count,
                skipped_tests=skipped_count
            )
            return passed, output, test_result

        except subprocess.TimeoutExpired as te:
            duration = time.time() - start_time
            out = f"Test execution timed out after {timeout} seconds: {te}"
            logger.error(out)
            return False, out, TestResult(
                passed=False,
                exit_code=-1,
                status_category="TIMEOUT",
                command=cmd_str,
                output=out,
                duration_seconds=duration
            )
        except FileNotFoundError as fnf:
            duration = time.time() - start_time
            out = f"Test runner executable not found ({fnf}). Command: {cmd_str}"
            logger.error(out)
            return False, out, TestResult(
                passed=False,
                exit_code=127,
                status_category="ENVIRONMENT_ERROR",
                command=cmd_str,
                output=out,
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            out = f"Unexpected test execution error: {e}"
            logger.error(out)
            return False, out, TestResult(
                passed=False,
                exit_code=-1,
                status_category="ENVIRONMENT_ERROR",
                command=cmd_str,
                output=out,
                duration_seconds=duration
            )

    def create_upgrade_archive(self, iteration: int, validate_required_files: Optional[bool] = None) -> Path:
        """
        Packages repository into a clean distribution zip archive with strict security filtering.
        Validates archive using ArchiveValidator before publication.
        Fails fast if any prohibited file or credential is found.
        Generates manifest.json alongside archive.
        """
        archive_name = f"medicore_upgraded_iter_{iteration}.zip"
        archive_path = self.upgrades_dir / archive_name
        latest_symlink = self.upgrades_dir / "medicore_latest.zip"
        manifest_path = self.upgrades_dir / f"{archive_name}.manifest.json"

        logger.info(f"📦 Packaging repository snapshot into {archive_path.name} with strict security policy...")

        # Temporary archive path to avoid publishing unvalidated files
        temp_archive_path = self.upgrades_dir / f".tmp_{archive_name}"
        if temp_archive_path.exists():
            temp_archive_path.unlink()

        try:
            with zipfile.ZipFile(temp_archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.repo_root):
                    # Filter prohibited directories in-place during walk
                    dirs[:] = [
                        d for d in dirs 
                        if not is_path_prohibited_for_packaging(str((Path(root) / d).relative_to(self.repo_root)))[0]
                    ]

                    for file in files:
                        file_path = Path(root) / file
                        try:
                            rel_path = file_path.relative_to(self.repo_root)
                        except ValueError:
                            continue

                        rel_str = str(rel_path)
                        prohibited, reason = is_path_prohibited_for_packaging(rel_str)
                        if prohibited:
                            continue

                        if file_path == archive_path or file_path == latest_symlink or file_path == temp_archive_path:
                            continue

                        zipf.write(file_path, arcname=rel_str)

            # 2. Strict Pre-Publication Validation
            require_structure = validate_required_files if validate_required_files is not None else ((self.repo_root / "backend" / "app").exists())
            is_valid, validation_errors, manifest = validate_archive(temp_archive_path, require_project_structure=require_structure)
            if not is_valid:
                temp_archive_path.unlink(missing_ok=True)
                err_msg = f"Archive security validation failed! Errors:\n" + "\n".join(f" - {e}" for e in validation_errors)
                logger.error(err_msg)
                raise SecurityPackagingError(err_msg)

            # 3. Publish validated archive
            if archive_path.exists():
                archive_path.unlink()
            temp_archive_path.replace(archive_path)

            # Write cryptographic manifest
            import json
            with open(manifest_path, "w", encoding="utf-8") as mf:
                json.dump(manifest, mf, indent=2)

            # Copy to latest
            shutil.copyfile(archive_path, latest_symlink)
            latest_manifest = self.upgrades_dir / "medicore_latest.manifest.json"
            shutil.copyfile(manifest_path, latest_manifest)
            logger.info(
                f"🎉 Validated and published archive: {latest_symlink.name} "
                f"({archive_path.stat().st_size / 1024:.1f} KB, {manifest['file_count']} files verified)"
            )
            return latest_symlink

        except Exception as e:
            if temp_archive_path.exists():
                temp_archive_path.unlink(missing_ok=True)
            raise e
