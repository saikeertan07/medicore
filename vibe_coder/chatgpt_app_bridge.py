"""
ChatGPT Desktop App Bridge for macOS.
Interacts with /Applications/ChatGPT.app via macOS AppleScript & clipboard.
Reveals the latest upgraded codebase archive in Finder and copies the clinical prompt.
"""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("vibe_coder.app_bridge")

class ChatGPTAppBridge:
    def __init__(self, repo_root: Path, upgrades_dir: Path):
        self.repo_root = repo_root
        self.upgrades_dir = upgrades_dir

    def activate_app_and_share(self, latest_zip: Path, prompt_text: str):
        """
        Activates ChatGPT Classic in app/browser, copies prompt to clipboard, and reveals the file in Finder.
        """
        logger.info(f"📱 Opening ChatGPT Classic...")
        # 1. Open ChatGPT Classic direct URL / app
        subprocess.run(["open", "https://chatgpt.com/g/g-YyyyMT9nv-chatgpt-classic"])
        try:
            subprocess.run(["open", "-a", "/Applications/ChatGPT.app"])
        except Exception:
            pass

        # 2. Copy the prompt to clipboard
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(prompt_text.encode("utf-8"))
        logger.info("📋 Copied clinical upgrade prompt to macOS clipboard.")

        # 3. Reveal the latest zip file in Finder so the user can instantly drag it into ChatGPT Classic
        if latest_zip.exists():
            subprocess.run(["open", "-R", str(latest_zip)])
            logger.info(f"📂 Revealed '{latest_zip.name}' in Finder ready for ChatGPT Classic.")

if __name__ == "__main__":
    from vibe_coder.prompt_library import HOSPITAL_UPGRADE_ROADMAP, generate_iteration_prompt
    bridge = ChatGPTAppBridge(Path("."), Path("./upgrades"))
    prompt = generate_iteration_prompt(1, "Baseline MediCore AI", HOSPITAL_UPGRADE_ROADMAP[0])
    bridge.activate_app_and_share(Path("./upgrades/medicore_latest.zip"), prompt)
