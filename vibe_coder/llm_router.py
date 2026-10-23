"""
Multi-Model LLM Router with Persistent Conversation Memory & Automatic Rate-Limit Failover.
Supports: Claude Sonnet, Gemini 3.8 Flash/Medium, ChatGPT (OpenAI).
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("vibe_coder.router")

class LLMRouter:
    def __init__(self, config):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self.current_model_index = 0
        self.rate_limited_models: Dict[str, float] = {}  # model -> retry_after_timestamp

    @property
    def current_model(self) -> str:
        return self.config.model_priority[self.current_model_index % len(self.config.model_priority)]

    def record_rate_limit(self, model: str, backoff_seconds: int = 60):
        """Marks a model as rate-limited until a future timestamp."""
        until = time.time() + backoff_seconds
        self.rate_limited_models[model] = until
        logger.warning(f"⚠️ Model '{model}' hit rate limit. Pausing model until {time.ctime(until)} (in {backoff_seconds}s)")

    def get_available_model(self) -> Optional[str]:
        """Finds the next model that is not currently rate-limited."""
        now = time.time()
        # Clean expired rate limits
        expired = [m for m, t in self.rate_limited_models.items() if now >= t]
        for m in expired:
            del self.rate_limited_models[m]
            logger.info(f"✅ Rate limit expired for '{m}'. Model is available again.")

        for i in range(len(self.config.model_priority)):
            idx = (self.current_model_index + i) % len(self.config.model_priority)
            candidate = self.config.model_priority[idx]
            if candidate in self.rate_limited_models:
                continue

            # Verify credentials exist for this candidate
            cand_lower = candidate.lower()
            if "gemini" in cand_lower and not (self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY")):
                continue
            if ("claude" in cand_lower or "sonnet" in cand_lower) and not (self.config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")):
                continue
            if ("chatgpt" in cand_lower or "openai" in cand_lower or "gpt" in cand_lower) and not (self.config.openai_api_key or os.environ.get("OPENAI_API_KEY")):
                continue

            self.current_model_index = idx
            return candidate
        return None

    def wait_for_any_model_availability(self) -> Tuple[str, float]:
        """If all models are rate-limited, sleeps until the earliest one becomes available."""
        if not self.rate_limited_models:
            return self.current_model, 0.0

        earliest_model = min(self.rate_limited_models, key=self.rate_limited_models.get)
        wait_seconds = max(1.0, self.rate_limited_models[earliest_model] - time.time())
        logger.info(f"⏳ All models are currently rate-limited. Auto-pausing for {wait_seconds:.1f}s until '{earliest_model}' is available...")
        time.sleep(wait_seconds)
        if earliest_model in self.rate_limited_models:
            del self.rate_limited_models[earliest_model]
        return earliest_model, wait_seconds

    def send_message(self, system_prompt: str, user_prompt: str) -> str:
        """Sends a message within the persistent conversation, handling failover and rate limits."""
        # Add to history
        self.conversation_history.append({"role": "user", "content": user_prompt})

        # Check if at least one provider has credentials
        has_any_key = any([
            self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY"),
            self.config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"),
            self.config.openai_api_key or os.environ.get("OPENAI_API_KEY"),
        ])
        if not has_any_key:
            raise RuntimeError(
                "No AI API keys detected! Please set at least one of:\n"
                "  • export GEMINI_API_KEY='...'\n"
                "  • export ANTHROPIC_API_KEY='...'\n"
                "  • export OPENAI_API_KEY='...'\n"
                "Or launch in ChatGPT Web Browser mode using:\n"
                "  • ./run_vibe_bot.sh browser"
            )

        max_attempts = len(self.config.model_priority) * 2
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            model = self.get_available_model()
            if not model:
                model, _ = self.wait_for_any_model_availability()

            logger.info(f"🚀 Dispatching upgrade prompt to model: {model} (Attempt {attempts})")

            try:
                if "gemini" in model.lower():
                    response_text = self._call_gemini(model, system_prompt)
                elif "claude" in model.lower() or "sonnet" in model.lower():
                    response_text = self._call_claude(model, system_prompt)
                elif "chatgpt" in model.lower() or "openai" in model.lower() or "gpt" in model.lower():
                    response_text = self._call_openai(model, system_prompt)
                else:
                    response_text = self._call_gemini(model, system_prompt)

                # Persist assistant response in same thread
                self.conversation_history.append({"role": "assistant", "content": response_text})
                return response_text

            except RateLimitException as rle:
                logger.warning(f"Rate limit hit on {model}: {rle}")
                self.record_rate_limit(model, backoff_seconds=self.config.rate_limit_initial_delay_sec)
                # Rotate to next model immediately
                self.current_model_index = (self.current_model_index + 1) % len(self.config.model_priority)
            except Exception as e:
                logger.error(f"Error calling {model}: {e}")
                self.record_rate_limit(model, backoff_seconds=30)
                self.current_model_index = (self.current_model_index + 1) % len(self.config.model_priority)

        raise RuntimeError("Exceeded maximum retry attempts across all configured models.")

    def _call_gemini(self, model_name: str, system_prompt: str) -> str:
        api_key = self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Normalize model identifier
        target_model = "gemini-2.0-flash" if "flash" in model_name else "gemini-1.5-pro"
        if "3.8" in model_name:
            target_model = model_name

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        
        # Prepare contents from conversation history
        contents = []
        for msg in self.conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
                return ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                raise RateLimitException(f"Gemini API returned HTTP {e.code}: {e.reason}")
            raise e

    def _call_claude(self, model_name: str, system_prompt: str) -> str:
        api_key = self.config.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured.")

        target_model = "claude-3-7-sonnet-20250219" if "sonnet" in model_name else "claude-3-5-sonnet-20241022"

        url = "https://api.anthropic.com/v1/messages"
        messages = [{"role": m["role"], "content": m["content"]} for m in self.conversation_history]

        payload = {
            "model": target_model,
            "max_tokens": 8192,
            "system": system_prompt,
            "messages": messages
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                for block in result.get("content", []):
                    if block.get("type") == "text":
                        return block.get("text", "")
                return ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 529):
                raise RateLimitException(f"Claude API returned HTTP {e.code}: {e.reason}")
            raise e

    def _call_openai(self, model_name: str, system_prompt: str) -> str:
        api_key = self.config.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        target_model = "gpt-4o"
        url = "https://api.openai.com/v1/chat/completions"

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend([{"role": m["role"], "content": m["content"]} for m in self.conversation_history])

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.2
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0]["message"]["content"]
                return ""
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                raise RateLimitException(f"OpenAI API returned HTTP {e.code}: {e.reason}")
            raise e


class RateLimitException(Exception):
    pass
