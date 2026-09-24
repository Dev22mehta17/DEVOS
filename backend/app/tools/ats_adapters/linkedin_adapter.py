import os
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.tools.browser_tool import browser_tool
from app.tools.file_tool import file_tool
from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine

logger = logging.getLogger(__name__)


class LinkedInEasyApplyAdapter:
    """Semi-autonomous assistant for LinkedIn Easy Apply job applications."""

    @staticmethod
    async def apply_to_job(job_url: str, goal_description: str = "", email_override: Optional[str] = None) -> Dict[str, Any]:
        action_id = f"linkedin_{uuid.uuid4().hex[:8]}"
        # Normalize search-results or collection URLs to clean direct view URL
        import re
        job_id_match = re.search(r'currentJobId=(\d+)', job_url) or re.search(r'/jobs/view/(\d+)', job_url)
        job_id = job_id_match.group(1) if job_id_match else None
        target_url = job_url
        if job_id and "search-results" in job_url:
            target_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            logger.info(f"[LinkedInAdapter] Normalized search URL to direct view: {target_url}")

        logger.info(f"[LinkedInAdapter] Opening LinkedIn job: {target_url}")
        nav_res = await browser_tool.navigate(target_url)
        await asyncio.sleep(4.0)

        page = await browser_tool.get_active_page()
        if not page:
            return {"status": "ERROR", "message": "Browser page unavailable"}

        # Scroll to ensure the job details load fully
        await page.evaluate("window.scrollTo(0, 300)")
        await asyncio.sleep(1.5)

        page_title = await page.title()

        # Step 1: Detect Easy Apply Button — checking both <button> and <a> elements
        EASY_APPLY_SELECTORS = [
            'a[href*="/apply/"]',
            'button.jobs-apply-button',
            'button.jobs-apply-button--top-card',
            'div.jobs-apply-button--top-card button',
            'div.jobs-apply-button--top-card a',
            'a[aria-label*="Easy Apply"]',
            'button[aria-label*="Easy Apply"]',
            'a[aria-label*="easy apply"]',
            'button[aria-label*="easy apply"]',
            '.jobs-s-apply button',
            '.jobs-s-apply a',
            '.jobs-apply-button--top-card',
            'button:has-text("Easy Apply")',
            'a:has-text("Easy Apply")',
        ]

        easy_apply_btn = None
        for attempt in range(3):
            for selector in EASY_APPLY_SELECTORS:
                try:
                    btn = await page.query_selector(selector)
                    if btn and await btn.is_visible():
                        easy_apply_btn = btn
                        logger.info(f"[LinkedInAdapter] Found Easy Apply element with selector: {selector}")
                        break
                except Exception:
                    continue
            if easy_apply_btn:
                break
            # If not found, wait and scroll
            logger.debug(f"[LinkedInAdapter] Easy Apply element not found on attempt {attempt+1}, retrying...")
            await asyncio.sleep(2.0)

        # Fallback: search all clickable elements for Easy Apply text or aria-label
        if not easy_apply_btn:
            try:
                trigger_info = await page.evaluate(r"""() => {
                    const clickable = Array.from(document.querySelectorAll('a, button, div[role="button"]'));
                    const match = clickable.find(el => {
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        const txt = (el.innerText || '').trim().toLowerCase();
                        const href = (el.getAttribute('href') || '').toLowerCase();
                        return aria.includes('easy apply') || txt === 'easy apply' || (txt.includes('easy apply') && el.tagName === 'BUTTON') || href.includes('/apply/');
                    });
                    if (match) {
                        return { tag: match.tagName, href: match.href || '', aria: match.getAttribute('aria-label') || '' };
                    }
                    return null;
                }""")
                if trigger_info:
                    logger.info(f"[LinkedInAdapter] Detected Easy Apply trigger via JS fallback: {trigger_info}")
                    if trigger_info.get("href") and "/apply/" in trigger_info["href"]:
                        logger.info(f"[LinkedInAdapter] Navigating directly to apply flow URL: {trigger_info['href']}")
                        await page.goto(trigger_info["href"], wait_until="domcontentloaded")
                        await asyncio.sleep(3.5)
                        easy_apply_btn = "NAVIGATED"
                    else:
                        easy_apply_btn = await page.query_selector('a[aria-label*="Easy Apply"], button[aria-label*="Easy Apply"], a:has-text("Easy Apply"), button:has-text("Easy Apply")')
            except Exception as e:
                logger.debug(f"[LinkedInAdapter] JS fallback error: {e}")

        # If still not found but we have a valid jobId, attempt direct SDUI apply flow navigation
        if not easy_apply_btn and job_id:
            sdui_url = f"https://www.linkedin.com/jobs/view/{job_id}/apply/?openSDUIApplyFlow=true"
            logger.info(f"[LinkedInAdapter] Attempting direct SDUI apply flow navigation: {sdui_url}")
            try:
                await page.goto(sdui_url, wait_until="domcontentloaded")
                await asyncio.sleep(3.5)
                # Verify if modal or application inputs appeared
                has_modal = await page.evaluate("() => document.querySelectorAll('input, select, .jobs-easy-apply-modal, button[aria-label*=\"Continue\"]').length > 0")
                if has_modal:
                    logger.info("[LinkedInAdapter] ✅ Direct SDUI apply flow opened successfully!")
                    easy_apply_btn = "NAVIGATED"
            except Exception as sdui_err:
                logger.warning(f"[LinkedInAdapter] SDUI navigation failed: {sdui_err}")

        if not easy_apply_btn:
            logger.warning("[LinkedInAdapter] No 'Easy Apply' button found on this job post after exhaustive search.")
            return {
                "status": "NOT_EASY_APPLY",
                "message": "This job does not have LinkedIn Easy Apply (it may redirect to an external company website).",
                "page_title": page_title
            }

        # Step 2: Open Easy Apply flow
        if easy_apply_btn and easy_apply_btn != "NAVIGATED":
            logger.info("[LinkedInAdapter] Clicking Easy Apply button...")
            try:
                href = await easy_apply_btn.get_attribute("href")
                if href and "/apply/" in href:
                    logger.info(f"[LinkedInAdapter] Direct apply href detected: {href}, navigating...")
                    await page.goto(href, wait_until="domcontentloaded")
                    await asyncio.sleep(3.5)
                else:
                    await easy_apply_btn.click()
                    await asyncio.sleep(2.5)
            except Exception as click_err:
                logger.warning(f"[LinkedInAdapter] Standard click failed: {click_err}. Retrying via evaluate...")
                await page.evaluate("""() => {
                    const el = document.querySelector('button.jobs-apply-button, a[aria-label*="Easy Apply"], button[aria-label*="Easy Apply"], a[href*="/apply/"]');
                    if (el) el.click();
                }""")
                await asyncio.sleep(2.5)

        # Step 3: Candidate Data from Memory
        if not email_override and goal_description:
            import re
            em_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', goal_description)
            if em_match:
                email_override = em_match.group(0).strip()

        p = memory_engine.profile_data
        personal = p.get("personal", {})
        chosen_email = email_override or memory_engine.get_field_value("email") or personal.get("email_primary", "mehtadev2004@gmail.com")
        phone = personal.get("phone", "7206049507")
        clean_phone = phone.replace("+91-", "").replace("+91", "").replace(" ", "").replace("-", "")

        best_resume = p.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()
        available_resumes = [r["path"] for r in file_tool.find_resume_files()]

        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []

        # Step 4: Step through Easy Apply Wizard (up to 5 steps max)
        max_steps = 6
        current_step = 0
        reached_review = False

        while current_step < max_steps and not reached_review:
            current_step += 1
            await asyncio.sleep(1.5)

            # Check if we are on the final Review step
            submit_btn = await page.query_selector(
                'button[aria-label*="Submit application"], button:has-text("Submit application")'
            )
            review_header = await page.query_selector('h3:has-text("Review your application"), .jobs-easy-apply-modal__content:has-text("Review")')

            if submit_btn or review_header:
                logger.info("[LinkedInAdapter] ✅ Reached final review screen before submission!")
                reached_review = True
                break

            # Fill or select Email address if visible on Contact info step
            try:
                email_select = await page.query_selector('select[id*="email"], select[name*="email"], select[aria-label*="Email" i]')
                if email_select and await email_select.is_visible():
                    await page.evaluate("""({sel, targetEmail}) => {
                        const opts = Array.from(sel.options);
                        const match = opts.find(o => o.text.toLowerCase().includes(targetEmail.toLowerCase()) || o.value.toLowerCase().includes(targetEmail.toLowerCase()));
                        if (match) {
                            sel.value = match.value;
                            sel.dispatchEvent(new Event('change', {bubbles: true}));
                            sel.dispatchEvent(new Event('input', {bubbles: true}));
                        }
                    }""", {"sel": email_select, "targetEmail": chosen_email})
                    filled_fields.append({
                        "field_label": "Email Address",
                        "value": chosen_email,
                        "fieldType": "dropdown",
                        "is_auto_matched": True
                    })
                else:
                    email_input = await page.query_selector('input[type="email"], input[id*="email"], input[name*="email"], input[aria-label*="Email" i]')
                    if email_input and await email_input.is_visible():
                        await email_input.fill(chosen_email)
                        filled_fields.append({
                            "field_label": "Email Address",
                            "value": chosen_email,
                            "fieldType": "text",
                            "is_auto_matched": True
                        })
            except Exception as e_err:
                logger.debug(f"[LinkedInAdapter] Email fill ignored: {e_err}")

            # Fill phone number if visible
            try:
                phone_input = await page.query_selector(
                    'input[id*="phoneNumber"], input[id*="phone-number"], input[name*="phone"], input[aria-label*="Phone" i]'
                )
                if phone_input and await phone_input.is_visible():
                    current_val = await phone_input.input_value()
                    if not current_val or len(current_val) < 5:
                        await phone_input.fill(clean_phone)
                        filled_fields.append({
                            "field_label": "Phone Number",
                            "value": clean_phone,
                            "fieldType": "text",
                            "is_auto_matched": True
                        })
                    else:
                        filled_fields.append({
                            "field_label": "Phone Number",
                            "value": current_val,
                            "fieldType": "text",
                            "is_auto_matched": True
                        })
            except Exception as e:
                logger.debug(f"[LinkedInAdapter] Phone fill ignored: {e}")

            # Check if resume is already attached or upload needed on resume step
            try:
                resume_card = await page.query_selector('.jobs-document-upload__title, div:has-text("Resume"), label:has-text("Resume")')
                if resume_card and await resume_card.is_visible():
                    if best_resume and not any(f.get("field_label") == "Resume / CV" for f in filled_fields):
                        filled_fields.append({
                            "field_label": "Resume / CV",
                            "value": f"[ATTACHED] {best_resume}",
                            "fieldType": "file",
                            "is_auto_matched": True
                        })
            except Exception as res_err:
                logger.debug(f"[LinkedInAdapter] Resume check ignored: {res_err}")

            # ─── 1. Radio questions (Work Authorization / Degree / Relocation) ───
            try:
                fieldsets = await page.query_selector_all('fieldset')
                for fs in fieldsets:
                    if not await fs.is_visible():
                        continue
                    legend = await page.evaluate("""(el) => {
                        const leg = el.querySelector('legend, span.fb-form-element-label, span[aria-hidden="true"]');
                        return leg ? leg.innerText.trim() : '';
                    }""", fs)
                    if not legend:
                        continue
                    leg_clean = re.sub(r'\s*\*+\s*$', '', legend).strip()
                    leg_lower = leg_clean.lower()

                    target_choice = "yes"
                    if any(k in leg_lower for k in ["sponsorship", "visa", "require sponsorship", "criminal", "drug test", "restriction"]):
                        target_choice = "no"
                    elif any(k in leg_lower for k in ["authorized to work", "legally authorized", "bachelor", "degree", "graduat",
                                                     "willing to relocate", "commute", "comfortable", "available", "full-time"]):
                        target_choice = "yes"

                    # Select target radio — click label and update input
                    await page.evaluate("""({fs, target}) => {
                        const labels = Array.from(fs.querySelectorAll('label'));
                        for (let l of labels) {
                            if (l.innerText && l.innerText.trim().toLowerCase() === target) {
                                const inp = l.querySelector('input[type="radio"]') || document.getElementById(l.getAttribute('for'));
                                if (inp) {
                                    inp.checked = true;
                                    inp.dispatchEvent(new Event('change', {bubbles: true}));
                                    inp.dispatchEvent(new Event('input', {bubbles: true}));
                                }
                                l.click();
                                break;
                            }
                        }
                    }""", {"fs": fs, "target": target_choice})
                    filled_fields.append({
                        "field_label": leg_clean,
                        "value": target_choice.capitalize(),
                        "fieldType": "radio",
                        "is_auto_matched": True
                    })
            except Exception as r_err:
                logger.debug(f"[LinkedInAdapter] Radio answer ignored: {r_err}")

            # ─── 2. Dropdown Selects (Screening Questions, Availability, Language) ───
            try:
                selects = await page.query_selector_all('select')
                for sel in selects:
                    if not await sel.is_visible():
                        continue
                    sel_data = await page.evaluate("""(el) => {
                        let label = '';
                        const formGroup = el.closest('.fb-form-element, .jobs-easy-apply-form-element, .jobs-easy-apply-form-section__grouping, div[data-test-form-element]');
                        if (formGroup) {
                            const lbl = formGroup.querySelector('label, span.fb-form-element-label, span[aria-hidden="true"], .t-14');
                            if (lbl) label = lbl.innerText.trim();
                        }
                        if (!label && el.id) {
                            const lbl = document.querySelector(`label[for="${el.id}"]`);
                            if (lbl) label = lbl.innerText.trim();
                        }
                        if (!label) {
                            label = el.getAttribute('aria-label') || el.name || '';
                        }
                        label = label.replace(/\\s*\\*+\\s*$/, '').trim();
                        const opts = Array.from(el.options).map(o => o.text.trim()).filter(Boolean);
                        const currText = el.options[el.selectedIndex] ? el.options[el.selectedIndex].text.trim() : '';
                        return { id: el.id, name: el.name, label: label, options: opts, currentText: currText };
                    }""", sel)

                    q_label = sel_data.get("label", "")
                    q_opts = sel_data.get("options", [])
                    curr_text = sel_data.get("currentText", "")

                    if not q_opts or (len(q_opts) == 1 and q_opts[0].lower().startswith("select")):
                        continue

                    # If already selected a valid answer, record it
                    if curr_text and curr_text.lower() not in ["select an option", "select", "choose", "--", ""]:
                        filled_fields.append({
                            "field_label": q_label or "Dropdown Question",
                            "value": curr_text,
                            "fieldType": "dropdown",
                            "is_auto_matched": True
                        })
                        continue

                    chosen = None
                    # Country code / phone country
                    if any(k in q_label.lower() for k in ["country", "phone country"]):
                        india_opt = next((o for o in q_opts if "india" in o.lower() or "+91" in o), None)
                        if india_opt:
                            chosen = india_opt
                    elif any(k in q_label.lower() for k in ["city", "location"]):
                        city_match = next((o for o in q_opts if any(c in o.lower() for c in ["chandigarh", "delhi", "ncr", "gurgaon", "noida"])), None)
                        if city_match:
                            chosen = city_match

                    # Intelligent memory option matching
                    if not chosen:
                        match = memory_engine.match_option(q_label, q_opts)
                        if match:
                            chosen = match["matched_option"]

                    # Yes / No fallback for screening dropdowns (e.g., commit to internship, hands-on experience, fast-paced)
                    if not chosen:
                        has_yes = any(o.lower().strip() == "yes" or o.lower().strip().startswith("yes") for o in q_opts)
                        has_no = any(o.lower().strip() == "no" or o.lower().strip().startswith("no") for o in q_opts)
                        if has_yes and has_no:
                            if any(k in q_label.lower() for k in ["criminal", "sponsorship", "visa", "restriction", "felony", "drug test"]):
                                chosen = next((o for o in q_opts if o.lower().strip() == "no" or o.lower().strip().startswith("no")), "No")
                            else:
                                chosen = next((o for o in q_opts if o.lower().strip() == "yes" or o.lower().strip().startswith("yes")), "Yes")

                    if chosen:
                        await page.evaluate("""({id, name, chosen}) => {
                            let sel = null;
                            if (id) sel = document.getElementById(id);
                            if (!sel && name) sel = document.querySelector(`select[name="${name}"]`);
                            if (sel) {
                                for (let opt of sel.options) {
                                    if (opt.text.trim().toLowerCase() === chosen.toLowerCase() || opt.value.toLowerCase() === chosen.toLowerCase()) {
                                        sel.value = opt.value;
                                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                                        sel.dispatchEvent(new Event('input', { bubbles: true }));
                                        break;
                                    }
                                }
                            }
                        }""", {"id": sel_data.get("id"), "name": sel_data.get("name"), "chosen": chosen})

                        filled_fields.append({
                            "field_label": q_label or "Screening Question",
                            "value": chosen,
                            "fieldType": "dropdown",
                            "is_auto_matched": True
                        })
                    else:
                        flagged_fields.append({
                            "field_label": q_label or "Screening Question",
                            "reason": "Please choose an option",
                            "options": q_opts,
                            "fieldType": "dropdown"
                        })
            except Exception as s_err:
                logger.debug(f"[LinkedInAdapter] Select/dropdown fill ignored: {s_err}")

            # ─── 3. Numeric & Text Screening Inputs (Years of experience, CGPA, URLs) ───
            try:
                inputs = await page.query_selector_all('input[type="text"]:not([id*="phoneNumber"]):not([id*="email"]), input[type="number"]')
                for inp in inputs:
                    if not await inp.is_visible():
                        continue
                    lbl_el = await page.evaluate("""(el) => {
                        const formGroup = el.closest('.fb-form-element, .jobs-easy-apply-form-element, .jobs-easy-apply-form-section__grouping, div');
                        const label = formGroup ? formGroup.querySelector('label, span.fb-form-element-label, span') : null;
                        return label ? label.innerText.trim() : '';
                    }""", inp)
                    lbl_clean = re.sub(r'\s*\*+\s*$', '', lbl_el).strip()
                    lbl_lower = lbl_clean.lower()
                    if not lbl_clean:
                        continue

                    curr_val = await inp.input_value()
                    if curr_val and len(curr_val.strip()) > 0:
                        continue  # Already filled

                    ans_val = None
                    if any(k in lbl_lower for k in ["years of experience", "total experience", "how many years"]):
                        ans_val = "1"
                        if any(k in lbl_lower for k in ["python", "c++", "java", "dsa", "backend", "software"]):
                            ans_val = "2"
                    elif any(k in lbl_lower for k in ["gpa", "cgpa"]):
                        ans_val = "8.7"
                    elif "percentage" in lbl_lower:
                        ans_val = "93.6"
                    else:
                        ans_val = memory_engine.get_field_value(lbl_clean)

                    if ans_val:
                        await inp.fill(str(ans_val))
                        filled_fields.append({
                            "field_label": lbl_clean,
                            "value": str(ans_val),
                            "fieldType": "text",
                            "is_auto_matched": True
                        })
            except Exception as q_err:
                logger.debug(f"[LinkedInAdapter] Screening input fill ignored: {q_err}")

            await asyncio.sleep(1.0)

            # Click "Next" or "Review" button to proceed to next step
            next_btn = await page.query_selector(
                'button[aria-label*="Continue to next step"], button:has-text("Next"), button[aria-label*="Review your application"], button:has-text("Review")'
            )
            if next_btn and await next_btn.is_visible():
                logger.info(f"[LinkedInAdapter] Clicking next step ({current_step})...")
                await next_btn.click()
                await asyncio.sleep(2.0)
            else:
                break

        # Step 5: Stage Final HITL Review Boundary (Never auto-submits without explicit user click)
        review_payload = {
            "action_id": action_id,
            "form_url": job_url,
            "portal_kind": "linkedin_easy_apply",
            "page_title": page_title,
            "goal_description": f"LinkedIn Easy Apply for '{page_title}'",
            "filled_fields": filled_fields,
            "flagged_fields": flagged_fields,
            "uploaded_resume": best_resume,
            "available_resumes": available_resumes,
            "status_note": "Application stepped through to final review screen on LinkedIn."
        }

        perm_check = permission_engine.check_action(
            action_id=action_id,
            action_type="submit_form",
            payload=review_payload
        )

        return {
            "status": "FORM_REVIEW_READY",
            "action_id": action_id,
            "payload": review_payload,
            "permission": perm_check
        }


linkedin_adapter = LinkedInEasyApplyAdapter()
