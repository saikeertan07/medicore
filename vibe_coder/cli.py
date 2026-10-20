"""
Command-Line Interface for MediCore Autonomous Vibe Coding Engine.
"""

import sys
import argparse
import logging
import json
from pathlib import Path

from vibe_coder.config import VibeBotConfig
from vibe_coder.loop_orchestrator import LoopOrchestrator

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

def show_status(state_file: Path):
    if not state_file.exists():
        print("No active vibe coder state found.")
        return
    with open(state_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("\n--- MediCore Vibe Coder Status ---")
    print(f"Current Iteration: #{data.get('iteration', 1)}")
    print(f"Target Duration: {data.get('target_duration_seconds', 0) / 3600:.1f} hours")
    print(f"Completed Milestones ({len(data.get('completed_milestones', []))}):")
    for m in data.get("completed_milestones", []):
        status = "✅ PASS" if m.get("tests_passed") else "⚠️ REVIEW"
        print(f"  • Iter #{m.get('iteration')}: {m.get('milestone')} [{status}]")
    print("----------------------------------\n")

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="MediCore AI 24/7 Autonomous Vibe Coding Bot")
    parser.add_argument("--hours", type=float, default=24.0, help="Continuous loop duration in hours (default: 24.0)")
    parser.add_argument("--repo-dir", type=str, default=".", help="Path to MediCore repository root")
    parser.add_argument("--browser", action="store_true", help="Enable ChatGPT Web Browser Mode (Playwright)")
    parser.add_argument("--models", type=str, default="claude-sonnet-4.6,gemini-3.8-flash,gemini-3.8-medium,chatgpt-4o", help="Comma-separated model priority list")
    parser.add_argument("--status", action="store_true", help="Display current loop progress and exit")
    parser.add_argument("--dry-run", action="store_true", help="Run a single test iteration and exit")

    args = parser.parse_args()

    repo_path = Path(args.repo_dir).resolve()
    state_file = repo_path / ".vibe_coder_state.json"

    if args.status:
        show_status(state_file)
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    config = VibeBotConfig(
        repo_root=repo_path,
        duration_hours=0.01 if args.dry_run else args.hours,
        model_priority=models,
        state_file=state_file
    )

    orchestrator = LoopOrchestrator(config, use_browser=args.browser)
    orchestrator.run_24h_loop()

if __name__ == "__main__":
    main()
