"""
MediCore AI & Vibe Coder Security Validator.
Enforces packaging security boundaries, path containment, atomic change staging,
secret detection, and pre-publication archive verification.
"""

import os
import re
import math
import hashlib
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set

logger = logging.getLogger("vibe_coder.security")

# Custom Exception Hierarchy
class VibeCoderSecurityError(Exception):
    """Base exception for all Vibe Coder security violations."""
    pass

class SecurityPathTraversalError(VibeCoderSecurityError):
    """Raised when an operation attempts directory traversal or escaping repo containment."""
    pass

class SecurityPackagingError(VibeCoderSecurityError):
    """Raised when packaging includes prohibited sensitive files or secrets."""
    pass

class SecurityStagingError(VibeCoderSecurityError):
    """Raised when staged changes fail syntax, safety, or verification checks."""
    pass


# -------------------------------------------------------------------------
# Secret Scanning Engine
# -------------------------------------------------------------------------
SECRET_PATTERNS = [
    ("PRIVATE_KEY", re.compile(r"-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----", re.IGNORECASE)),
    ("CERTIFICATE", re.compile(r"-----BEGIN\s+CERTIFICATE-----", re.IGNORECASE)),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    ("JWT_TOKEN", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("STRIPE_KEY", re.compile(r"\b[rs]k_live_[0-9a-zA-Z]{24,}\b")),
    ("GENERIC_SECRET_ASSIGNMENT", re.compile(r"""(?:api_key|secret_key|private_key|postgres_password|auth_token)\s*[:=]\s*["']([A-Za-z0-9_\-\.]{24,})["']""", re.IGNORECASE)),
]

def calculate_shannon_entropy(data: str) -> float:
    """Calculates the Shannon entropy of a string."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    frequencies = {}
    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1
    for count in frequencies.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

def scan_text_for_secrets(text: str, filename_context: str = "") -> List[str]:
    """
    Scans text for credential patterns.
    Returns list of human-readable violation descriptions.
    NEVER logs or returns actual secret token values.
    """
    violations = []
    for pattern_name, regex in SECRET_PATTERNS:
        match = regex.search(text)
        if match:
            # Exclude known benign examples and documentation place-holders
            matched_str = match.group(0).lower()
            if any(exempt in matched_str for exempt in ["placeholder", "example", "your_secret", "change_me", "test-key", "dev_insecure", "testing_only", "dummy"]):
                continue
            violations.append(f"Detected {pattern_name} in '{filename_context}'. Secret pattern matched; actual contents redacted.")
    return violations


# -------------------------------------------------------------------------
# Packaging Exclusion & Validation Policy
# -------------------------------------------------------------------------
PROHIBITED_DIR_NAMES: Set[str] = {
    ".git",
    ".github",
    ".pytest_cache",
    "node_modules",
    ".next",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    "upgrades",
    ".vibe_bot_chrome_profile",
    "logs",
    "uploads",
    ".cache",
    "coverage",
    ".nyc_output",
    "build",
    "dist",
}

PROHIBITED_EXTENSIONS: Set[str] = {
    ".pem",
    ".key",
    ".p8",
    ".pkcs12",
    ".pfx",
    ".crt",
    ".cer",
    ".keystore",
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-journal",
    ".db-wal",
    ".rdb",
    ".log",
    ".tmp",
    ".swp",
    ".bak",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
}

PROHIBITED_EXACT_FILENAMES: Set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    ".env.backup",
    ".vibe_coder_state.json",
    "credentials.json",
    "service_account.json",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    ".DS_Store",
    "Thumbs.db",
}

REQUIRED_ARCHIVE_FILES: Set[str] = {
    "README.md",
    "docker-compose.yml",
    "backend/Dockerfile",
    "backend/requirements.txt",
    "backend/app/main.py",
    "backend/tests/conftest.py",
    "frontend/package.json",
}

def is_path_prohibited_for_packaging(rel_path_str: str) -> Tuple[bool, Optional[str]]:
    """
    Checks if a relative path is prohibited from being packaged into release archives.
    Returns (is_prohibited, reason).
    """
    parts = Path(rel_path_str).parts
    # 1. Prohibited Directory Anywhere in Path
    for part in parts[:-1]:
        if part in PROHIBITED_DIR_NAMES or part.startswith(".env"):
            return True, f"Path contains prohibited directory '{part}'"

    file_name = parts[-1] if parts else ""
    # 2. Exact prohibited file match
    if file_name in PROHIBITED_EXACT_FILENAMES:
        return True, f"Prohibited sensitive file '{file_name}'"

    # Allow .env.example strictly
    if file_name.startswith(".env") and file_name != ".env.example":
        return True, f"Prohibited environment file '{file_name}'"

    # 3. Prohibited Extension match
    suffix = Path(file_name).suffix.lower()
    if suffix in PROHIBITED_EXTENSIONS:
        return True, f"Prohibited file extension '{suffix}' for file '{file_name}'"

    # 4. Prohibited Temporary/Editor artifacts
    if file_name.endswith("~") or (file_name.startswith("#") and file_name.endswith("#")):
        return True, f"Prohibited temporary/swap file '{file_name}'"

    return False, None


# -------------------------------------------------------------------------
# Archive Validator Engine
# -------------------------------------------------------------------------
def validate_archive(archive_path: Path, require_project_structure: bool = True) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Exhaustively scans a generated zip archive before publication or distribution.
    Verifies:
      1. Zero prohibited files or extensions.
      2. Zero secrets in included text files.
      3. All required source and test files present (if require_project_structure=True).
      4. Generates a cryptographic manifest (SHA-256).
    Returns (is_valid, error_list, manifest).
    """
    errors: List[str] = []
    manifest: Dict[str, Any] = {
        "archive_name": archive_path.name,
        "archive_size_bytes": archive_path.stat().st_size if archive_path.exists() else 0,
        "file_count": 0,
        "files": []
    }

    if not archive_path.exists():
        return False, [f"Archive does not exist: {archive_path}"], manifest

    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()
            manifest["file_count"] = len(namelist)
            found_paths = set(namelist)

            # Check for required files
            if require_project_structure:
                for required in REQUIRED_ARCHIVE_FILES:
                    if required not in found_paths:
                        errors.append(f"Required file missing from archive: '{required}'")

            # Check every file inside zip
            for entry_name in namelist:
                prohibited, reason = is_path_prohibited_for_packaging(entry_name)
                if prohibited:
                    errors.append(f"Prohibited entry in archive: '{entry_name}' ({reason})")

                # Secret scanning on readable files (size < 5MB)
                info = zf.getinfo(entry_name)
                if info.file_size < 5 * 1024 * 1024:
                    raw = zf.read(entry_name)
                    # Compute hash for manifest
                    entry_sha256 = hashlib.sha256(raw).hexdigest()
                    manifest["files"].append({
                        "path": entry_name,
                        "size_bytes": info.file_size,
                        "sha256": entry_sha256
                    })

                    # Try decoding as text for secret scanning (exempt security test fixture itself)
                    if not entry_name.endswith("test_vibe_coder_security.py"):
                        try:
                            text_content = raw.decode("utf-8")
                            secret_violations = scan_text_for_secrets(text_content, entry_name)
                            for sv in secret_violations:
                                errors.append(sv)
                        except UnicodeDecodeError:
                            # Binary file (png, ico, etc.)
                            pass

    except zipfile.BadZipFile as bzf:
        return False, [f"Corrupted zip archive: {bzf}"], manifest
    except Exception as e:
        return False, [f"Validation failed with exception: {e}"], manifest

    is_valid = (len(errors) == 0)
    return is_valid, errors, manifest


# -------------------------------------------------------------------------
# Path Containment & Security Validator
# -------------------------------------------------------------------------
def validate_and_resolve_path(repo_root: Path, rel_path: str) -> Path:
    """
    Robust path containment check.
    Prevents path traversal, absolute path injection, symlink escapes,
    null byte attacks, and sibling directory prefix collisions.
    """
    if not rel_path or not isinstance(rel_path, str):
        raise SecurityPathTraversalError("Target path must be a non-empty string.")

    # 1. Null byte check
    if "\0" in rel_path:
        raise SecurityPathTraversalError("Null byte injection detected in target path.")

    # 2. Reject absolute path representations
    clean_str = rel_path.strip()
    if os.path.isabs(clean_str) or clean_str.startswith("/") or clean_str.startswith("\\"):
        raise SecurityPathTraversalError(f"Absolute paths are prohibited: '{rel_path}'")

    # 3. Reject windows drive letters
    if re.match(r"^[a-zA-Z]:", clean_str):
        raise SecurityPathTraversalError(f"Drive letter paths are prohibited: '{rel_path}'")

    # 4. Canonicalize root and candidate target
    repo_root_resolved = repo_root.resolve()
    target_path = (repo_root_resolved / clean_str).resolve()

    # 5. Strict containment check via commonpath and is_relative_to
    try:
        common = Path(os.path.commonpath([str(repo_root_resolved), str(target_path)]))
        if common != repo_root_resolved:
            raise SecurityPathTraversalError(f"Path escapes repository root via traversal: '{rel_path}'")
    except ValueError as ve:
        raise SecurityPathTraversalError(f"Path comparison failure: {ve}")

    # 6. Check for sibling directory with similar prefix (e.g. /repo vs /repo_attacker)
    if not target_path.is_relative_to(repo_root_resolved):
        raise SecurityPathTraversalError(f"Target path '{target_path}' is not within repo root '{repo_root_resolved}'")

    # 7. Symlink Escape Verification
    # If the target exists and is a symlink, verify its real target is inside repo
    if target_path.is_symlink():
        real_target = target_path.resolve()
        if not real_target.is_relative_to(repo_root_resolved):
            raise SecurityPathTraversalError(f"Symlink escapes repository: '{rel_path}' -> '{real_target}'")

    # Verify no parent directory component in target_path is a symlink escaping root
    curr = target_path.parent
    while curr != repo_root_resolved and curr != curr.parent:
        if curr.is_symlink():
            real_parent = curr.resolve()
            if not real_parent.is_relative_to(repo_root_resolved):
                raise SecurityPathTraversalError(f"Parent directory symlink escapes repository: '{curr}' -> '{real_parent}'")
        curr = curr.parent

    # 8. Directories supplied where files are expected
    if target_path.exists() and target_path.is_dir():
        raise SecurityPathTraversalError(f"Target path '{rel_path}' is an existing directory, not a file.")

    # 9. Prevent writing directly into prohibited repository internal directories
    try:
        rel_from_root = target_path.relative_to(repo_root_resolved)
        parts = rel_from_root.parts
        if parts:
            if parts[0] in [".git", "node_modules", "venv", ".venv"]:
                raise SecurityPathTraversalError(f"Modification of protected internal directory '{parts[0]}' is prohibited.")
            if parts[-1] in [".env", ".vibe_coder_state.json"]:
                raise SecurityPathTraversalError(f"Autonomous modification of protected configuration '{parts[-1]}' is prohibited.")
    except ValueError:
        pass

    return target_path
