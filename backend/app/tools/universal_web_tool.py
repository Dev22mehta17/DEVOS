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


class UniversalWebTool:
    """Executes multi-step browser tasks on any supported website (job boards, registrations, portals)."""

    @staticmethod
    async def execute_web_task(url: str, goal_description: str) -> Dict[str, Any]:
        action_id = f"web_{uuid.uuid4().hex[:8]}"

        # Step 1: Open Target URL
        nav_res = await browser_tool.navigate(url)
        await asyncio.sleep(3.0)

        # Step 2: Auto-detect if we need to click an "Apply" / "Register" / "Sign Up" button first
        page_title = nav_res.get("title", "Web Task")
        if not browser_tool.page:
            return {"status": "ERROR", "message": "Browser page unavailable"}

        page = browser_tool.page

        # Check for initial trigger buttons if no form is directly visible
        try:
            apply_btn = await page.query_selector(
                'a:has-text("Apply"), button:has-text("Apply"), '
                'a:has-text("Register"), button:has-text("Register"), '
                'a:has-text("Sign Up"), button:has-text("Get Started")'
            )
            if apply_btn:
                # Only click if there are no inputs currently visible
                inputs_now = await page.query_selector_all('input[type="text"], input[type="email"], textarea')
                if len(inputs_now) == 0:
                    logger.info("[UniversalWeb] Clicking initial action button...")
                    await apply_btn.click()
                    await asyncio.sleep(3.0)
        except Exception as e:
            logger.debug(f"[UniversalWeb] Initial button check ignored: {e}")

        # Step 3: Inspect all form inputs on the webpage
        inputs = await browser_tool.inspect_inputs()
        logger.info(f"[UniversalWeb] Found {len(inputs)} fields on {url}")

        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []

        # Find best resume candidate
        best_resume = memory_engine.profile_data.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()
        available_resumes = [r["path"] for r in file_tool.find_resume_files()]
        if best_resume and best_resume not in available_resumes:
            available_resumes.insert(0, best_resume)

        text_input_idx = 0
        file_added = False

        for inp in inputs:
            label = inp.get("labelText") or inp.get("name") or inp.get("id") or ""
            ftype = inp.get("fieldType") or inp.get("type", "text")
            q_index = inp.get("questionIndex", 0)

            # 1. File Upload
            if ftype == "file" or "resume" in label.lower() or "cv" in label.lower():
                if not file_added:
                    file_added = True
                    if best_resume:
                        filled_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "value": f"[ATTACHED FILE] {best_resume}",
                            "is_file": True,
                            "file_path": best_resume,
                            "fieldType": "file",
                            "questionIndex": q_index
                        })
                    else:
                        flagged_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "reason": "Please attach a resume PDF.",
                            "is_file": True,
                            "fieldType": "file",
                            "questionIndex": q_index
                        })
                continue

            # 2. Radio Options
            if ftype == "radio":
                opts = inp.get("options", [])
                match = memory_engine.match_option(label, opts)
                if match:
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": match["matched_option"],
                        "options": opts,
                        "fieldType": "radio",
                        "questionIndex": q_index,
                        "is_auto_matched": True
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please select an option",
                        "options": opts,
                        "fieldType": "radio",
                        "questionIndex": q_index
                    })
                continue

            # 3. Checkbox Options
            if ftype == "checkbox":
                opts = inp.get("options", [])
                flagged_fields.append({
                    "field_label": label,
                    "field_id": inp.get("id"),
                    "reason": "Please choose applicable options",
                    "options": opts,
                    "fieldType": "checkbox",
                    "questionIndex": q_index
                })
                continue

            # 4. Dropdown Options
            if ftype == "dropdown":
                opts = inp.get("options", [])
                match = memory_engine.match_option(label, opts)
                if match:
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": match["matched_option"],
                        "options": opts,
                        "fieldType": "dropdown",
                        "questionIndex": q_index,
                        "is_auto_matched": True
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please select an option",
                        "options": opts,
                        "fieldType": "dropdown",
                        "questionIndex": q_index
                    })
                continue

            # 5. Text / Textarea
            val = memory_engine.get_field_value(label)
            if val is not None and val != "":
                idx = text_input_idx
                name_str = inp.get("name", "")
                await browser_tool.fill_input_by_index_or_name(idx, name_str, str(val))
                filled_fields.append({
                    "field_label": label,
                    "field_id": inp.get("id"),
                    "value": val,
                    "fieldType": "text",
                    "index": idx,
                    "name": name_str,
                    "questionIndex": q_index
                })
            else:
                # Open-ended answer generation
                is_open = ftype == "textarea" or any(k in label.lower() for k in ["why", "describe", "about", "project", "motivation", "interest", "statement"])
                if is_open:
                    gen_res = answer_generator.generate_answer(label, f"{page_title} {url} {goal_description}")
                    gen_ans = gen_res.get("answer", "")
                    idx = text_input_idx
                    name_str = inp.get("name", "")
                    if gen_ans:
                        await browser_tool.fill_input_by_index_or_name(idx, name_str, gen_ans[:500])
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": gen_ans[:500],
                        "is_ai_generated": True,
                        "ai_source": gen_res.get("source"),
                        "ai_company": gen_res.get("company"),
                        "fieldType": "text",
                        "index": idx,
                        "name": name_str,
                        "questionIndex": q_index
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please fill this field",
                        "fieldType": "text",
                        "questionIndex": q_index
                    })
            text_input_idx += 1

        review_payload = {
            "action_id": action_id,
            "form_url": url,
            "page_title": page_title,
            "goal_description": goal_description,
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


universal_web_tool = UniversalWebTool()
