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
        """Scans DOM for ALL form field types: text, radio, checkbox, dropdown, file, specialized for Google Forms."""
        if not self.page:
            return []
        try:
            try:
                await self.page.wait_for_selector('input[type="text"], textarea, div[role="heading"]', timeout=8000)
            except Exception:
                pass

            inputs_data = await self.page.evaluate("""() => {
                const results = [];
                let questionIndex = 0;

                // Helper: get the question heading from a container
                function getHeading(container) {
                    if (!container) return '';
                    const headingEl = container.querySelector('div[role="heading"], .M7eMe, span.M7eMe');
                    return headingEl ? headingEl.innerText.trim().split('\\n')[0] : '';
                }

                // Helper: check if required (has *)
                function isRequired(container) {
                    return container ? container.innerText.includes('*') : false;
                }

                // Walk through all Google Forms question blocks (div[role="listitem"])
                const questionBlocks = document.querySelectorAll('div[role="listitem"]');
                
                questionBlocks.forEach((block) => {
                    const heading = getHeading(block);
                    const required = isRequired(block);

                    // 1. Text/Email/Tel inputs and textareas
                    const textInputs = block.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input[type="date"], textarea');
                    if (textInputs.length > 0) {
                        textInputs.forEach((inp) => {
                            results.push({
                                id: inp.id || `input_${questionIndex}`,
                                name: inp.name || '',
                                type: inp.type || inp.tagName.toLowerCase() === 'textarea' ? 'textarea' : 'text',
                                tagName: inp.tagName.toLowerCase(),
                                placeholder: inp.placeholder || '',
                                labelText: heading || inp.getAttribute('aria-label') || inp.placeholder || '',
                                value: inp.value || '',
                                required: required,
                                questionIndex: questionIndex,
                                fieldType: 'text'
                            });
                        });
                        questionIndex++;
                        return;
                    }

                    // 2. Radio buttons (Google Forms: div[role="radiogroup"] > div[role="radio"])
                    const radioGroup = block.querySelector('div[role="radiogroup"], fieldset[role="radiogroup"]');
                    if (radioGroup) {
                        const radios = radioGroup.querySelectorAll('div[role="radio"], label[role="radio"]');
                        const options = [];
                        let selectedOption = null;
                        radios.forEach((radio) => {
                            const label = radio.getAttribute('data-value') || radio.innerText.trim();
                            const checked = radio.getAttribute('aria-checked') === 'true';
                            if (label) options.push(label);
                            if (checked) selectedOption = label;
                        });
                        if (options.length > 0) {
                            results.push({
                                id: `radio_${questionIndex}`,
                                type: 'radio',
                                labelText: heading,
                                options: options,
                                value: selectedOption || '',
                                required: required,
                                questionIndex: questionIndex,
                                fieldType: 'radio'
                            });
                            questionIndex++;
                            return;
                        }
                    }

                    // 3. Checkboxes (Google Forms: div[role="group"] with div[role="checkbox"])
                    const checkboxes = block.querySelectorAll('div[role="checkbox"], label[role="checkbox"]');
                    if (checkboxes.length > 0) {
                        const options = [];
                        const selected = [];
                        checkboxes.forEach((cb) => {
                            const label = cb.getAttribute('data-answer-value') || cb.getAttribute('aria-label') || cb.innerText.trim();
                            const checked = cb.getAttribute('aria-checked') === 'true';
                            if (label) {
                                options.push(label);
                                if (checked) selected.push(label);
                            }
                        });
                        if (options.length > 0) {
                            results.push({
                                id: `checkbox_${questionIndex}`,
                                type: 'checkbox',
                                labelText: heading,
                                options: options,
                                value: selected.join(', '),
                                required: required,
                                questionIndex: questionIndex,
                                fieldType: 'checkbox'
                            });
                            questionIndex++;
                            return;
                        }
                    }

                    // 4. Dropdown (Google Forms: div[role="listbox"] with div[role="option"])
                    const listbox = block.querySelector('div[role="listbox"]');
                    if (listbox) {
                        const optionEls = listbox.querySelectorAll('div[role="option"], span[role="option"]');
                        const options = [];
                        let selectedOption = null;
                        optionEls.forEach((opt) => {
                            const label = opt.getAttribute('data-value') || opt.innerText.trim();
                            const isSelected = opt.getAttribute('aria-selected') === 'true';
                            if (label && label !== 'Choose') options.push(label);
                            if (isSelected && label !== 'Choose') selectedOption = label;
                        });
                        if (options.length > 0) {
                            results.push({
                                id: `dropdown_${questionIndex}`,
                                type: 'dropdown',
                                labelText: heading,
                                options: options,
                                value: selectedOption || '',
                                required: required,
                                questionIndex: questionIndex,
                                fieldType: 'dropdown'
                            });
                            questionIndex++;
                            return;
                        }
                    }

                    // 5. File Upload ("Add file" button)
                    const fileBtn = Array.from(block.querySelectorAll('div[role="button"], span'))
                        .find(el => el.innerText && el.innerText.trim().toLowerCase().includes('add file'));
                    if (fileBtn) {
                        results.push({
                            id: `file_btn_${questionIndex}`,
                            name: 'file_upload',
                            type: 'file',
                            tagName: 'button',
                            labelText: heading || 'Resume / File Upload',
                            required: required,
                            questionIndex: questionIndex,
                            fieldType: 'file'
                        });
                        questionIndex++;
                        return;
                    }
                });

                // Fallback: also scan for inputs NOT inside listitem blocks (non-Google-Forms pages)
                if (results.length === 0) {
                    const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], textarea'));
                    inputs.forEach((inp, idx) => {
                        let container = inp.closest('div[role="listitem"]') || inp.closest('div[jsmodel]') || inp.parentElement?.parentElement;
                        let headingText = '';
                        if (container) {
                            const headingEl = container.querySelector('div[role="heading"], .M7eMe, span');
                            if (headingEl) headingText = headingEl.innerText;
                        }
                        if (!headingText && inp.getAttribute('aria-label')) headingText = inp.getAttribute('aria-label');
                        if (!headingText && inp.placeholder) headingText = inp.placeholder;
                        results.push({
                            id: inp.id || `input_${idx}`,
                            name: inp.name || '',
                            type: inp.type || 'text',
                            tagName: inp.tagName.toLowerCase(),
                            placeholder: inp.placeholder || '',
                            labelText: (headingText || '').trim().split('\\n')[0],
                            value: inp.value || '',
                            required: container ? container.innerText.includes('*') : false,
                            questionIndex: idx,
                            fieldType: 'text'
                        });
                    });
                }

                return results;
            }""")
            return inputs_data
        except Exception as e:
            logger.error(f"Error inspecting form inputs: {e}")
            return []

    async def fill_input_by_index_or_name(self, idx: int, name: str, val: str) -> bool:
        """Fills text input element directly on page and triggers DOM input/change events."""
        if not self.page:
            return False
        try:
            success = await self.page.evaluate("""([idx, nameStr, valStr]) => {
                let input = null;
                if (nameStr) {
                    input = document.querySelector(`input[name="${nameStr}"], textarea[name="${nameStr}"]`);
                }
                if (!input) {
                    const all = Array.from(document.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input[type="date"], textarea'));
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

    async def select_radio_option(self, question_index: int, option_text: str) -> bool:
        """Clicks a radio button option in a Google Form by question index and option text."""
        if not self.page:
            return False
        try:
            success = await self.page.evaluate("""([qIdx, optText]) => {
                const blocks = document.querySelectorAll('div[role="listitem"]');
                let radioBlockIdx = 0;
                for (const block of blocks) {
                    const radioGroup = block.querySelector('div[role="radiogroup"], fieldset[role="radiogroup"]');
                    if (!radioGroup) continue;
                    if (radioBlockIdx === qIdx) {
                        const radios = radioGroup.querySelectorAll('div[role="radio"], label[role="radio"]');
                        for (const radio of radios) {
                            const label = (radio.getAttribute('data-value') || radio.innerText.trim()).toLowerCase();
                            if (label === optText.toLowerCase() || label.includes(optText.toLowerCase())) {
                                radio.click();
                                return true;
                            }
                        }
                        // Fallback: try partial match
                        for (const radio of radios) {
                            const label = (radio.getAttribute('data-value') || radio.innerText.trim()).toLowerCase();
                            if (optText.toLowerCase().includes(label) || label.includes(optText.toLowerCase().substring(0, 4))) {
                                radio.click();
                                return true;
                            }
                        }
                        return false;
                    }
                    radioBlockIdx++;
                }
                return false;
            }""", [question_index, option_text])
            if success:
                logger.info(f"[Browser] Selected radio option '{option_text}' at question index {question_index}")
            return success
        except Exception as e:
            logger.error(f"Error selecting radio option: {e}")
            return False

    async def select_checkbox_options(self, question_index: int, option_texts: List[str]) -> bool:
        """Clicks multiple checkbox options in a Google Form by question index."""
        if not self.page:
            return False
        try:
            success = await self.page.evaluate("""([qIdx, optTexts]) => {
                const blocks = document.querySelectorAll('div[role="listitem"]');
                let cbBlockIdx = 0;
                for (const block of blocks) {
                    const checkboxes = block.querySelectorAll('div[role="checkbox"], label[role="checkbox"]');
                    if (checkboxes.length === 0) continue;
                    if (cbBlockIdx === qIdx) {
                        let clicked = 0;
                        for (const cb of checkboxes) {
                            const label = (cb.getAttribute('data-answer-value') || cb.getAttribute('aria-label') || cb.innerText.trim()).toLowerCase();
                            for (const opt of optTexts) {
                                if (label === opt.toLowerCase() || label.includes(opt.toLowerCase())) {
                                    if (cb.getAttribute('aria-checked') !== 'true') {
                                        cb.click();
                                    }
                                    clicked++;
                                    break;
                                }
                            }
                        }
                        return clicked > 0;
                    }
                    cbBlockIdx++;
                }
                return false;
            }""", [question_index, option_texts])
            if success:
                logger.info(f"[Browser] Selected checkbox options {option_texts} at question index {question_index}")
            return success
        except Exception as e:
            logger.error(f"Error selecting checkbox options: {e}")
            return False

    async def select_dropdown_option(self, question_index: int, option_text: str) -> bool:
        """Opens a dropdown and selects an option in a Google Form."""
        if not self.page:
            return False
        try:
            # First, click the dropdown to open it
            opened = await self.page.evaluate("""(qIdx) => {
                const blocks = document.querySelectorAll('div[role="listitem"]');
                let ddBlockIdx = 0;
                for (const block of blocks) {
                    const listbox = block.querySelector('div[role="listbox"]');
                    if (!listbox) continue;
                    if (ddBlockIdx === qIdx) {
                        listbox.click();
                        return true;
                    }
                    ddBlockIdx++;
                }
                return false;
            }""", question_index)

            if not opened:
                return False

            await asyncio.sleep(0.8)  # Wait for dropdown animation

            # Now select the option from the opened dropdown
            success = await self.page.evaluate("""(optText) => {
                // Google Forms dropdown options appear as div[role="option"] in a presentation layer
                const options = document.querySelectorAll('div[role="option"], div[data-value]');
                for (const opt of options) {
                    const label = (opt.getAttribute('data-value') || opt.innerText.trim()).toLowerCase();
                    if (label === optText.toLowerCase() || label.includes(optText.toLowerCase())) {
                        opt.click();
                        return true;
                    }
                }
                return false;
            }""", option_text)

            if success:
                logger.info(f"[Browser] Selected dropdown option '{option_text}' at question index {question_index}")
            return success
        except Exception as e:
            logger.error(f"Error selecting dropdown option: {e}")
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

    async def upload_file_to_google_form(self, file_path: str) -> bool:
        """Uploads a local file to a Google Form file upload field.
        
        Google Forms file upload uses a Google Picker iframe dialog:
        1. Click 'Add file' button on the form
        2. A Google Picker iframe overlay appears (NOT a popup window)
        3. Inside the iframe, click 'Browse' → triggers native OS file chooser
        4. Select file → upload starts to Google Drive
        5. Click 'Upload' to confirm and attach to form
        """
        if not self.page or not file_path or not os.path.exists(file_path):
            logger.warning(f"[Upload] File path invalid or missing: {file_path}")
            return False

        try:
            logger.info(f"[Upload] Starting Google Form file upload: {file_path}")

            # Method 1: Try direct input[type="file"] (works on standard HTML forms)
            file_inputs = await self.page.query_selector_all('input[type="file"]')
            if file_inputs:
                for f_inp in file_inputs:
                    try:
                        await f_inp.set_input_files(file_path)
                        logger.info("[Upload] ✅ Uploaded via input[type='file']")
                        await asyncio.sleep(2.0)
                        return True
                    except Exception as e:
                        logger.debug(f"[Upload] Direct file input failed: {e}")

            # Method 2: Google Forms — click 'Add file' which opens a Google Picker iframe dialog
            add_btn = await self.page.query_selector(
                'div[role="button"][aria-label*="Add file"], '
                'div[role="button"]:has-text("Add file"), '
                'span:has-text("Add file"), '
                'span:has-text("Add File")'
            )
            
            if not add_btn:
                logger.warning("[Upload] Could not find 'Add file' button")
                return False

            logger.info("[Upload] Found 'Add file' button, clicking...")
            await add_btn.click()
            await asyncio.sleep(3.0)

            # The Google Picker opens as an iframe dialog on the SAME page
            # Find the picker iframe (src contains "docs.google.com/picker")
            picker_frame = None
            for frame in self.page.frames:
                if "docs.google.com/picker" in frame.url or "picker" in frame.url:
                    picker_frame = frame
                    logger.info(f"[Upload] Found Google Picker iframe: {frame.url[:80]}...")
                    break

            if not picker_frame:
                # Try finding iframe element directly
                iframe_el = await self.page.query_selector('iframe[src*="picker"], iframe[src*="docs.google.com"]')
                if iframe_el:
                    picker_frame = await iframe_el.content_frame()
                    logger.info("[Upload] Found picker iframe via element query")

            if not picker_frame:
                logger.warning("[Upload] Could not find Google Picker iframe")
                # Last resort: try file chooser on page level
                try:
                    async with self.page.expect_file_chooser(timeout=5000) as fc_info:
                        # Try clicking Browse if it's on the main page
                        browse = await self.page.query_selector('button:has-text("Browse")')
                        if browse:
                            await browse.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(file_path)
                    logger.info("[Upload] ✅ Uploaded via main page file chooser")
                    await asyncio.sleep(5.0)
                    return True
                except Exception:
                    pass
                return False

            # Inside the picker iframe, find and click the "Browse" button
            # File choosers bubble up to the PAGE level even from iframes
            browse_btn = None
            browse_selectors = [
                'button:has-text("Browse")',
                'div[role="button"]:has-text("Browse")',
                'span:has-text("Browse")',
                '.picker-upload-button',
            ]
            for sel in browse_selectors:
                try:
                    browse_btn = await picker_frame.wait_for_selector(sel, timeout=5000)
                    if browse_btn:
                        logger.info(f"[Upload] Found Browse button in iframe: {sel}")
                        break
                except Exception:
                    continue

            if not browse_btn:
                logger.warning("[Upload] Could not find Browse button inside picker iframe")
                # Try hidden file input inside iframe
                try:
                    frame_file_input = await picker_frame.query_selector('input[type="file"]')
                    if frame_file_input:
                        await frame_file_input.set_input_files(file_path)
                        logger.info("[Upload] ✅ Uploaded via iframe's input[type=file]")
                        await asyncio.sleep(5.0)
                        return True
                except Exception:
                    pass
                return False

            # Click Browse and handle the native file chooser
            # IMPORTANT: expect_file_chooser must be on the PAGE level, not the frame
            try:
                async with self.page.expect_file_chooser(timeout=10000) as fc_info:
                    await browse_btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(file_path)
                logger.info(f"[Upload] ✅ File selected via Browse button: {os.path.basename(file_path)}")
            except Exception as fc_err:
                logger.error(f"[Upload] File chooser from Browse failed: {fc_err}")
                return False

            # Wait for the file to upload to Google Drive (progress bar shows)
            logger.info("[Upload] Waiting for file to upload to Google Drive...")
            await asyncio.sleep(10.0)

            # Click 'Upload' button inside the picker iframe to confirm
            try:
                upload_confirm = None
                upload_selectors = [
                    'button:has-text("Upload")',
                    'div[role="button"]:has-text("Upload")',
                    '#picker\\:ap\\:2',
                ]
                for sel in upload_selectors:
                    try:
                        upload_confirm = await picker_frame.wait_for_selector(sel, timeout=5000)
                        if upload_confirm:
                            break
                    except Exception:
                        continue

                if upload_confirm:
                    await upload_confirm.click()
                    logger.info("[Upload] Clicked Upload confirm button")
                    await asyncio.sleep(5.0)
                else:
                    logger.info("[Upload] No Upload confirm button found — file may auto-attach")
            except Exception as e:
                logger.debug(f"[Upload] Upload confirm click issue: {e}")

            # Wait for the picker dialog to close and the file to attach
            await asyncio.sleep(3.0)
            logger.info("[Upload] ✅ File upload completed successfully")
            return True

        except Exception as e:
            logger.error(f"[Upload] Fatal error: {e}")
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
