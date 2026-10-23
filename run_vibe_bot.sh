#!/usr/bin/env bash
# ==============================================================================
# MediCore AI - 24/7 Autonomous Vibe Coding Bot Launcher
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🏥 MediCore AI - 24/7 Autonomous Vibe Coding Engine"
echo "======================================================================"

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not found."
    exit 1
fi

# Ensure output directories exist
mkdir -p upgrades logs

case "$1" in
    classic-daemon)
        echo "🚀 Launching 24-Hour Continuous Vibe Coding Daemon on ChatGPT Classic..."
        nohup python3 -c "from pathlib import Path; from vibe_coder.chatgpt_classic_app_bridge import ChatGPTClassicAppBridge; ChatGPTClassicAppBridge(Path('.').resolve(), Path('./upgrades').resolve()).run_continuous_app_loop(hours=24, cycle_interval_minutes=15)" > logs/vibe_bot_classic.log 2>&1 &
        echo "✅ ChatGPT Classic Bot started in background (PID: $!)"
        echo "📋 Monitor logs with: tail -f logs/vibe_bot_classic.log"
        ;;
    classic|classic-loop)
        echo "🚀 Starting 24-Hour Continuous Vibe Coding Loop on /Applications/ChatGPT Classic.app..."
        python3 -c "from pathlib import Path; from vibe_coder.chatgpt_classic_app_bridge import ChatGPTClassicAppBridge; ChatGPTClassicAppBridge(Path('.').resolve(), Path('./upgrades').resolve()).run_continuous_app_loop(hours=24, cycle_interval_minutes=15)"
        ;;
    app)
        echo "📱 Connecting to macOS ChatGPT Desktop App..."
        python3 -m vibe_coder.chatgpt_app_bridge
        ;;
    status)
        python3 -m vibe_coder.cli --status
        ;;
    browser)
        echo "🌐 Starting Vibe Coder in ChatGPT Web Browser mode..."
        python3 -m vibe_coder.cli --hours 24 --browser
        ;;
    daemon)
        echo "🚀 Starting Vibe Coder in background daemon mode (24 hours)..."
        nohup python3 -m vibe_coder.cli --hours 24 > logs/vibe_bot_daemon.log 2>&1 &
        echo "✅ Bot started in background with PID: $!"
        echo "📋 Monitor logs with: tail -f logs/vibe_bot_daemon.log"
        echo "📊 Check status with: ./run_vibe_bot.sh status"
        ;;
    dry-run)
        echo "🧪 Executing single dry-run test iteration..."
        python3 -m vibe_coder.cli --dry-run
        ;;
    *)
        echo "🚀 Running Vibe Coder in foreground (24 hours loop)..."
        echo "   Priority: Claude Sonnet -> Gemini 3.8 Flash/Medium -> ChatGPT 4o"
        echo "   Automatic failover & rate limit pause/resume active."
        python3 -m vibe_coder.cli --hours 24
        ;;
esac
