"""
Unit tests for the 24/7 MediCore Vibe Coding Bot engine.
"""

import os
import tempfile
from pathlib import Path
import pytest

from vibe_coder.config import VibeBotConfig
from vibe_coder.prompt_library import (
    HOSPITAL_MISSION_SYSTEM_PROMPT,
    HOSPITAL_UPGRADE_ROADMAP,
    generate_iteration_prompt
)
from vibe_coder.code_updater import CodeUpdater
from vibe_coder.llm_router import LLMRouter, RateLimitException

def test_prompt_generation():
    milestone = HOSPITAL_UPGRADE_ROADMAP[0]
    prompt = generate_iteration_prompt(1, "Existing modules: auth, patients", milestone)
    assert "CONTINUOUS VIBE CODING LOOP - ITERATION #1" in prompt
    assert milestone["title"] in prompt
    assert "Emergency Triage" in prompt

def test_code_block_extraction():
    updater = CodeUpdater(Path("/tmp"), Path("/tmp/upgrades"))
    sample_response = """
Here is the upgrade for the triage system:

```filepath:backend/app/services/triage_service.py
# Triage implementation
def calculate_news2(vitals: dict) -> int:
    return 0
```

And here is the test:
```python:backend/tests/test_triage.py
def test_news2():
    assert True
```
"""
    extracted = updater.extract_file_blocks(sample_response)
    assert len(extracted) == 2
    paths = [p for p, _ in extracted]
    assert "backend/app/services/triage_service.py" in paths
    assert "backend/tests/test_triage.py" in paths

def test_rate_limit_tracking():
    config = VibeBotConfig(
        model_priority=["claude-sonnet-4.6", "gemini-3.8-flash", "chatgpt-4o"],
        anthropic_api_key="test-key-claude",
        gemini_api_key="test-key-gemini"
    )
    router = LLMRouter(config)
    assert router.current_model == "claude-sonnet-4.6"
    
    # Mark Claude rate limited
    router.record_rate_limit("claude-sonnet-4.6", backoff_seconds=120)
    
    # Next model should be Gemini
    next_model = router.get_available_model()
    assert next_model == "gemini-3.8-flash"

def test_upgrade_zip_packaging():
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_dir = Path(tmp_dir) / "repo"
        upgrades_dir = Path(tmp_dir) / "upgrades"
        repo_dir.mkdir()
        (repo_dir / "test.txt").write_text("hello hospital")

        updater = CodeUpdater(repo_dir, upgrades_dir)
        archive = updater.create_upgrade_archive(1)
        assert archive.exists()
        assert archive.name == "medicore_latest.zip"
        assert (upgrades_dir / "medicore_upgraded_iter_1.zip").exists()
