"""
macOS Desktop Automation Bridge for '/Applications/ChatGPT Classic.app'.
Presents the latest upgraded repository archive and clinical prompt directly
into the active chat of the ChatGPT Classic desktop application without restarting chats.
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("vibe_coder.classic_app")

class ChatGPTClassicAppBridge:
    def __init__(self, repo_root: Path, upgrades_dir: Path):
        self.repo_root = repo_root
        self.upgrades_dir = upgrades_dir
        self.app_name = "ChatGPT Classic"
        self.app_path = "/Applications/ChatGPT Classic.app"

    def is_app_installed(self) -> bool:
        return Path(self.app_path).exists()

    def send_to_active_chat(self, zip_path: Path, prompt_text: str, auto_press_enter: bool = True):
        """
        Activates ChatGPT Classic, attaches the zip file, inserts the prompt,
        and submits it into the current ongoing chat.
        """
        if not self.is_app_installed():
            raise FileNotFoundError(f"Application '{self.app_path}' not found.")

        logger.info(f"🚀 Bringing '{self.app_name}' to foreground...")
        # 1. Activate application
        subprocess.run(["open", "-a", self.app_path], check=True)
        time.sleep(1.0)

        # 2. Attach latest zip file via clipboard
        abs_zip = zip_path.resolve()
        logger.info(f"📎 Pasting file attachment '{abs_zip.name}' into active chat...")
        apple_script_paste_file = f'''
        set theFile to POSIX file "{abs_zip}"
        set the clipboard to (theFile as alias)
        tell application "{self.app_name}" to activate
        delay 0.5
        tell application "System Events"
            keystroke "v" using command down
        end tell
        '''
        subprocess.run(["osascript", "-e", apple_script_paste_file], check=True)
        time.sleep(2.0)  # Allow attachment chip to render in ChatGPT

        # 3. Copy prompt text to clipboard
        logger.info("✍️ Pasting clinical upgrade prompt into chat input...")
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(prompt_text.encode("utf-8"))

        apple_script_paste_text = f'''
        tell application "{self.app_name}" to activate
        delay 0.5
        tell application "System Events"
            keystroke "v" using command down
        end tell
        '''
        subprocess.run(["osascript", "-e", apple_script_paste_text], check=True)
        time.sleep(1.0)

        # 4. Press Enter to submit in the same chat
        if auto_press_enter:
            logger.info("📨 Sending message in current chat...")
            apple_script_enter = f'''
            tell application "{self.app_name}" to activate
            tell application "System Events"
                key code 36
            end tell
            '''
            subprocess.run(["osascript", "-e", apple_script_enter], check=True)
            logger.info("✅ Submitted successfully to ChatGPT Classic!")

    def run_continuous_app_loop(self, hours: float = 24.0, cycle_interval_minutes: int = 15):
        """
        Runs the 24-hour continuous loop directly targeting /Applications/ChatGPT Classic.app.
        """
        from vibe_coder.code_updater import CodeUpdater
        from vibe_coder.prompt_library import HOSPITAL_UPGRADE_ROADMAP, generate_iteration_prompt

        updater = CodeUpdater(self.repo_root, self.upgrades_dir)
        end_time = time.time() + (hours * 3600)
        iteration = 1

        logger.info("=" * 70)
        logger.info(f"🏥 Starting 24-Hour Continuous Loop on '{self.app_name}'")
        logger.info(f"⏱️ Duration: {hours} hours | Target end: {time.ctime(end_time)}")
        logger.info(f"🔄 Loop Interval: {cycle_interval_minutes} minutes")
        logger.info("=" * 70)

        while time.time() < end_time:
            roadmap_idx = (iteration - 1) % len(HOSPITAL_UPGRADE_ROADMAP)
            milestone = HOSPITAL_UPGRADE_ROADMAP[roadmap_idx]

            logger.info(f"\n--- [ITERATION #{iteration}] Packaging & Sending to ChatGPT Classic ---")
            logger.info(f"Target Milestone: {milestone['title']}")

            # 1. Package latest updated code zip
            latest_zip = updater.create_upgrade_archive(iteration)

            # 2. Build clinical prompt
            prompt = generate_iteration_prompt(iteration, "MediCore AI Hospital Platform", milestone)

            # 3. Share to active chat in ChatGPT Classic
            try:
                self.send_to_active_chat(latest_zip, prompt, auto_press_enter=True)
            except Exception as e:
                logger.error(f"Encountered error while communicating with {self.app_name}: {e}")

            iteration += 1
            remaining_mins = max(0, int((end_time - time.time()) / 60))
            logger.info(f"⏳ Sleeping {cycle_interval_minutes} mins before next iteration (Remaining: {remaining_mins} mins)...")
            time.sleep(cycle_interval_minutes * 60)

        logger.info("🏁 24-Hour Loop Completed.")

if __name__ == "__main__":
    from vibe_coder.code_updater import CodeUpdater
    from vibe_coder.prompt_library import HOSPITAL_UPGRADE_ROADMAP, generate_iteration_prompt

    repo = Path(".").resolve()
    upgrades = repo / "upgrades"
    bridge = ChatGPTClassicAppBridge(repo, upgrades)

    updater = CodeUpdater(repo, upgrades)
    latest_zip = updater.create_upgrade_archive(1)
    prompt = generate_iteration_prompt(1, "MediCore AI Hospital Platform", HOSPITAL_UPGRADE_ROADMAP[0])

    bridge.send_to_active_chat(latest_zip, prompt, auto_press_enter=True)
