import logging
import uuid
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
        
        # Step 2: Inspect Form Inputs
        inputs = await browser_tool.inspect_inputs()
        
        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []
        uploaded_resume_path = None

        # Check for resume upload files on machine
        resume_files = file_tool.find_resume_files()
        available_resume_paths = [r["path"] for r in resume_files]

        # Check if user previously ingested/uploaded a resume
        default_res_path = memory_engine.profile_data.get("documents", {}).get("active_resume_path")
        if default_res_path and default_res_path not in available_resume_paths:
            available_resume_paths.insert(0, default_res_path)

        uploaded_resume_path = default_res_path or file_tool.get_best_resume_path()

        file_added = False
        for inp in inputs:
            label = inp.get("labelText") or inp.get("name") or inp.get("id")
            inp_type = inp.get("type", "")

            # File upload handling (add only once)
            if inp_type == "file" or "resume" in label.lower() or "cv" in label.lower():
                if not file_added:
                    file_added = True
                    if uploaded_resume_path:
                        filled_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "value": f"[ATTACHED FILE] {uploaded_resume_path}",
                            "is_file": True,
                            "file_path": uploaded_resume_path
                        })
                    else:
                        flagged_fields.append({
                            "field_label": label or "Resume Upload",
                            "field_id": inp.get("id"),
                            "reason": "No local resume found. Ingest resume using Memory panel.",
                            "is_file": True
                        })
                continue

            # Text / Standard inputs lookup
            val = memory_engine.get_field_value(label)
            if val:
                idx = inp.get("index", 0)
                name_str = inp.get("name", "")
                await browser_tool.fill_input_by_index_or_name(idx, name_str, str(val))
                filled_fields.append({
                    "field_label": label,
                    "field_id": inp.get("id"),
                    "value": val,
                    "is_file": False,
                    "index": idx,
                    "name": name_str
                })
            else:
                # Open ended answer generation via semantic memory fallback
                if inp_type in ("textarea", "text") and any(k in label.lower() for k in ["why", "describe", "about", "project"]):
                    context_snippets = memory_engine.query_semantic_memory(label)
                    gen_ans = f"Based on my SDE intern experience at Amazon and degree at Thapar University: {' '.join(context_snippets[:2])}"
                    idx = inp.get("index", 0)
                    name_str = inp.get("name", "")
                    await browser_tool.fill_input_by_index_or_name(idx, name_str, gen_ans[:250])
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": gen_ans[:250],
                        "is_ai_generated": True,
                        "index": idx,
                        "name": name_str
                    })
                else:
                    flagged_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "reason": "Required user confirmation / value missing in memory"
                    })

        form_review_payload = {
            "action_id": action_id,
            "form_url": form_url,
            "page_title": nav_result.get("title", "Form"),
            "filled_fields": filled_fields,
            "flagged_fields": flagged_fields,
            "uploaded_resume": uploaded_resume_path,
            "available_resumes": available_resume_paths
        }

        # Step 3: Permission Gate for Form Submission
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
    async def submit_form(action_id: str, approval_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Form submission was not approved."}

        logger.info(f"Executing form submission for action {action_id}")
        
        # Apply updated fields edited by user in UI popup
        if approval_payload and "updated_fields" in approval_payload:
            for idx, f in enumerate(approval_payload["updated_fields"]):
                if f.get("value"):
                    f_idx = f.get("index", idx)
                    f_name = f.get("name", "")
                    await browser_tool.fill_input_by_index_or_name(f_idx, f_name, f["value"])

        # Upload selected resume to Google Form file input if required
        selected_res = approval_payload.get("selected_resume") if approval_payload else None
        if selected_res:
            logger.info(f"Uploading selected resume file: {selected_res}")
            await browser_tool.upload_file_to_google_form(selected_res)

        submitted = await browser_tool.click_submit_button()
        return {
            "status": "SUBMITTED",
            "action_id": action_id,
            "submitted_on_chrome": submitted,
            "message": "Form submitted successfully on Chrome."
        }

form_tool = FormTool()
