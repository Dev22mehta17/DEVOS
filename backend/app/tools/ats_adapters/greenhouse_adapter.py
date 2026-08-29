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


class GreenhouseAdapter:
    """Specialized automation adapter for Greenhouse ATS (boards.greenhouse.io)."""

    @staticmethod
    async def fill_application(url: str, goal_description: str = "") -> Dict[str, Any]:
        action_id = f"greenhouse_{uuid.uuid4().hex[:8]}"
        logger.info(f"[GreenhouseAdapter] Opening job post: {url}")

        # Step 1: Navigate to Greenhouse application page
        nav_res = await browser_tool.navigate(url)
        await asyncio.sleep(2.5)

        page = await browser_tool.get_active_page()
        if not page:
            return {"status": "ERROR", "message": "Browser page unavailable"}

        page_title = await page.title()

        # Step 2: Auto-scroll to application form if needed
        await page.evaluate("""() => {
            const form = document.querySelector('#app_form, #application_form, div#application, form');
            if (form) form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }""")
        await asyncio.sleep(1.0)

        # Step 3: Extract Candidate Data from Memory
        p = memory_engine.profile_data
        personal = p.get("personal", {})
        full_name = personal.get("full_name", "Dev Mehta")
        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else "Dev"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Mehta"
        email = personal.get("email_primary", "mehtadev2004@gmail.com")
        phone = personal.get("phone", "+91-7206049507")
        location = personal.get("location", "India")
        links = p.get("links", {})
        linkedin_url = links.get("linkedin", "")
        github_url = links.get("github", "")
        portfolio_url = links.get("portfolio", "")

        # Find best resume
        best_resume = p.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()
        available_resumes = [r["path"] for r in file_tool.find_resume_files()]
        if best_resume and best_resume not in available_resumes:
            available_resumes.insert(0, best_resume)

        filled_fields: List[Dict[str, Any]] = []
        flagged_fields: List[Dict[str, Any]] = []

        # Step 4: Fill standard Greenhouse fields
        standard_fields_map = [
            ("#first_name, input[name*='first_name'], input[autocomplete='given-name']", first_name, "First Name"),
            ("#last_name, input[name*='last_name'], input[autocomplete='family-name']", last_name, "Last Name"),
            ("#email, input[name*='email'], input[autocomplete='email']", email, "Email"),
            ("#phone, input[name*='phone'], input[autocomplete='tel']", phone, "Phone Number"),
        ]

        for selector, val, label in standard_fields_map:
            try:
                el = await page.query_selector(selector)
                if el and await el.is_visible():
                    await el.fill(val)
                    filled_fields.append({
                        "field_label": label,
                        "field_id": selector,
                        "value": val,
                        "fieldType": "text",
                        "is_auto_matched": True
                    })
            except Exception as e:
                logger.debug(f"[GreenhouseAdapter] Error filling {label}: {e}")

        # Step 5: Fill Social and Portfolio URLs
        url_fields_map = [
            ("linkedin", linkedin_url, "LinkedIn Profile"),
            ("github", github_url, "GitHub Profile"),
            ("portfolio", portfolio_url, "Portfolio / Website"),
            ("website", portfolio_url, "Personal Website")
        ]

        for key, val, label in url_fields_map:
            if not val:
                continue
            try:
                matched_input = await page.evaluate(f"""(key, val) => {{
                    const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="url"], input:not([type])'));
                    for (const inp of inputs) {{
                        const lbl = (inp.getAttribute('aria-label') || inp.placeholder || inp.name || inp.id || '').toLowerCase();
                        const parentText = (inp.closest('.field, div, label') ? inp.closest('.field, div, label').innerText : '').toLowerCase();
                        if (lbl.includes(key) || parentText.includes(key)) {{
                            inp.value = val;
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return inp.id || inp.name || key;
                        }}
                    }}
                    return null;
                }}""", key, val)
                if matched_input:
                    filled_fields.append({
                        "field_label": label,
                        "field_id": matched_input,
                        "value": val,
                        "fieldType": "text",
                        "is_auto_matched": True
                    })
            except Exception as e:
                logger.debug(f"[GreenhouseAdapter] Error filling URL {key}: {e}")

        # Step 6: Attach Resume File
        if best_resume and os.path.exists(best_resume):
            try:
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(best_resume)
                    filled_fields.append({
                        "field_label": "Resume / CV",
                        "field_id": "resume_file",
                        "value": f"[ATTACHED FILE] {best_resume}",
                        "is_file": True,
                        "file_path": best_resume,
                        "fieldType": "file"
                    })
                    logger.info(f"[GreenhouseAdapter] ✅ Attached resume: {best_resume}")
            except Exception as f_err:
                logger.warning(f"[GreenhouseAdapter] Resume attach error: {f_err}")
                flagged_fields.append({
                    "field_label": "Resume Upload",
                    "field_id": "resume_file",
                    "reason": "Please attach your resume manually.",
                    "is_file": True,
                    "fieldType": "file"
                })
        else:
            flagged_fields.append({
                "field_label": "Resume Upload",
                "field_id": "resume_file",
                "reason": "No local resume found.",
                "is_file": True,
                "fieldType": "file"
            })

        # Step 7: Inspect remaining custom questions / dropdowns
        try:
            custom_questions = await page.evaluate("""() => {
                const results = [];
                const fields = document.querySelectorAll('.field, .custom-question, div[id*="question"]');
                fields.forEach((f, idx) => {
                    const labelEl = f.querySelector('label, .label');
                    const label = labelEl ? labelEl.innerText.trim() : '';
                    if (!label || label.toLowerCase().includes('first name') || label.toLowerCase().includes('last name') || label.toLowerCase().includes('email') || label.toLowerCase().includes('phone') || label.toLowerCase().includes('resume')) return;

                    const select = f.querySelector('select');
                    const textarea = f.querySelector('textarea');
                    const textInput = f.querySelector('input[type="text"], input:not([type])');

                    if (select) {
                        const opts = Array.from(select.options).map(o => o.text.trim()).filter(Boolean);
                        results.push({ index: idx, label: label, type: 'dropdown', options: opts, id: select.id || select.name });
                    } else if (textarea) {
                        results.push({ index: idx, label: label, type: 'textarea', id: textarea.id || textarea.name });
                    } else if (textInput && !textInput.value) {
                        results.push({ index: idx, label: label, type: 'text', id: textInput.id || textInput.name });
                    }
                });
                return results;
            }""")

            for cq in custom_questions:
                q_label = cq.get("label", "")
                q_type = cq.get("type", "text")
                q_opts = cq.get("options", [])
                q_id = cq.get("id", "")

                if q_type == "dropdown":
                    match = memory_engine.match_option(q_label, q_opts)
                    if match:
                        chosen = match["matched_option"]
                        await page.evaluate(f"""(id, chosen) => {{
                            const sel = document.getElementById(id) || document.querySelector(`[name="${{id}}"]`);
                            if (sel) {{
                                for (let opt of sel.options) {{
                                    if (opt.text.trim().toLowerCase() === chosen.toLowerCase()) {{
                                        sel.value = opt.value;
                                        sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        break;
                                    }}
                                }}
                            }}
                        }}""", q_id, chosen)
                        filled_fields.append({
                            "field_label": q_label,
                            "field_id": q_id,
                            "value": chosen,
                            "options": q_opts,
                            "fieldType": "dropdown",
                            "is_auto_matched": True
                        })
                    else:
                        flagged_fields.append({
                            "field_label": q_label,
                            "field_id": q_id,
                            "reason": "Please select an option",
                            "options": q_opts,
                            "fieldType": "dropdown"
                        })
                elif q_type == "textarea":
                    # Generate authentic answer via AnswerGenerator
                    gen_res = answer_generator.generate_answer(q_label, f"{page_title} {url} {goal_description}")
                    gen_ans = gen_res.get("answer", "")
                    if gen_ans:
                        await page.evaluate(f"""(id, val) => {{
                            const ta = document.getElementById(id) || document.querySelector(`[name="${{id}}"]`);
                            if (ta) {{
                                ta.value = val;
                                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}""", q_id, gen_ans[:600])
                        filled_fields.append({
                            "field_label": q_label,
                            "field_id": q_id,
                            "value": gen_ans[:600],
                            "is_ai_generated": True,
                            "ai_source": gen_res.get("source"),
                            "fieldType": "text"
                        })
                    else:
                        flagged_fields.append({
                            "field_label": q_label,
                            "field_id": q_id,
                            "reason": "Please fill response",
                            "fieldType": "text"
                        })
        except Exception as cq_err:
            logger.debug(f"[GreenhouseAdapter] Custom question extraction ignored: {cq_err}")

        # Step 8: Prepare Review Payload & Stage HITL Permission
        review_payload = {
            "action_id": action_id,
            "form_url": url,
            "portal_kind": "greenhouse",
            "page_title": page_title,
            "goal_description": goal_description or f"Greenhouse Job Application for {page_title}",
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


greenhouse_adapter = GreenhouseAdapter()
