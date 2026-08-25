import os
import logging
import uuid
import asyncio
from typing import Dict, Any, List
from app.tools.browser_tool import browser_tool
from app.tools.file_tool import file_tool
from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine

logger = logging.getLogger(__name__)


class FormTool:
    @staticmethod
    async def process_form(form_url: str) -> Dict[str, Any]:
        action_id = f"form_{uuid.uuid4().hex[:8]}"

        # Step 1: Open Form URL
        nav_result = await browser_tool.navigate(form_url)
        await asyncio.sleep(2.5)  # Wait for form to fully render

        page_title = nav_result.get("title", "")
        if "page not found" in page_title.lower() or "404" in page_title.lower():
            logger.warning(f"[FormTool] Page returned 404 / Not Found for {form_url}")
            return {
                "status": "PAGE_NOT_FOUND",
                "message": f"The page at {form_url} returned 'Page not found'. Please verify the form link.",
                "payload": {"form_url": form_url, "page_title": page_title, "filled_fields": [], "flagged_fields": []}
            }

        # Step 2: Inspect ALL Form Inputs (text, radio, checkbox, dropdown, file)
        inputs = await browser_tool.inspect_inputs()
        logger.info(f"[FormTool] Detected {len(inputs)} form fields")

        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []
        uploaded_resume_path = None

        # Check for resume upload files on machine
        resume_files = file_tool.find_resume_files()
        available_resume_paths = [r["path"] for r in resume_files]

        default_res_path = memory_engine.profile_data.get("documents", {}).get("active_resume_path")
        if default_res_path and default_res_path not in available_resume_paths:
            available_resume_paths.insert(0, default_res_path)
        uploaded_resume_path = default_res_path or file_tool.get_best_resume_path()

        file_added = False
        text_input_idx = 0  # Track text input index separately for fill_input_by_index_or_name

        for inp in inputs:
            label = inp.get("labelText") or inp.get("name") or inp.get("id") or ""
            field_type = inp.get("fieldType") or inp.get("type", "text")
            q_index = inp.get("questionIndex", 0)

            # ─── File Upload ───
            if field_type == "file" or "resume" in label.lower() or "cv" in label.lower():
                if not file_added:
                    file_added = True
                    if uploaded_resume_path:
                        filled_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "value": f"[ATTACHED FILE] {uploaded_resume_path}",
                            "is_file": True,
                            "file_path": uploaded_resume_path,
                            "fieldType": "file",
                            "questionIndex": q_index
                        })
                    else:
                        flagged_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "reason": "No local resume found. Upload one using the panel above.",
                            "is_file": True,
                            "fieldType": "file",
                            "questionIndex": q_index
                        })
                continue

            # ─── Radio Buttons ───
            if field_type == "radio":
                options = inp.get("options", [])
                match = memory_engine.match_option(label, options)
                if match:
                    chosen_val = match["matched_option"]
                    # Click option immediately on Chrome so page displays it
                    await browser_tool.select_radio_option(q_index, chosen_val, label)
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": chosen_val,
                        "options": options,
                        "fieldType": "radio",
                        "questionIndex": q_index,
                        "confidence": match["confidence"],
                        "is_auto_matched": True
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please select an option",
                        "options": options,
                        "fieldType": "radio",
                        "questionIndex": q_index
                    })
                continue

            # ─── Checkboxes ───
            if field_type == "checkbox":
                options = inp.get("options", [])
                # For checkboxes, try to match multiple options from skills or other lists
                matched_opts = []
                skills = memory_engine.profile_data.get("professional", {}).get("skills", [])
                for opt in options:
                    for skill in skills:
                        if skill.lower() in opt.lower() or opt.lower() in skill.lower():
                            matched_opts.append(opt)
                            break
                
                if matched_opts:
                    # Click checkboxes immediately on Chrome
                    await browser_tool.select_checkbox_options(q_index, matched_opts, label)
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": ", ".join(matched_opts),
                        "options": options,
                        "fieldType": "checkbox",
                        "questionIndex": q_index,
                        "is_auto_matched": True
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please select applicable options",
                        "options": options,
                        "fieldType": "checkbox",
                        "questionIndex": q_index
                    })
                continue

            # ─── Dropdown ───
            if field_type == "dropdown":
                options = inp.get("options", [])
                match = memory_engine.match_option(label, options)
                if match:
                    chosen_val = match["matched_option"]
                    # Select option immediately on Chrome
                    await browser_tool.select_dropdown_option(q_index, chosen_val, label)
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": chosen_val,
                        "options": options,
                        "fieldType": "dropdown",
                        "questionIndex": q_index,
                        "confidence": match["confidence"],
                        "is_auto_matched": True
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Please select an option",
                        "options": options,
                        "fieldType": "dropdown",
                        "questionIndex": q_index
                    })
                continue

            # ─── Text / Textarea / Email / Phone / etc ───
            val = memory_engine.get_field_value(label)
            if val is not None and val != "":
                idx = text_input_idx
                name_str = inp.get("name", "")
                await browser_tool.fill_input_by_index_or_name(idx, name_str, str(val), label=label, question_index=q_index)
                filled_fields.append({
                    "field_label": label,
                    "field_id": inp.get("id"),
                    "value": val,
                    "is_file": False,
                    "fieldType": "text",
                    "index": idx,
                    "name": name_str,
                    "questionIndex": q_index
                })
            else:
                # Use AnswerGenerator for open-ended or long-form questions
                from app.core.answer_generator import answer_generator
                page_title = nav_result.get("title", "")
                is_open_ended = (
                    field_type == "textarea" or 
                    any(k in label.lower() for k in [
                        "why", "what", "describe", "about", "project", "tell us", "cover letter", 
                        "motivation", "challenge", "background", "experience", "hire", "interest",
                        "proud", "proudest", "learn", "learned", "struggle", "achievement", "contribution",
                        "internship", "work", "comment", "anything else", "note", "statement", "essay",
                        "ppo", "offer", "reason", "strength", "weakness"
                    ])
                )

                if is_open_ended:
                    gen_res = answer_generator.generate_answer(label, f"{page_title} {form_url}")
                    gen_ans = gen_res.get("answer", "")
                    idx = text_input_idx
                    name_str = inp.get("name", "")
                    if gen_ans:
                        await browser_tool.fill_input_by_index_or_name(idx, name_str, gen_ans[:500], label=label, question_index=q_index)
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
                        "reason": "Value not found in profile. Please enter manually.",
                        "fieldType": "text",
                        "index": text_input_idx,
                        "name": inp.get("name", ""),
                        "questionIndex": q_index
                    })

            text_input_idx += 1

        logger.info(f"[FormTool] Filled: {len(filled_fields)}, Flagged: {len(flagged_fields)}")

        form_review_payload = {
            "action_id": action_id,
            "form_url": form_url,
            "page_title": nav_result.get("title", "Form"),
            "filled_fields": filled_fields,
            "flagged_fields": flagged_fields,
            "uploaded_resume": uploaded_resume_path,
            "available_resumes": available_resume_paths
        }

        perm_check = permission_engine.check_action(
            action_id=action_id,
            action_type="submit_form",
            payload=form_review_payload
        )

        return {
            "status": "FORM_REVIEW_READY",
            "action_id": action_id,
            "payload": form_review_payload,
            "permission": perm_check
        }

    @staticmethod
    def _resolve_resume_path(selected_resume: str) -> str:
        """Resolves a resume path to an absolute path that exists on disk."""
        if not selected_resume:
            return ""
        if os.path.isabs(selected_resume) and os.path.exists(selected_resume):
            return selected_resume
        from pathlib import Path
        uploads_dir = Path(__file__).parent.parent.parent / "uploads"
        candidate = uploads_dir / os.path.basename(selected_resume)
        if candidate.exists():
            return str(candidate.resolve())
        downloads = Path.home() / "Downloads" / os.path.basename(selected_resume)
        if downloads.exists():
            return str(downloads.resolve())
        documents = Path.home() / "Documents" / os.path.basename(selected_resume)
        if documents.exists():
            return str(documents.resolve())
        mem_path = memory_engine.profile_data.get("documents", {}).get("active_resume_path", "")
        if mem_path and os.path.exists(mem_path):
            return mem_path
        logger.warning(f"[FormTool] Could not resolve resume path: {selected_resume}")
        return selected_resume

    @staticmethod
    async def submit_form(action_id: str, approval_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Form submission was not approved."}

        logger.info(f"[FormTool] Executing instant form submission for action {action_id}")

        page = await browser_tool.get_active_page()
        form_url = approval_payload.get("form_url") if approval_payload else None

        # Check if the page is currently on the form or needs re-navigation
        current_url = page.url
        is_already_on_form = form_url and (
            form_url in current_url or 
            "docs.google.com/forms" in current_url or 
            "forms.gle" in current_url
        )

        if not is_already_on_form and form_url:
            logger.info(f"[FormTool] Navigating to form: {form_url}")
            await page.goto(form_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2.0)

        # Step 1: Update fields if user edited them in modal
        all_fields = []
        if approval_payload:
            all_fields = approval_payload.get("updated_fields", []) or approval_payload.get("filled_fields", [])

        text_idx = 0
        for f in all_fields:
            ft = f.get("fieldType", "text")
            val = f.get("value", "")

            if ft == "text" and val and not str(val).startswith("[ATTACHED FILE]"):
                f_idx = f.get("index", text_idx)
                f_name = f.get("name", "")
                f_label = f.get("field_label", "")
                f_qidx = f.get("questionIndex")
                await browser_tool.fill_input_by_index_or_name(f_idx, f_name, str(val), label=f_label, question_index=f_qidx)
                text_idx += 1

            elif ft == "radio" and val:
                q_idx = f.get("questionIndex", 0)
                label = f.get("field_label", "")
                await browser_tool.select_radio_option(q_idx, str(val), label)

            elif ft == "checkbox" and val:
                q_idx = f.get("questionIndex", 0)
                label = f.get("field_label", "")
                selected_opts = [v.strip() for v in str(val).split(",")]
                await browser_tool.select_checkbox_options(q_idx, selected_opts, label)

            elif ft == "dropdown" and val:
                q_idx = f.get("questionIndex", 0)
                label = f.get("field_label", "")
                await browser_tool.select_dropdown_option(q_idx, str(val), label)

        # Step 2: Upload resume ONLY if not already attached on page
        selected_res = approval_payload.get("selected_resume") if approval_payload else None
        if selected_res:
            # Check if file is already attached on page (e.g. badge visible)
            has_attached_file = await page.evaluate("""() => {
                const attachedBadge = document.querySelector('.s09pje, div[data-item-id], div[aria-label*="Remove file"], span:has-text(".pdf")');
                return !!attachedBadge;
            }""")

            if not has_attached_file:
                resolved_path = FormTool._resolve_resume_path(selected_res)
                if resolved_path and os.path.exists(resolved_path):
                    logger.info(f"[FormTool] Uploading resume: {resolved_path}")
                    await browser_tool.upload_file_to_google_form(resolved_path)
            else:
                logger.info("[FormTool] Resume already attached on form. Skipping re-upload.")

        # Step 3: Instant Submit click
        submitted = await browser_tool.click_submit_button()
        logger.info(f"[FormTool] Submit button clicked: {submitted}")

        # Step 4: Verification
        await asyncio.sleep(1.2)
        try:
            page_text = await page.inner_text("body")
            if "your response has been recorded" in page_text.lower() or "thanks" in page_text.lower() or "submitted" in page_text.lower():
                logger.info("[FormTool] ✅ Form submission confirmed — success page detected")
                return {
                    "status": "SUBMITTED",
                    "action_id": action_id,
                    "submitted_on_chrome": True,
                    "verified": True,
                    "message": "Form submitted and confirmed on Chrome."
                }
        except Exception:
            pass

        return {
            "status": "SUBMITTED",
            "action_id": action_id,
            "submitted_on_chrome": submitted,
            "verified": False,
            "message": "Form submitted on Chrome." if submitted else "Form submit button not found."
        }


form_tool = FormTool()
