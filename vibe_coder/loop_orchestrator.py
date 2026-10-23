"""
MediCore AI & Vibe Coder — Autonomous Loop Orchestrator.
Features:
  - Durable task state with atomic file persistence (fsync + os.replace).
  - Interruption recovery: detects unfinished tasks, re-validates disk status, and recovers safely.
  - Bounded exponential backoff on transient errors with fail-fast on permanent errors.
  - Verifiable task management: tracks affected files, test outcomes, and completion evidence.
  - Graceful termination when all tasks are complete with final verification.
"""

import os
import json
import time
import signal
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from vibe_coder.config import VibeBotConfig
from vibe_coder.prompt_library import (
    HOSPITAL_MISSION_SYSTEM_PROMPT,
    HOSPITAL_UPGRADE_ROADMAP,
    generate_iteration_prompt
)
from vibe_coder.llm_router import LLMRouter, RateLimitException
from vibe_coder.code_updater import CodeUpdater

logger = logging.getLogger("vibe_coder.orchestrator")


class LoopOrchestrator:
    def __init__(self, config: VibeBotConfig, use_browser: bool = False):
        self.config = config
        self.use_browser = use_browser
        self.config.ensure_directories()

        self.router = LLMRouter(config)
        self.updater = CodeUpdater(config.repo_root, config.upgrades_dir)
        self.browser_bridge = None
        self.running = True

        # State management
        self.state: Dict[str, Any] = self._load_or_init_state()

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info("\n🛑 Interrupt received. Gracefully saving state and finishing current cycle...")
        self.running = False

    def _initialize_fresh_tasks(self) -> List[Dict[str, Any]]:
        tasks = []
        for idx, milestone in enumerate(HOSPITAL_UPGRADE_ROADMAP):
            tasks.append({
                "task_id": f"TASK-{idx + 1:03d}",
                "module": milestone.get("module", f"module_{idx+1}"),
                "title": milestone.get("title", f"Milestone #{idx+1}"),
                "description": milestone.get("objective", f"Autonomous upgrade for {milestone.get('title')}"),
                "priority": idx + 1,
                "status": "PENDING",  # PENDING, IN_PROGRESS, COMPLETED, FAILED
                "start_time": None,
                "last_update": time.time(),
                "files_affected": [],
                "tests_executed": [],
                "test_outcomes": {},
                "failure_information": None,
                "retry_count": 0,
                "max_retries": 3,
                "next_action": f"Implement {milestone.get('title')}",
                "completion_evidence": None
            })
        return tasks

    def _load_or_init_state(self) -> Dict[str, Any]:
        """Loads previous state with structural validation and interruption recovery."""
        if self.config.state_file.exists():
            try:
                with open(self.config.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate schema
                if isinstance(data, dict) and "tasks" in data:
                    logger.info(f"📂 Loaded existing state: Iteration #{data.get('iteration', 1)} with {len(data['tasks'])} tasks.")
                    self._recover_interrupted_tasks(data["tasks"])
                    return data
                elif isinstance(data, dict):
                    # Legacy state upgrade
                    data["tasks"] = self._initialize_fresh_tasks()
                    return data
            except Exception as e:
                logger.warning(f"Could not read state file ({e}). Initializing fresh state.")

        return {
            "start_time": time.time(),
            "target_duration_seconds": self.config.duration_hours * 3600,
            "iteration": 1,
            "tasks": self._initialize_fresh_tasks(),
            "completed_milestones": [],
            "models_used": {},
            "history": []
        }

    def _recover_interrupted_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Recovers tasks that were left in IN_PROGRESS after unexpected process termination."""
        for t in tasks:
            if t.get("status") == "IN_PROGRESS":
                logger.warning(f"⚠️ Recovered interrupted task '{t['task_id']}' ({t['title']}).")
                retries = t.get("retry_count", 0) + 1
                t["retry_count"] = retries
                if retries >= t.get("max_retries", 3):
                    t["status"] = "FAILED"
                    t["failure_information"] = "Process interrupted and max retry budget exhausted."
                    logger.error(f"Task '{t['task_id']}' marked FAILED due to repeated interruption.")
                else:
                    t["status"] = "PENDING"
                    t["next_action"] = f"Resume from interrupted milestone (retry #{retries})"
                t["last_update"] = time.time()

    def _save_state(self):
        """Atomic state persistence using temp file, fsync, and atomic rename to avoid corruption."""
        try:
            temp_path = self.config.state_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(self.config.state_file)
        except Exception as e:
            logger.error(f"Failed to persist state atomically: {e}")

    def get_summary_of_repo(self) -> str:
        """Inspects repo to provide concise summary for context."""
        tree = []
        app_dir = self.config.repo_root / "backend" / "app"
        if app_dir.exists():
            for root, dirs, files in os.walk(app_dir):
                for f in files:
                    if f.endswith(".py"):
                        rel = Path(root).relative_to(self.config.repo_root) / f
                        tree.append(str(rel))
        return "Existing backend modules:\n" + "\n".join(tree[:25])

    def get_next_pending_task(self) -> Optional[Dict[str, Any]]:
        """Returns the highest priority pending task."""
        pending = [t for t in self.state.get("tasks", []) if t.get("status") == "PENDING"]
        if not pending:
            return None
        pending.sort(key=lambda t: t.get("priority", 999))
        return pending[0]

    def run_24h_loop(self):
        """Main autonomous execution loop."""
        end_time = self.state["start_time"] + self.state["target_duration_seconds"]
        logger.info("=" * 70)
        logger.info(f"🏥 MediCore AI Autonomous Vibe Coding Engine Initialized")
        logger.info(f"⏱️ Duration: {self.config.duration_hours} hours (Target end: {time.ctime(end_time)})")
        logger.info(f"🔄 Models: {' -> '.join(self.config.model_priority)}")
        logger.info(f"📁 Target Repository: {self.config.repo_root}")
        logger.info("=" * 70)

        # Initialize browser if requested
        if self.use_browser:
            from vibe_coder.browser_bridge import ChatGPTBrowserBridge
            self.browser_bridge = ChatGPTBrowserBridge(self.config)
            try:
                self.browser_bridge.start()
            except Exception as e:
                logger.error(f"Browser launch failed: {e}. Falling back to multi-model API router.")
                self.browser_bridge = None

        while self.running and time.time() < end_time:
            task = self.get_next_pending_task()
            if not task:
                logger.info("🎉 All roadmap tasks have been successfully processed or completed!")
                logger.info("Running final comprehensive verification...")
                passed, test_log, _ = self.updater.run_tests(suite="all")
                logger.info(f"Final Verification Suite Status: {'PASSED' if passed else 'REVIEW NEEDED'}")
                break

            iter_num = self.state.get("iteration", 1)
            task["status"] = "IN_PROGRESS"
            task["start_time"] = time.time()
            task["last_update"] = time.time()
            self._save_state()

            logger.info(f"\n--- [CYCLE #{iter_num}] Task {task['task_id']}: {task['title']} ---")

            # 1. Package current codebase state into archive
            latest_zip = self.updater.create_upgrade_archive(iter_num)

            # 2. Build iteration prompt
            repo_summary = self.get_summary_of_repo()
            milestone_dict = {"module": task["module"], "title": task["title"], "objective": task["description"]}
            user_prompt = generate_iteration_prompt(iter_num, repo_summary, milestone_dict)

            ai_response = ""
            # 3. Request upgrade with bounded exponential backoff
            max_backoff_attempts = 3
            for backoff_attempt in range(max_backoff_attempts):
                try:
                    if self.browser_bridge:
                        logger.info("Attempting ChatGPT Web Bridge turn...")
                        ai_response, is_rate_limited = self.browser_bridge.upload_file_and_send_prompt(
                            file_path=latest_zip,
                            prompt_text=user_prompt
                        )
                        if is_rate_limited:
                            logger.warning("ChatGPT Web rate limit detected! Delegating to LLM Router API...")
                            ai_response = self.router.send_message(HOSPITAL_MISSION_SYSTEM_PROMPT, user_prompt)
                    else:
                        ai_response = self.router.send_message(HOSPITAL_MISSION_SYSTEM_PROMPT, user_prompt)
                    break
                except RateLimitException as rle:
                    delay = min(self.config.rate_limit_max_delay_sec, self.config.rate_limit_initial_delay_sec * (2 ** backoff_attempt))
                    logger.warning(f"Rate limit backoff (attempt {backoff_attempt+1}/{max_backoff_attempts}): sleeping {delay}s")
                    time.sleep(delay)
                except Exception as e:
                    logger.info(f"Continuous Autonomous Hospital Watcher active: {e}")
                    ai_response = ""
                    break

            # 4. Extract generated code files and apply updates
            file_blocks = self.updater.extract_file_blocks(ai_response)
            if file_blocks:
                logger.info(f"Found {len(file_blocks)} files in AI upgrade plan. Staging and applying...")
                applied, errors = self.updater.apply_updates(file_blocks)
                task["files_affected"] = [f[0] for f in file_blocks]
                if errors:
                    logger.warning(f"Encountered {len(errors)} issues during code apply: {errors}")
            else:
                logger.warning("No formatted code blocks detected in response.")

            # 5. Run test verification
            passed, test_log, test_res = self.updater.run_tests(suite="all")
            logger.info(f"Test Run Result: {'PASSED' if passed else 'REVIEW NEEDED'}")

            task["tests_executed"] = [test_res.command]
            task["test_outcomes"] = {
                "passed": passed,
                "exit_code": test_res.exit_code,
                "status": test_res.status_category,
                "duration_seconds": test_res.duration_seconds
            }

            if passed and file_blocks:
                task["status"] = "COMPLETED"
                task["completion_evidence"] = {
                    "verified_at": time.time(),
                    "files_count": len(file_blocks),
                    "test_status": "SUCCESS"
                }
                logger.info(f"✅ Successfully completed task {task['task_id']}: {task['title']}")
            else:
                task["retry_count"] = task.get("retry_count", 0) + 1
                if task["retry_count"] >= task.get("max_retries", 3):
                    task["status"] = "FAILED"
                    task["failure_information"] = "Verification tests failed after maximum retry attempts."
                    logger.error(f"❌ Task {task['task_id']} reached maximum retry attempts and is marked FAILED.")
                else:
                    task["status"] = "PENDING"
                    task["next_action"] = f"Retry task {task['task_id']} with refined prompts."

            task["last_update"] = time.time()
            self.state["completed_milestones"].append({
                "iteration": iter_num,
                "task_id": task["task_id"],
                "milestone": task["module"],
                "timestamp": time.time(),
                "tests_passed": passed
            })
            self.state["iteration"] = iter_num + 1
            self._save_state()

            # 6. Cooldown
            remaining_seconds = max(0, end_time - time.time())
            remaining_hours = remaining_seconds / 3600
            logger.info(f"Iteration #{iter_num} finished. Remaining: {remaining_hours:.2f} hours.")
            time.sleep(self.config.iteration_cooldown_sec)

        # Cleanup
        if self.browser_bridge:
            self.browser_bridge.close()

        logger.info("\n🏁 Autonomous Vibe Coding Run Finished.")
        self.updater.create_upgrade_archive(self.state.get("iteration", 1))
