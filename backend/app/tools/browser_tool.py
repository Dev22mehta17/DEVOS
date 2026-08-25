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
        """Attempts connection to Chrome CDP port 9222, auto-spawning Chrome if needed."""
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
                logger.info(f"Chrome CDP not active on {CDP_URL} ({cdp_err}). Auto-launching Google Chrome...")

            # Attempt 2: Auto-spawn real Google Chrome on Mac with remote debugging port 9222
            try:
                import subprocess
                from pathlib import Path
                profile_dir = Path.home() / ".gemini" / "antigravity" / "chrome_devos_profile"
                profile_dir.mkdir(parents=True, exist_ok=True)

                chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                if os.path.exists(chrome_path):
                    subprocess.Popen([
                        chrome_path,
                        "--remote-debugging-port=9222",
                        f"--user-data-dir={str(profile_dir)}",
                        "--no-first-run",
                        "--no-default-browser-check"
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.sleep(2.0)

                    self.browser = await self.playwright.chromium.connect_over_cdp(CDP_URL)
                    contexts = self.browser.contexts
                    self.context = contexts[0] if contexts else await self.browser.new_context()
                    pages = self.context.pages
                    self.page = pages[0] if pages else await self.context.new_page()
                    self.is_connected = True
                    logger.info("✅ Auto-launched Google Chrome and attached via CDP.")
                    return True
            except Exception as spawn_err:
                logger.warning(f"Could not auto-spawn Google Chrome: {spawn_err}")

            # Attempt 3: Standalone Playwright Chromium with stealth flags
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
            # Bring Chrome window to front on Mac so user sees it
            try:
                import subprocess
                subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to activate'], capture_output=True, timeout=2)
            except Exception:
                pass

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

                // Universal Scanner for non-Google-Forms pages (Taleo, Greenhouse, Lever, Workday, Portals)
                if (results.length === 0) {
                    const allInputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), textarea, select'));
                    
                    allInputs.forEach((inp, idx) => {
                        const tag = inp.tagName.toLowerCase();
                        const type = inp.type ? inp.type.toLowerCase() : 'text';
                        
                        // Find associated label text
                        let labelText = '';
                        if (inp.id) {
                            const lbl = document.querySelector(`label[for="${inp.id}"]`);
                            if (lbl) labelText = lbl.innerText.trim();
                        }
                        if (!labelText) {
                            const parentLbl = inp.closest('label');
                            if (parentLbl) labelText = parentLbl.innerText.trim();
                        }
                        if (!labelText && inp.getAttribute('aria-label')) {
                            labelText = inp.getAttribute('aria-label').trim();
                        }
                        if (!labelText && inp.placeholder) {
                            labelText = inp.placeholder.trim();
                        }
                        if (!labelText && inp.name) {
                            labelText = inp.name.replace(/([A-Z])/g, ' $1').replace(/[-_]/g, ' ').trim();
                        }

                        // Determine field type
                        let fType = 'text';
                        let options = [];
                        let currVal = inp.value || '';

                        if (type === 'file') {
                            fType = 'file';
                        } else if (type === 'radio') {
                            fType = 'radio';
                            options = [inp.value || labelText];
                        } else if (type === 'checkbox') {
                            fType = 'checkbox';
                            options = [inp.value || labelText];
                        } else if (tag === 'select') {
                            fType = 'dropdown';
                            options = Array.from(inp.options).map(o => o.text.trim()).filter(t => t && t !== 'Select' && t !== '-- Select --');
                            currVal = inp.options[inp.selectedIndex]?.text || '';
                        } else if (tag === 'textarea') {
                            fType = 'text';
                        }

                        results.push({
                            id: inp.id || `input_${idx}`,
                            name: inp.name || '',
                            type: type,
                            tagName: tag,
                            placeholder: inp.placeholder || '',
                            labelText: (labelText || `Field ${idx + 1}`).split('\\n')[0].trim(),
                            value: currVal,
                            options: options,
                            required: inp.required || inp.getAttribute('aria-required') === 'true',
                            questionIndex: idx,
                            fieldType: fType
                        });
                    });
                }

                return results;
            }""")
            return inputs_data
        except Exception as e:
            logger.error(f"Error inspecting form inputs: {e}")
            return []

    async def fill_input_by_index_or_name(self, idx: int, name: str, val: str, label: str = "", question_index: int = None) -> bool:
        """Fills text input element directly in its question block by label matching, with index fallback."""
        if not self.page:
            return False
        try:
            success = await self.page.evaluate("""([idx, nameStr, valStr, labelStr, qIdx]) => {
                const cleanStr = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
                const targetLabel = cleanStr(labelStr);
                const labelWords = targetLabel.split(' ').filter(w => w.length > 2);

                let input = null;

                // Strategy 1: Find target question block by label text
                if (targetLabel) {
                    const blocks = Array.from(document.querySelectorAll('div[role="listitem"], .geS5n, .freebirdFormviewerViewNumberedItemContainer, fieldset'));
                    let bestBlock = null;
                    let bestScore = 0;

                    blocks.forEach((b) => {
                        const heading = b.querySelector('div[role="heading"], .M7eMe, legend, label, span');
                        if (!heading) return;
                        const hText = cleanStr(heading.innerText);
                        if (!hText) return;

                        let score = 0;
                        if (hText.includes(targetLabel) || targetLabel.includes(hText)) {
                            score = 100;
                        } else {
                            labelWords.forEach(w => {
                                if (hText.includes(w)) score += 10;
                            });
                        }

                        if (score > bestScore && score >= 20) {
                            bestScore = score;
                            bestBlock = b;
                        }
                    });

                    if (bestBlock) {
                        input = bestBlock.querySelector('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input[type="date"], textarea, input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])');
                    }
                }

                // Strategy 2: Find by question index if provided
                if (!input && qIdx !== null && qIdx !== undefined) {
                    const blocks = Array.from(document.querySelectorAll('div[role="listitem"], .geS5n, .freebirdFormviewerViewNumberedItemContainer, fieldset'));
                    if (qIdx < blocks.length) {
                        input = blocks[qIdx].querySelector('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], textarea, input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"])');
                    }
                }

                // Strategy 3: Find by name attribute
                if (!input && nameStr) {
                    input = document.querySelector(`input[name="${nameStr}"], textarea[name="${nameStr}"]`);
                }

                // Strategy 4: Fallback to global index
                if (!input && idx !== null && idx !== undefined) {
                    const all = Array.from(document.querySelectorAll('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input[type="url"], input[type="date"], textarea'));
                    input = all[idx];
                }

                if (input) {
                    input.scrollIntoView({ behavior: 'auto', block: 'center' });
                    input.focus();
                    input.value = valStr;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.blur();
                    return true;
                }
                return false;
            }""", [idx, name, str(val), label, question_index])
            return success
        except Exception as e:
            logger.error(f"Error filling input for label '{label}' (idx {idx}): {e}")
            return False

    async def select_radio_option(self, question_index: int, option_text: str, question_label: str = "") -> bool:
        """Clicks a radio button option in a Google Form or web portal by question label or index."""
        if not self.page or not option_text:
            return False
        try:
            success = await self.page.evaluate("""([qIdx, optText, qLabel]) => {
                const optClean = (optText || '').toLowerCase().trim();
                const cleanStr = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
                const targetLabel = cleanStr(qLabel);
                const labelWords = targetLabel.split(' ').filter(w => w.length > 2);

                const blocks = Array.from(document.querySelectorAll('div[role="listitem"], fieldset, .freebirdFormviewerViewNumberedItemContainer, .geS5n'));

                // Strategy 1: Find target question block by heading similarity
                let targetBlock = null;
                let bestScore = 0;

                blocks.forEach((b, idx) => {
                    const headingEl = b.querySelector('div[role="heading"], .M7eMe, legend, label, span');
                    if (!headingEl) return;
                    const hText = cleanStr(headingEl.innerText);
                    if (!hText) return;

                    let score = 0;
                    if (hText.includes(targetLabel) || targetLabel.includes(hText)) {
                        score = 100;
                    } else {
                        labelWords.forEach(w => {
                            if (hText.includes(w)) score += 10;
                        });
                    }

                    if (score > bestScore && score >= 20) {
                        bestScore = score;
                        targetBlock = b;
                    }
                });

                if (!targetBlock && qIdx < blocks.length) {
                    targetBlock = blocks[qIdx];
                }

                // Strategy 2: Search within targetBlock, then fallback to whole document
                const roots = targetBlock ? [targetBlock, document] : [document];

                for (const searchRoot of roots) {
                    const radios = Array.from(searchRoot.querySelectorAll('div[role="radio"], label[role="radio"], input[type="radio"], .docssharedWizToggleLabeledContainer'));

                    for (const el of radios) {
                        const radioInput = el.getAttribute('role') === 'radio' ? el : el.querySelector('div[role="radio"], input[type="radio"]') || el;
                        const rValue = (radioInput.getAttribute('data-value') || radioInput.value || '').toLowerCase().trim();
                        const rText = (el.innerText || '').toLowerCase().trim();
                        const rAria = (radioInput.getAttribute('aria-label') || '').toLowerCase().trim();

                        if (rValue === optClean || rText.includes(optClean) || rAria.includes(optClean) || optClean.includes(rValue)) {
                            radioInput.scrollIntoView({ behavior: 'auto', block: 'center' });

                            // Trigger click on radio and parent containers
                            radioInput.click();
                            el.click();

                            const span = el.querySelector('span');
                            if (span) span.click();

                            // Dispatch synthetic click & change events
                            radioInput.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }));
                            radioInput.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }));
                            radioInput.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                            radioInput.dispatchEvent(new Event('change', { bubbles: true }));

                            radioInput.setAttribute('aria-checked', 'true');
                            if (radioInput.tagName && radioInput.tagName.toLowerCase() === 'input') {
                                radioInput.checked = true;
                            }
                            return true;
                        }
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
                'div[role="button"][aria-label*="Add File"], '
                'div[role="button"]:has-text("Add file"), '
                'div[role="button"]:has-text("Add File"), '
                'span:has-text("Add file"), '
                'span:has-text("Add File")'
            )
            
            if not add_btn:
                logger.warning("[Upload] Could not find 'Add file' button")
                return False

            logger.info("[Upload] Found 'Add file' button, clicking...")
            await add_btn.scroll_into_view_if_needed()
            await add_btn.click()
            await asyncio.sleep(2.5)

            # Wait for picker iframe to appear
            picker_frame = None
            for _ in range(8):
                for frame in self.page.frames:
                    if "docs.google.com/picker" in frame.url or "picker" in frame.url or "google.com/picker" in frame.url:
                        picker_frame = frame
                        break
                if picker_frame:
                    break
                await asyncio.sleep(0.5)

            if not picker_frame:
                # Try finding iframe element directly
                iframe_el = await self.page.query_selector('iframe[src*="picker"], iframe[src*="docs.google.com"]')
                if iframe_el:
                    picker_frame = await iframe_el.content_frame()

            if picker_frame:
                logger.info(f"[Upload] Found Google Picker iframe: {picker_frame.url[:80]}...")
                
                # Try direct file input inside iframe first (instant & reliable)
                try:
                    file_input = await picker_frame.wait_for_selector('input[type="file"]', timeout=3000)
                    if file_input:
                        await file_input.set_input_files(file_path)
                        logger.info(f"[Upload] ✅ Staged file via picker iframe input[type=file]: {os.path.basename(file_path)}")
                        await asyncio.sleep(4.0)

                        # Click Upload button inside iframe if present
                        upload_btn = await picker_frame.query_selector('button:has-text("Upload"), div[role="button"]:has-text("Upload"), div[aria-label*="Upload"], .picker-action-button')
                        if upload_btn:
                            await upload_btn.click()
                            logger.info("[Upload] Clicked Upload confirmation button inside picker.")
                            await asyncio.sleep(4.0)
                        return True
                except Exception as frame_err:
                    logger.debug(f"[Upload] Direct iframe file input: {frame_err}")

                # Fallback: Find and click Browse button inside picker iframe
                browse_selectors = [
                    'button:has-text("Browse")',
                    'div[role="button"]:has-text("Browse")',
                    'span:has-text("Browse")',
                    '.picker-upload-button',
                ]
                browse_btn = None
                for sel in browse_selectors:
                    try:
                        browse_btn = await picker_frame.wait_for_selector(sel, timeout=2000)
                        if browse_btn:
                            break
                    except Exception:
                        continue

                if browse_btn:
                    try:
                        async with self.page.expect_file_chooser(timeout=8000) as fc_info:
                            await browse_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(file_path)
                        logger.info(f"[Upload] ✅ File selected via Browse chooser: {os.path.basename(file_path)}")
                        await asyncio.sleep(3.0)

                        # Wait for upload to complete and click confirmation button
                        upload_selectors = [
                            'button:has-text("Upload")',
                            'div[role="button"]:has-text("Upload")',
                            'div[aria-label*="Upload"]',
                            'button:has-text("Insert")',
                            'div[role="button"]:has-text("Insert")',
                            'button:has-text("Select")',
                            '.picker-action-button',
                            '#picker\\:ap\\:2'
                        ]
                        for sel in upload_selectors:
                            try:
                                btn = await picker_frame.query_selector(sel)
                                if btn:
                                    await btn.click()
                                    logger.info(f"[Upload] Clicked confirmation button: {sel}")
                                    await asyncio.sleep(3.0)
                                    break
                            except Exception:
                                pass

                        await asyncio.sleep(2.0)
                        return True
                    except Exception as e:
                        logger.warning(f"[Upload] Browse click chooser error: {e}")

            # Fallback Method 3: Page-level file chooser directly on Add File button
            try:
                async with self.page.expect_file_chooser(timeout=5000) as fc_info:
                    await add_btn.click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(file_path)
                logger.info("[Upload] ✅ Uploaded via page file chooser")
                await asyncio.sleep(4.0)

                # Click confirmation button if visible on page
                upload_submit = await self.page.query_selector('button:has-text("Upload"), div[role="button"]:has-text("Upload"), span:has-text("Upload")')
                if upload_submit:
                    await upload_submit.click()
                    await asyncio.sleep(3.0)
                return True
            except Exception:
                pass

            return False

        except Exception as e:
            logger.error(f"[Upload] Fatal error: {e}")
            return False

    async def extract_search_summary(self) -> Dict[str, Any]:
        """Scrapes AI Overview, featured answer snippet, key facts, and top organic results from Google Search."""
        if not self.page:
            return {"direct_answer": "", "key_facts": [], "sources": []}
        try:
            # Wait for dynamic AI Overview / results widgets
            await asyncio.sleep(2.5)

            extracted = await self.page.evaluate("""() => {
                let answer = "";
                const keyFacts = [];
                const sources = [];

                // 1. Extract from AI Overview / Featured Snippet container
                const fullText = document.body.innerText;
                const aiIdx = fullText.indexOf("AI Overview");
                
                if (aiIdx !== -1) {
                    const afterAi = fullText.substring(aiIdx + "AI Overview".length).trim();
                    const lines = afterAi.split("\\n").map(l => l.trim()).filter(l => l && !l.includes("हिन्दी") && !l.includes("Feedback") && !l.includes("Listen") && !l.includes("Share"));
                    
                    if (lines.length > 0) {
                        answer = lines[0];
                    }
                    
                    // Look for Key Facts section
                    const kfIdx = afterAi.indexOf("Key Facts");
                    if (kfIdx !== -1) {
                        const kfLines = afterAi.substring(kfIdx + "Key Facts".length).split("\\n").map(l => l.trim()).filter(l => l);
                        for (const kl of kfLines) {
                            if (kl.includes(":") && (kl.startsWith("Role:") || kl.startsWith("Term") || kl.startsWith("Official") || kl.startsWith("Born") || kl.startsWith("President") || kl.startsWith("Capital") || kl.startsWith("Population") || kl.startsWith("Founded") || kl.startsWith("CEO") || kl.startsWith("Founder") || kl.startsWith("Headquarters") || kl.startsWith("Spouse") || kl.startsWith("Height") || kl.startsWith("Net worth") || kl.startsWith("Age"))) {
                                keyFacts.push(kl);
                            } else if (kl.includes("sites") || kl.includes("Wikipedia") || kl.length > 120) {
                                break;
                            }
                        }
                    }
                }

                // 2. Fallback: Knowledge Panel description or featured snippet
                if (!answer) {
                    const descEl = document.querySelector('div[data-attrid="description"], .kno-rdesc, .hgKElc, .V3FYCf, div[jsname="x3hk2d"]');
                    if (descEl && descEl.innerText.trim()) {
                        answer = descEl.innerText.trim();
                    }
                }

                // 3. Extract top organic result links
                const anchors = Array.from(document.querySelectorAll("a"));
                const seenUrls = new Set();

                for (const a of anchors) {
                    const href = a.href || "";
                    if (!href.startsWith("http") || href.includes("google.com") || href.includes("youtube.com/search") || href.includes("accounts.google")) continue;
                    
                    const titleEl = a.querySelector("h3") || (a.innerText.length > 10 && a.innerText.length < 80 ? a : null);
                    if (titleEl && !seenUrls.has(href)) {
                        seenUrls.add(href);
                        const container = a.closest("div.g, div[data-sokoban-container], div.MjjYud, div") || a.parentElement;
                        const snippetEl = container ? container.querySelector("div[style*='-webkit-line-clamp'], div.VwiC3b, span.aCOpRe, div.yXK7lf") : null;
                        
                        let domain = "";
                        try { domain = new URL(href).hostname.replace("www.", ""); } catch(e){}

                        sources.push({
                            title: titleEl.innerText.trim().split("\\n")[0],
                            url: href,
                            source: domain,
                            snippet: snippetEl ? snippetEl.innerText.trim() : ""
                        });
                        if (sources.length >= 4) break;
                    }
                }

                return {
                    direct_answer: answer,
                    key_facts: keyFacts,
                    sources: sources
                };
            }""")
            return extracted or {"direct_answer": "", "key_facts": [], "sources": []}
        except Exception as e:
            logger.error(f"[BrowserTool] Error extracting search summary: {e}")
            return {"direct_answer": "", "key_facts": [], "sources": []}

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
