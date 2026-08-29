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
    async def apply_to_job(job_url: str, goal_description: str = "") -> Dict[str, Any]:
        action_id = f"linkedin_{uuid.uuid4().hex[:8]}"
        logger.info(f"[LinkedInAdapter] Opening LinkedIn job: {job_url}")

        nav_res = await browser_tool.navigate(job_url)
        await asyncio.sleep(3.0)

        page = await browser_tool.get_active_page()
        if not page:
            return {"status": "ERROR", "message": "Browser page unavailable"}

        page_title = await page.title()

        # Step 1: Detect Easy Apply Button
        easy_apply_btn = await page.query_selector(
            'button.jobs-apply-button, button[aria-label*="Easy Apply"], button:has-text("Easy Apply")'
        )

        if not easy_apply_btn:
            logger.warning("[LinkedInAdapter] No 'Easy Apply' button found on this job post.")
            return {
                "status": "NOT_EASY_APPLY",
                "message": "This job does not have LinkedIn Easy Apply (it may redirect to an external company website).",
                "page_title": page_title
            }

        # Step 2: Click Easy Apply to open modal
        logger.info("[LinkedInAdapter] Clicking Easy Apply button...")
        await easy_apply_btn.click()
        await asyncio.sleep(2.0)

        # Step 3: Candidate Data from Memory
        p = memory_engine.profile_data
        personal = p.get("personal", {})
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

            # Fill phone number if visible
            try:
                phone_input = await page.query_selector(
                    'input[id*="phoneNumber"], input[id*="phone-number"], input[name*="phone"], input[aria-label*="Phone"]'
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
            except Exception as e:
                logger.debug(f"[LinkedInAdapter] Phone fill ignored: {e}")

            # Answer standard screening questions (Numeric inputs, Yes/No radios)
            try:
                # 1. Numeric inputs (Years of experience)
                num_inputs = await page.query_selector_all('input[type="text"][id*="numeric"], input[type="number"], .fb-single-line-text input')
                for inp in num_inputs:
                    if not await inp.is_visible():
                        continue
                    lbl_el = await page.evaluate("""(el) => {
                        const formGroup = el.closest('.fb-form-element, .jobs-easy-apply-form-element, div');
                        const label = formGroup ? formGroup.querySelector('label, span') : null;
                        return label ? label.innerText.trim() : '';
                    }""", inp)
                    
                    lbl_lower = (lbl_el or "").lower()
                    ans_val = "1"  # Default 1 year experience (Amazon internship + projects)
                    if any(k in lbl_lower for k in ["python", "c++", "java", "dsa", "backend", "software"]):
                        ans_val = "2"
                    elif any(k in lbl_lower for k in ["gpa", "cgpa"]):
                        ans_val = "8.7"
                    elif "percentage" in lbl_lower:
                        ans_val = "93.6"

                    await inp.fill(ans_val)
                    filled_fields.append({
                        "field_label": lbl_el or "Screening Question",
                        "value": ans_val,
                        "fieldType": "text",
                        "is_auto_matched": True
                    })
            except Exception as q_err:
                logger.debug(f"[LinkedInAdapter] Screening question fill ignored: {q_err}")

            # 2. Radio questions (Work Authorization / Sponsorship)
            try:
                radios = await page.query_selector_all('fieldset')
                for fs in radios:
                    legend = await page.evaluate("""(el) => {
                        const leg = el.querySelector('legend, span.fb-form-element-label');
                        return leg ? leg.innerText.trim().toLowerCase() : '';
                    }""", fs)
                    
                    target_choice = "yes"
                    if any(k in legend for k in ["sponsorship", "visa", "require sponsorship", "criminal"]):
                        target_choice = "no"
                    elif any(k in legend for k in ["authorized to work", "legally authorized", "bachelor", "degree", "graduat"]):
                        target_choice = "yes"

                    # Select target radio
                    await page.evaluate("""({fs, target}) => {
                        const labels = Array.from(fs.querySelectorAll('label, input[type="radio"]'));
                        for (let l of labels) {
                            if (l.innerText && l.innerText.trim().toLowerCase() === target) {
                                l.click();
                                break;
                            }
                        }
                    }""", {"fs": fs, "target": target_choice})
            except Exception as r_err:
                logger.debug(f"[LinkedInAdapter] Radio answer ignored: {r_err}")

            # Click "Next" or "Review" button to proceed to next step
            next_btn = await page.query_selector(
                'button[aria-label*="Continue to next step"], button:has-text("Next"), button[aria-label*="Review your application"], button:has-text("Review")'
            )
            if next_btn and await next_btn.is_visible():
                logger.info(f"[LinkedInAdapter] Clicking next step ({current_step})...")
                await next_btn.click()
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
