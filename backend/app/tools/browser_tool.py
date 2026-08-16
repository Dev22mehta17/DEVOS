import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

CDP_URL = os.getenv("CHROME_CDP_URL", "http://localhost:9222")

class BrowserTool:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_connected = False

    async def initialize(self) -> bool:
        """Attempts connection to Chrome CDP port 9222, fallback to persistent context."""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()

            # Attempt 1: Connect to running Chrome CDP
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(CDP_URL)
                contexts = self.browser.contexts
                self.context = contexts[0] if contexts else await self.browser.new_context()
                pages = self.context.pages
                self.page = pages[0] if pages else await self.context.new_page()
                self.is_connected = True
                logger.info(f"Successfully attached to active Chrome via CDP at {CDP_URL}")
                return True
            except Exception as cdp_err:
                logger.warning(f"Chrome CDP connection failed ({cdp_err}). Launching standalone Playwright Chromium...")

            # Attempt 2: Standalone Playwright Chromium with stealth flags
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            self.is_connected = True
            logger.info("Launched Playwright Chromium instance with stealth flags.")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Playwright browser tool: {e}")
            self.is_connected = False
            return False

    async def navigate(self, url: str) -> Dict[str, Any]:
        if not self.page:
            await self.initialize()
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self.page.title()
            current_url = self.page.url
            return {
                "status": "SUCCESS",
                "title": title,
                "url": current_url
            }
        except Exception as e:
            logger.error(f"Navigation error for {url}: {e}")
            return {"status": "ERROR", "message": str(e)}

    async def get_page_info(self) -> Dict[str, Any]:
        if not self.page:
            return {"status": "ERROR", "message": "No active page"}
        title = await self.page.title()
        url = self.page.url
        return {"title": title, "url": url}

    async def inspect_inputs(self) -> List[Dict[str, Any]]:
        """Scans DOM for form input fields, textareas, selects, and file pickers."""
        if not self.page:
            return []
        try:
            inputs_data = await self.page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('input, textarea, select'));
                return elements.map((el, idx) => {
                    let labelText = '';
                    if (el.id) {
                        const lbl = document.querySelector(`label[for="${el.id}"]`);
                        if (lbl) labelText = lbl.innerText;
                    }
                    if (!labelText && el.closest('label')) {
                        labelText = el.closest('label').innerText;
                    }
                    if (!labelText && el.placeholder) {
                        labelText = el.placeholder;
                    }
                    if (!labelText && el.name) {
                        labelText = el.name;
                    }
                    if (!labelText && el.getAttribute('aria-label')) {
                        labelText = el.getAttribute('aria-label');
                    }
                    return {
                        id: el.id || `input_${idx}`,
                        name: el.name || '',
                        type: el.type || el.tagName.toLowerCase(),
                        tagName: el.tagName.toLowerCase(),
                        placeholder: el.placeholder || '',
                        labelText: (labelText || '').trim(),
                        value: el.value || '',
                        required: el.required || false
                    };
                });
            }""")
            return inputs_data
        except Exception as e:
            logger.error(f"Error inspecting form inputs: {e}")
            return []

    async def fill_input(self, selector: str, value: str) -> bool:
        if not self.page:
            return False
        try:
            await self.page.fill(selector, value)
            return True
        except Exception as e:
            logger.error(f"Error filling input {selector}: {e}")
            return False

    async def upload_file(self, selector: str, file_path: str) -> bool:
        if not self.page:
            return False
        try:
            await self.page.set_input_files(selector, file_path)
            return True
        except Exception as e:
            logger.error(f"Error uploading file {file_path} to {selector}: {e}")
            return False

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error closing browser tool: {e}")

browser_tool = BrowserTool()
