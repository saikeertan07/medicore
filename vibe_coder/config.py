import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VibeBotConfig:
    # Target repository to analyze and continuously upgrade
    repo_root: Path = field(default_factory=lambda: Path(os.environ.get("MEDICORE_ROOT", "/Users/tedlasaikeertan/.gemini/antigravity/scratch/medicore")).resolve())
    
    # Run duration in hours (24 hours default)
    duration_hours: float = 24.0
    
    # Preferred models order for dynamic switching
    # Automatically falls back to the next model upon rate limit or quota exhaustion
    model_priority: List[str] = field(default_factory=lambda: [
        "claude-sonnet-4.6",       # Anthropic Claude 3.7 / 3.5 / next-gen Sonnet
        "gemini-3.8-flash",        # Google Gemini 3.8 Flash
        "gemini-3.8-medium",       # Google Gemini 3.8 Medium / Pro
        "chatgpt-4o",              # OpenAI ChatGPT
    ])
    
    # API Keys
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    
    # Browser Bridge Config (for ChatGPT Classic)
    chatgpt_web_url: str = "https://chatgpt.com/g/g-YyyyMT9nv-chatgpt-classic"
    browser_headless: bool = False
    browser_user_data_dir: Path = field(default_factory=lambda: Path.home() / ".vibe_bot_chrome_profile")
    
    # State & Output paths
    state_file: Path = field(default_factory=lambda: Path.cwd() / ".vibe_coder_state.json")
    upgrades_dir: Path = field(default_factory=lambda: Path.cwd() / "upgrades")
    
    # Rate limit retry configuration
    rate_limit_initial_delay_sec: int = 60
    rate_limit_max_delay_sec: int = 1800  # 30 minutes
    iteration_cooldown_sec: int = 15       # Brief pause between iterations
    
    def ensure_directories(self):
        self.upgrades_dir.mkdir(parents=True, exist_ok=True)
        self.browser_user_data_dir.mkdir(parents=True, exist_ok=True)
