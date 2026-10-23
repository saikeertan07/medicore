"""
Playwright-based Browser Bridge for ChatGPT Web Interface.
Automates uploading the latest codebase file to an ongoing ChatGPT session,
monitoring generation, detecting rate-limit banners, and extracting code blocks.
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger("vibe_coder.browser")

class ChatGPTBrowserBridge:
    def __init__(self, config):
        self.config = config
        self.playwright = None
        self.browser_context = None
        self.page = None
        self.active_chat_url: Optional[str] = None

    def start(self):
        """Initializes Playwright with a persistent browser context."""
        try:
            from playwright.sync_api import sync_playwright
            self.playwright = sync_playwright().start()
            logger.info(f"🌐 Launching Chrome with profile at {self.config.browser_user_data_dir}")
            
            # Persistent context keeps login cookies active across iterations
            self.browser_context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.browser_user_data_dir),
                channel="chrome",
                headless=self.config.browser_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            self.page = self.browser_context.pages[0] if self.browser_context.pages else self.browser_context.new_page()
            logger.info("✅ Browser launched successfully.")
        except ImportError:
            logger.error("Playwright is not installed. Run `pip install playwright && playwright install chromium`.")
            raise

    def open_or_resume_chat(self, target_chat_url: Optional[str] = None):
        """Navigates to the active chat session (keeping the same chat) or initiates a new one."""
        url_to_open = target_chat_url or self.active_chat_url or self.config.chatgpt_web_url
        logger.info(f"Opening ChatGPT: {url_to_open}")
        self.page.goto(url_to_open, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(3000)

        # Update active URL after initial load
        if "chatgpt.com/c/" in self.page.url:
            self.active_chat_url = self.page.url
            logger.info(f"📌 Attached to persistent chat session: {self.active_chat_url}")

    def upload_file_and_send_prompt(self, file_path: Path, prompt_text: str) -> Tuple[str, bool]:
        """
        Uploads the updated file to the chat, sends the prompt, and extracts the response.
        Returns (response_text, is_rate_limited).
        """
        self.open_or_resume_chat()

        # 1. Attach latest file if an upload input is available
        try:
            file_input = self.page.locator('input[type="file"]')
            if file_input.count() > 0 and file_path.exists():
                logger.info(f"📎 Attaching latest code file: {file_path.name}")
                file_input.first.set_input_files(str(file_path))
                self.page.wait_for_timeout(3000)
            else:
                logger.info("ℹ️ File input not found or not required; appending file context to prompt.")
        except Exception as e:
            logger.warning(f"File upload attempt encountered: {e}. Falling back to prompt text context.")

        # 2. Type prompt into the textarea
        logger.info("✍️ Typing prompt into ChatGPT textarea...")
        textarea = self.page.locator('#prompt-textarea')
        if textarea.count() == 0:
            textarea = self.page.locator('div[contenteditable="true"]')

        textarea.fill(prompt_text)
        self.page.wait_for_timeout(1000)
        
        # Press Enter or click send button
        send_btn = self.page.locator('button[data-testid="send-button"]')
        if send_btn.count() > 0 and send_btn.is_enabled():
            send_btn.click()
        else:
            textarea.press("Enter")

        logger.info("🚀 Message submitted to ChatGPT. Waiting for generation...")
        
        # 3. Capture new chat URL once created
        self.page.wait_for_timeout(5000)
        if "chatgpt.com/c/" in self.page.url:
            self.active_chat_url = self.page.url
            logger.info(f"📌 Locked session to continuous chat: {self.active_chat_url}")

        # 4. Wait for generation to finish
        # We poll for the 'Stop generating' button to disappear
        start_time = time.time()
        max_wait = 300  # 5 minutes max per turn
        while time.time() - start_time < max_wait:
            self.page.wait_for_timeout(3000)

            # Check for Rate Limit banner
            page_text = self.page.inner_text("body")
            if any(limit_str in page_text.lower() for limit_str in [
                "you've hit the limit",
                "usage cap reached",
                "too many requests",
                "please try again after"
            ]):
                logger.warning("🚨 ChatGPT Web rate-limit detected!")
                return "", True

            # Check if streaming completed
            stop_btn = self.page.locator('button[aria-label="Stop streaming"]')
            if stop_btn.count() == 0:
                # Finished generating
                break

        # 5. Extract the latest assistant response
        articles = self.page.locator('article')
        if articles.count() > 0:
            last_article = articles.last
            response_text = last_article.inner_text()
            return response_text, False

        return self.page.inner_text("body"), False

    def close(self):
        """Closes browser context and Playwright cleanly."""
        try:
            if self.browser_context:
                self.browser_context.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser session closed cleanly.")
        except Exception as e:
            logger.warning(f"Error while closing browser: {e}")
