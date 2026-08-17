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
        """Scans DOM for form input fields, textareas, selects, and file pickers, specialized for Google Forms."""
        if not self.page:
            return []
        try:
            inputs_data = await self.page.evaluate("""() => {
                // 1. Google Forms specialized items inspection
                const googleFormItems = Array.from(document.querySelectorAll('div[role="listitem"], div[jsmodel]'));
                if (googleFormItems.length > 0) {
                    const results = [];
                    googleFormItems.forEach((container, idx) => {
                        const heading = container.querySelector('div[role="heading"], .M7eMe, span');
                        const labelText = heading ? heading.innerText : '';
                        const input = container.querySelector('input[type="text"], input[type="email"], input[type="tel"], textarea');
                        if (input) {
                            results.push({
                                id: input.id || `gform_input_${idx}`,
                                name: input.name || '',
                                type: input.type || 'text',
                                tagName: input.tagName.toLowerCase(),
                                placeholder: input.placeholder || '',
                                labelText: (labelText || '').trim().split('\\n')[0],
                                value: input.value || '',
                                required: container.innerText.includes('*'),
                                index: idx
                            });
                        }
                    });
                    if (results.length > 0) return results;
                }

                // 2. Standard HTML inputs fallback
                const elements = Array.from(document.querySelectorAll('input, textarea, select'));
                return elements.map((el, idx) => {
                    let labelText = '';
                    if (el.id) {
                        const lbl = document.querySelector(`label[for="${el.id}"]`);
                        if (lbl) labelText = lbl.innerText;
                    }
                    if (!labelText && el.closest('label')) labelText = el.closest('label').innerText;
                    if (!labelText && el.closest('div')) labelText = el.closest('div').innerText;
                    if (!labelText && el.placeholder) labelText = el.placeholder;
                    if (!labelText && el.name) labelText = el.name;
                    if (!labelText && el.getAttribute('aria-label')) labelText = el.getAttribute('aria-label');

                    return {
                        id: el.id || `input_${idx}`,
                        name: el.name || '',
                        type: el.type || el.tagName.toLowerCase(),
                        tagName: el.tagName.toLowerCase(),
                        placeholder: el.placeholder || '',
                        labelText: (labelText || '').trim().split('\\n')[0],
                        value: el.value || '',
                        required: el.required || false,
                        index: idx
                    };
                });
            }""")
            return inputs_data
        except Exception as e:
            logger.error(f"Error inspecting form inputs: {e}")
            return []

    async def fill_input_by_index_or_name(self, idx: int, name: str, val: str) -> bool:
        """Fills input element directly on page and triggers DOM input/change events."""
        if not self.page:
            return False
        try:
            success = await self.page.evaluate("""([idx, nameStr, valStr]) => {
                let input = null;
                if (nameStr) {
                    input = document.querySelector(`input[name="${nameStr}"], textarea[name="${nameStr}"]`);
                }
                if (!input) {
                    const all = Array.from(document.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], textarea'));
                    input = all[idx];
                }
                if (input) {
                    input.focus();
                    input.value = valStr;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.blur();
                    return true;
                }
                return false;
            }""", [idx, name, val])
            return success
        except Exception as e:
            logger.error(f"Error filling input idx {idx}: {e}")
            return False

    async def click_submit_button(self) -> bool:
        """Clicks the Submit button on Google Form or standard HTML form."""
        if not self.page:
            return False
        try:
            clicked = await self.page.evaluate("""() => {
                const btn = Array.from(document.querySelectorAll('div[role="button"], span, button, input[type="submit"]'))
                    .find(el => el.innerText && el.innerText.trim().toLowerCase() === 'submit');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }""")
            if clicked:
                logger.info("Clicked Submit button on Chrome page.")
                await asyncio.sleep(2.0)
                return True
            return False
        except Exception as e:
            logger.error(f"Error clicking submit button: {e}")
            return False

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
