import os
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.tools.browser_tool import browser_tool
from app.tools.file_tool import file_tool
from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine
from app.core.answer_generator import answer_generator

logger = logging.getLogger(__name__)


class LeverAdapter:
    """Specialized automation adapter for Lever ATS (jobs.lever.co)."""

    @staticmethod
    async def fill_application(url: str, goal_description: str = "") -> Dict[str, Any]:
        action_id = f"lever_{uuid.uuid4().hex[:8]}"
        logger.info(f"[LeverAdapter] Opening Lever job post: {url}")

        nav_res = await browser_tool.navigate(url)
        await asyncio.sleep(2.5)

        page = await browser_tool.get_active_page()
        if not page:
            return {"status": "ERROR", "message": "Browser page unavailable"}

        page_title = await page.title()

        # Step 1: Auto-click "Apply for this job" / "Apply now" button if on job overview
        try:
            apply_btn = await page.query_selector(
                'a.postings-btn, a[href*="/apply"], button.template-btn-submit, a:has-text("Apply")'
            )
            if apply_btn:
                logger.info("[LeverAdapter] Clicking 'Apply for this job' button...")
                await apply_btn.click()
                await asyncio.sleep(2.0)
        except Exception as e:
            logger.debug(f"[LeverAdapter] Apply button click ignored: {e}")

        # Step 2: Extract Candidate Data from Memory
        p = memory_engine.profile_data
        personal = p.get("personal", {})
        full_name = personal.get("full_name", "Dev Mehta")
        email = personal.get("email_primary", "mehtadev2004@gmail.com")
        phone = personal.get("phone", "+91-7206049507")
        current_company = p.get("professional", {}).get("current_company", "Amazon Pay India")
        links = p.get("links", {})
        linkedin_url = links.get("linkedin", "")
        github_url = links.get("github", "")
        portfolio_url = links.get("portfolio", "")

        best_resume = p.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()
        available_resumes = [r["path"] for r in file_tool.find_resume_files()]
        if best_resume and best_resume not in available_resumes:
            available_resumes.insert(0, best_resume)

        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []

        # Step 3: Fill Standard Lever Input Fields
        lever_inputs = [
            ('input[name="name"]', full_name, "Full Name"),
            ('input[name="email"]', email, "Email"),
            ('input[name="phone"]', phone, "Phone Number"),
            ('input[name="org"]', current_company, "Current Company / Org"),
            ('input[name="urls[LinkedIn]"], input[placeholder*="LinkedIn"]', linkedin_url, "LinkedIn URL"),
            ('input[name="urls[GitHub]"], input[placeholder*="GitHub"]', github_url, "GitHub URL"),
            ('input[name="urls[Portfolio]"], input[name="urls[Other]"], input[placeholder*="Portfolio"], input[placeholder*="Website"]', portfolio_url, "Portfolio URL"),
        ]

        for sel, val, label in lever_inputs:
            if not val:
                continue
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.fill(val)
                    filled_fields.append({
                        "field_label": label,
                        "field_id": sel,
                        "value": val,
                        "fieldType": "text",
                        "is_auto_matched": True
                    })
            except Exception as e:
                logger.debug(f"[LeverAdapter] Error filling {label}: {e}")

        # Step 4: Attach Resume File
        if best_resume and os.path.exists(best_resume):
            try:
                file_input = await page.query_selector('input#resume-upload-input, input[type="file"]')
                if file_input:
                    await file_input.set_input_files(best_resume)
                    filled_fields.append({
                        "field_label": "Resume / CV",
                        "field_id": "resume_upload",
                        "value": f"[ATTACHED FILE] {best_resume}",
                        "is_file": True,
                        "file_path": best_resume,
                        "fieldType": "file"
                    })
                    logger.info(f"[LeverAdapter] ✅ Attached resume: {best_resume}")
            except Exception as f_err:
                logger.warning(f"[LeverAdapter] Resume attach error: {f_err}")
                flagged_fields.append({
                    "field_label": "Resume Upload",
                    "field_id": "resume_upload",
                    "reason": "Please upload resume.",
                    "is_file": True,
                    "fieldType": "file"
                })
        else:
            flagged_fields.append({
                "field_label": "Resume Upload",
                "field_id": "resume_upload",
                "reason": "No local resume found.",
                "is_file": True,
                "fieldType": "file"
            })

        # Step 5: Handle Additional Comments / Custom Textareas
        try:
            custom_areas = await page.query_selector_all('textarea')
            for ta in custom_areas:
                name_attr = await ta.get_attribute("name") or "comments"
                aria_label = await ta.get_attribute("aria-label") or name_attr
                gen_res = answer_generator.generate_answer(aria_label, f"{page_title} {url} {goal_description}")
                ans_text = gen_res.get("answer", "")
                if ans_text:
                    await ta.fill(ans_text[:500])
                    filled_fields.append({
                        "field_label": aria_label,
                        "field_id": name_attr,
                        "value": ans_text[:500],
                        "is_ai_generated": True,
                        "ai_source": gen_res.get("source"),
                        "fieldType": "text"
                    })
        except Exception as ta_err:
            logger.debug(f"[LeverAdapter] Textarea processing ignored: {ta_err}")

        # Step 6: Prepare Review Payload & Stage HITL Permission
        review_payload = {
            "action_id": action_id,
            "form_url": url,
            "portal_kind": "lever",
            "page_title": page_title,
            "goal_description": goal_description or f"Lever Job Application for {page_title}",
            "filled_fields": filled_fields,
            "flagged_fields": flagged_fields,
            "uploaded_resume": best_resume,
            "available_resumes": available_resumes
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


lever_adapter = LeverAdapter()
