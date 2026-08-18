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

    async def get_active_page(self) -> Page:
        """Returns an active, alive Playwright Page, automatically reconnecting via CDP if closed."""
        try:
            if not self.browser or not self.browser.is_connected():
                logger.info("[BrowserTool] Reconnecting to Chrome via CDP...")
                await self.initialize()

            if not self.context:
                contexts = self.browser.contexts if self.browser else []
                self.context = contexts[0] if contexts else await self.browser.new_context()

            # 1. Reuse existing non-closed page
            if self.page and not self.page.is_closed():
                return self.page

            # 2. Check existing open pages in context
            if self.context:
                pages = self.context.pages
                for p in pages:
                    if not p.is_closed():
                        self.page = p
                        return self.page

                # 3. Create new page if all were closed
                self.page = await self.context.new_page()
                return self.page
        except Exception as e:
            logger.warning(f"[BrowserTool] Recovering active page: {e}")
            await self.initialize()
            if self.page and not self.page.is_closed():
                return self.page
            if self.context:
                self.page = await self.context.new_page()
                return self.page

        raise RuntimeError("Failed to acquire active Chrome page.")

    async def navigate(self, url: str) -> Dict[str, Any]:
        page = await self.get_active_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await page.title()
            current_url = page.url
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
        """Scans DOM for ALL form field types: radio, checkbox, dropdown, file, text, specialized for Google Forms."""
        if not self.page:
            return []
        try:
            try:
                await self.page.wait_for_selector('div[role="listitem"], input, textarea, div[role="heading"]', timeout=8000)
            except Exception:
                pass

            inputs_data = await self.page.evaluate("""() => {
                const results = [];
                let questionIndex = 0;

                // Helper: get the question heading from a container
                function getHeading(container) {
                    if (!container) return '';
                    const headingEl = container.querySelector('div[role="heading"], .M7eMe, span.M7eMe, .F9vfv');
                    if (headingEl) {
                        return headingEl.innerText.trim().split('\\n')[0].replace(/\\*$/, '').trim();
                    }
                    return '';
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

                    // 1. Check for File Upload ("Add file" button) FIRST
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

                    // 2. Check for Radio buttons (Google Forms: div[role="radiogroup"] > div[role="radio"]) FIRST
                    const radioGroup = block.querySelector('div[role="radiogroup"], fieldset[role="radiogroup"]');
                    if (radioGroup) {
                        const radios = radioGroup.querySelectorAll('div[role="radio"], label[role="radio"]');
                        const options = [];
                        let selectedOption = null;
                        radios.forEach((radio) => {
                            const label = radio.getAttribute('data-value') || 
                                          radio.getAttribute('aria-label') || 
                                          radio.innerText.trim();
                            const checked = radio.getAttribute('aria-checked') === 'true';
                            if (label && !options.includes(label)) options.push(label);
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

                    // 3. Check for Checkboxes (Google Forms: div[role="group"] with div[role="checkbox"])
                    const checkboxes = block.querySelectorAll('div[role="checkbox"], label[role="checkbox"]');
                    if (checkboxes.length > 0) {
                        const options = [];
                        const selected = [];
                        checkboxes.forEach((cb) => {
                            const label = cb.getAttribute('data-answer-value') || cb.getAttribute('aria-label') || cb.innerText.trim();
                            const checked = cb.getAttribute('aria-checked') === 'true';
                            if (label && !options.includes(label)) {
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

                    // 4. Check for Dropdown (Google Forms: div[role="listbox"] with div[role="option"])
                    const listbox = block.querySelector('div[role="listbox"]');
                    if (listbox) {
                        const optionEls = listbox.querySelectorAll('div[role="option"], span[role="option"]');
                        const options = [];
                        let selectedOption = null;
                        optionEls.forEach((opt) => {
                            const label = opt.getAttribute('data-value') || opt.innerText.trim();
                            const isSelected = opt.getAttribute('aria-selected') === 'true';
                            if (label && label !== 'Choose' && !options.includes(label)) options.push(label);
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

                    // 5. Only if not radio/checkbox/dropdown/file, check for Text/Email/Tel/Textarea inputs
                    const textInputs = block.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input[type="date"], textarea');
                    if (textInputs.length > 0) {
                        textInputs.forEach((inp) => {
                            results.push({
                                id: inp.id || `input_${questionIndex}`,
                                name: inp.name || '',
                                type: inp.tagName.toLowerCase() === 'textarea' ? 'textarea' : (inp.type || 'text'),
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

    async def select_radio_option(self, question_index: int, option_text: str, question_label: str = "") -> bool:
        """Clicks a radio button option in a Google Form by question label or index."""
        if not self.page or not option_text:
            return False
        try:
            success = await self.page.evaluate("""([qIdx, optText, qLabel]) => {
                const optClean = (optText || '').toLowerCase().trim();
                const labelClean = (qLabel || '').toLowerCase().trim();
                const blocks = Array.from(document.querySelectorAll('div[role="listitem"]'));

                // Find the target block by label match or by index
                let targetBlock = null;
                if (labelClean) {
                    targetBlock = blocks.find(b => {
                        const heading = b.querySelector('div[role="heading"], .M7eMe, span');
                        return heading && heading.innerText.toLowerCase().includes(labelClean);
                    });
                }
                if (!targetBlock && qIdx < blocks.length) {
                    targetBlock = blocks[qIdx];
                }

                // If target block found, search within it
                const searchRoot = targetBlock || document;
                const radios = Array.from(searchRoot.querySelectorAll('div[role="radio"], label[role="radio"]'));

                for (const radio of radios) {
                    const rValue = (radio.getAttribute('data-value') || '').toLowerCase().trim();
                    const rText = (radio.innerText || '').toLowerCase().trim();
                    const rAria = (radio.getAttribute('aria-label') || '').toLowerCase().trim();

                    if (rValue === optClean || rText === optClean || rAria === optClean ||
                        rValue.includes(optClean) || rText.includes(optClean) || optClean.includes(rValue)) {
                        radio.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        radio.click();
                        // Dispatch mouse & change events
                        radio.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        const parent = radio.parentElement;
                        if (parent) parent.click();
                        return true;
                    }
                }
                return false;
            }""", [question_index, option_text, question_label])
            if success:
                logger.info(f"[Browser] ✅ Selected radio option '{option_text}' for question '{question_label}' (idx {question_index})")
            else:
                logger.warning(f"[Browser] ❌ Failed to find radio option '{option_text}' for question '{question_label}'")
            return success
        except Exception as e:
            logger.error(f"Error selecting radio option: {e}")
            return False

    async def select_checkbox_options(self, question_index: int, option_texts: List[str], question_label: str = "") -> bool:
        """Clicks multiple checkbox options in a Google Form by question label or index."""
        if not self.page or not option_texts:
            return False
        try:
            success = await self.page.evaluate("""([qIdx, optTexts, qLabel]) => {
                const labelClean = (qLabel || '').toLowerCase().trim();
                const blocks = Array.from(document.querySelectorAll('div[role="listitem"]'));

                let targetBlock = null;
                if (labelClean) {
                    targetBlock = blocks.find(b => {
                        const heading = b.querySelector('div[role="heading"], .M7eMe, span');
                        return heading && heading.innerText.toLowerCase().includes(labelClean);
                    });
                }
                if (!targetBlock && qIdx < blocks.length) {
                    targetBlock = blocks[qIdx];
                }

                const searchRoot = targetBlock || document;
                const checkboxes = Array.from(searchRoot.querySelectorAll('div[role="checkbox"], label[role="checkbox"]'));
                let clickedCount = 0;

                for (const cb of checkboxes) {
                    const cbValue = (cb.getAttribute('data-answer-value') || cb.getAttribute('aria-label') || cb.innerText || '').toLowerCase().trim();
                    for (const opt of optTexts) {
                        const targetOpt = opt.toLowerCase().trim();
                        if (cbValue === targetOpt || cbValue.includes(targetOpt) || targetOpt.includes(cbValue)) {
                            if (cb.getAttribute('aria-checked') !== 'true') {
                                cb.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                cb.click();
                                cb.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                                cb.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            clickedCount++;
                            break;
                        }
                    }
                }
                return clickedCount > 0;
            }""", [question_index, option_texts, question_label])
            if success:
                logger.info(f"[Browser] ✅ Selected checkbox options {option_texts} for question '{question_label}'")
            return success
        except Exception as e:
            logger.error(f"Error selecting checkbox options: {e}")
            return False

    async def select_dropdown_option(self, question_index: int, option_text: str, question_label: str = "") -> bool:
        """Opens a dropdown and selects an option in a Google Form."""
        if not self.page or not option_text:
            return False
        try:
            opened = await self.page.evaluate("""([qIdx, qLabel]) => {
                const labelClean = (qLabel || '').toLowerCase().trim();
                const blocks = Array.from(document.querySelectorAll('div[role="listitem"]'));

                let targetBlock = null;
                if (labelClean) {
                    targetBlock = blocks.find(b => {
                        const heading = b.querySelector('div[role="heading"], .M7eMe, span');
                        return heading && heading.innerText.toLowerCase().includes(labelClean);
                    });
                }
                if (!targetBlock && qIdx < blocks.length) {
                    targetBlock = blocks[qIdx];
                }

                const searchRoot = targetBlock || document;
                const listbox = searchRoot.querySelector('div[role="listbox"]');
                if (listbox) {
                    listbox.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    listbox.click();
                    return true;
                }
                return false;
            }""", [question_index, question_label])

            if not opened:
                return False

            await asyncio.sleep(1.0)

            success = await self.page.evaluate("""(optText) => {
                const optClean = (optText || '').toLowerCase().trim();
                const options = Array.from(document.querySelectorAll('div[role="option"], div[data-value], span.vRMGwf'));
                for (const opt of options) {
                    const label = (opt.getAttribute('data-value') || opt.innerText || '').toLowerCase().trim();
                    if (label === optClean || label.includes(optClean) || optClean.includes(label)) {
                        opt.click();
                        return true;
                    }
                }
                return false;
            }""", option_text)

            if success:
                logger.info(f"[Browser] ✅ Selected dropdown option '{option_text}' for '{question_label}'")
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
