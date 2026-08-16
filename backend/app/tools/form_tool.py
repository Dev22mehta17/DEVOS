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

        # Check for resume upload file
        resume_path = file_tool.get_best_resume_path()

        for inp in inputs:
            label = inp.get("labelText") or inp.get("name") or inp.get("id")
            inp_type = inp.get("type", "")

            # File upload handling
            if inp_type == "file" or "resume" in label.lower() or "cv" in label.lower():
                if resume_path:
                    uploaded_resume_path = resume_path
                    filled_fields.append({
                        "field_label": label or "Resume Upload",
                        "field_id": inp.get("id"),
                        "value": f"[ATTACHED FILE] {resume_path}",
                        "is_file": True,
                        "file_path": resume_path
                    })
                else:
                    flagged_fields.append({
                        "field_label": label or "Resume Upload",
                        "field_id": inp.get("id"),
                        "reason": "No local resume found in ~/Downloads or ~/Documents",
                        "is_file": True
                    })
                continue

            # Text / Standard inputs lookup
            val = memory_engine.get_field_value(label)
            if val:
                filled_fields.append({
                    "field_label": label,
                    "field_id": inp.get("id"),
                    "value": val,
                    "is_file": False
                })
            else:
                # Open ended answer generation via semantic memory fallback
                if inp_type in ("textarea", "text") and any(k in label.lower() for k in ["why", "describe", "about", "project"]):
                    context_snippets = memory_engine.query_semantic_memory(label)
                    gen_ans = f"Based on my SDE intern experience at Amazon and degree at Thapar University: {' '.join(context_snippets[:2])}"
                    filled_fields.append({
                        "field_label": label,
                        "field_id": inp.get("id"),
                        "value": gen_ans[:250],
                        "is_ai_generated": True
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
            "uploaded_resume": uploaded_resume_path
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
    async def submit_form(action_id: str) -> Dict[str, Any]:
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Form submission was not approved."}

        logger.info(f"Executing form submission for action {action_id}")
        return {
            "status": "SUBMITTED",
            "action_id": action_id,
            "message": "Form submitted successfully."
        }

form_tool = FormTool()
