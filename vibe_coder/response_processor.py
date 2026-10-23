"""
ChatGPT Response Processor & Code Ingestion Engine.
Takes raw response text (from clipboard, file, or chat),
extracts code blocks, validates syntax, updates repository files,
executes tests, and packages the next updated archive snapshot.
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any

from vibe_coder.code_updater import CodeUpdater

logger = logging.getLogger("vibe_coder.processor")

class ResponseProcessor:
    def __init__(self, repo_root: Path, upgrades_dir: Path):
        self.repo_root = repo_root
        self.upgrades_dir = upgrades_dir
        self.updater = CodeUpdater(repo_root, upgrades_dir)

    def get_clipboard_text(self) -> str:
        """Reads text directly from macOS clipboard using pbpaste."""
        try:
            res = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
            return res.stdout
        except Exception as e:
            logger.error(f"Failed to read clipboard: {e}")
            return ""

    def process_text(self, text: str, iteration: int = 1) -> Dict[str, Any]:
        """
        Parses code blocks from text, writes them to disk, runs tests,
        and generates a new zip archive.
        """
        if not text or len(text.strip()) < 10:
            return {"status": "EMPTY", "message": "No text or insufficient content provided."}

        logger.info(f"🔍 Parsing code blocks from input ({len(text)} characters)...")
        blocks = self.updater.extract_file_blocks(text)
        if not blocks:
            logger.warning("No code blocks with filepaths found in the input text.")
            return {
                "status": "NO_BLOCKS",
                "message": "No recognized file blocks found. Ensure format is ```filepath:path/to/file.py",
                "extracted_count": 0
            }

        logger.info(f"📦 Found {len(blocks)} code files in ChatGPT response. Applying updates...")
        applied_count, errors = self.updater.apply_updates(blocks)
        logger.info(f"✅ Applied {applied_count}/{len(blocks)} files to {self.repo_root}")

        # Run test verification
        passed, test_log = self.updater.run_tests()
        logger.info(f"🧪 Test Results: {'PASSED ✅' if passed else 'FAILED ❌'}")

        # Package updated snapshot
        new_archive = self.updater.create_upgrade_archive(iteration)

        return {
            "status": "SUCCESS" if (applied_count > 0 and passed) else "PARTIAL",
            "applied_count": applied_count,
            "total_blocks": len(blocks),
            "files": [b[0] for b in blocks],
            "errors": errors,
            "tests_passed": passed,
            "test_log": test_log[:500],
            "new_archive": str(new_archive)
        }

    def watch_clipboard_and_process(self, poll_interval_sec: int = 2):
        """
        Watches the macOS clipboard continuously. When the user copies a response
        from ChatGPT, the processor automatically detects it, applies the code,
        and builds the next release!
        """
        logger.info("👀 Watching macOS clipboard for ChatGPT responses...")
        logger.info("👉 Simply click 'Copy' on ChatGPT's response in ChatGPT Classic, and it will be processed automatically!")

        last_processed_hash = ""
        iteration = 1

        while True:
            text = self.get_clipboard_text()
            if text and ("```" in text or "def " in text or "class " in text or "import " in text):
                text_hash = str(hash(text))
                if text_hash != last_processed_hash and len(text.strip()) > 50:
                    last_processed_hash = text_hash
                    logger.info("\n🔔 New code detected on clipboard! Ingesting...")
                    result = self.process_text(text, iteration=iteration)
                    iteration += 1
                    logger.info(f"Result: {result['status']} | Files: {result.get('files', [])}")
                    logger.info("=" * 60)
            time.sleep(poll_interval_sec)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    repo = Path(".").resolve()
    processor = ResponseProcessor(repo, repo / "upgrades")

    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        processor.watch_clipboard_and_process()
    elif len(sys.argv) > 1 and sys.argv[1] == "--file":
        file_path = Path(sys.argv[2])
        res = processor.process_text(file_path.read_text(encoding="utf-8"))
        print(res)
    else:
        # Default: process whatever is currently on clipboard
        clip = processor.get_clipboard_text()
        res = processor.process_text(clip)
        print(res)
