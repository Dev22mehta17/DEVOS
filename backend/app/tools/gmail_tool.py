import os
import logging
import uuid
import asyncio
from typing import Dict, Any, Optional, List
from app.tools.browser_tool import browser_tool
from app.core.memory_engine import memory_engine
from app.core.permission_engine import permission_engine
from app.tools.file_tool import file_tool

logger = logging.getLogger(__name__)


class GmailTool:
    @staticmethod
    def get_social_signature() -> str:
        """Generates a clean professional email signature with social links."""
        p = memory_engine.profile_data
        name = p.get("personal", {}).get("full_name", "Dev Mehta")
        role = p.get("professional", {}).get("current_role", "Software Engineer")
        phone = p.get("personal", {}).get("phone", "")
        links = p.get("links", {})
        
        sig_lines = [
            f"\n\nBest regards,\n{name}",
            f"{role}" if role else "",
            f"Phone: {phone}" if phone else "",
            f"LinkedIn: {links.get('linkedin', '')}" if links.get('linkedin') else "",
            f"GitHub: {links.get('github', '')}" if links.get('github') else "",
            f"Portfolio: {links.get('portfolio', '')}" if links.get('portfolio') else "",
        ]
        return "\n".join([l for l in sig_lines if l])

    @staticmethod
    async def create_draft(recipient: str, subject: str, body: str, attach_resume: bool = False) -> Dict[str, Any]:
        """Creates a fresh compose draft with optional resume attachment and signature."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"

        # Append signature if not already present
        sig = GmailTool.get_social_signature()
        if "Best regards" not in body and "Best," not in body:
            body = body + sig

        attached_file = None
        if attach_resume:
            attached_file = memory_engine.profile_data.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()

        draft_payload = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "action_id": action_id,
            "action_kind": "COMPOSE",
            "attached_file": attached_file,
            "account": "Primary Chrome Logged-in Google Account"
        }

        perm_check = permission_engine.check_action(
            action_id=action_id,
            action_type="compose_email",
            payload=draft_payload
        )

        return {
            "status": "DRAFT_READY",
            "action_id": action_id,
            "payload": draft_payload,
            "permission": perm_check
        }

    @staticmethod
    async def search_and_read_thread(query: str) -> Dict[str, Any]:
        """Searches Gmail for emails matching a query and extracts details of the latest thread."""
        try:
            page = await browser_tool.get_active_page()
            encoded_query = query.replace(" ", "+")
            search_url = f"https://mail.google.com/mail/u/0/#search/{encoded_query}"
            logger.info(f"[Gmail] Searching emails: {search_url}")

            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3.5)

            # Extract list of search result email rows
            thread_info = await page.evaluate("""() => {
                const rows = document.querySelectorAll('tr.zA, div[role="main"] tr');
                if (rows.length === 0) return null;

                const firstRow = rows[0];
                const senderEl = firstRow.querySelector('.zF, .yW span, .bA4 span, span[email]');
                const subjectEl = firstRow.querySelector('.bog span, .y6 span');
                const snippetEl = firstRow.querySelector('.y2');
                const dateEl = firstRow.querySelector('.xW span, .xY');

                return {
                    sender: senderEl ? (senderEl.getAttribute('email') || senderEl.innerText.trim()) : 'Recruiter / Hiring Team',
                    subject: subjectEl ? subjectEl.innerText.trim() : 'Interview Opportunity',
                    snippet: snippetEl ? snippetEl.innerText.trim() : '',
                    date: dateEl ? dateEl.innerText.trim() : ''
                };
            }""")

            if thread_info:
                logger.info(f"[Gmail] Found email thread: from='{thread_info['sender']}', subject='{thread_info['subject']}'")
                return {"status": "SUCCESS", "thread": thread_info}
            else:
                logger.warning(f"[Gmail] No emails found for query: '{query}'")
                return {"status": "NOT_FOUND", "message": f"No emails found matching query '{query}'."}

        except Exception as e:
            logger.error(f"[Gmail] Error searching emails: {e}")
            return {"status": "ERROR", "message": str(e)}

    @staticmethod
    async def create_reply_draft(query: str, reply_intent: str = "confirm availability", attach_resume: bool = False) -> Dict[str, Any]:
        """Finds matching email thread and drafts a context-aware reply for user approval."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"

        # Step 1: Search email
        search_res = await GmailTool.search_and_read_thread(query)
        thread = search_res.get("thread", {})

        sender = thread.get("sender", "Recruiter / Hiring Team")
        subject = thread.get("subject", "Interview / Opportunity")
        snippet = thread.get("snippet", "")

        # Format recipient (extract email or use sender name)
        reply_subj = subject if subject.lower().startswith("re:") else f"Re: {subject}"

        # Generate intelligent reply body
        name = memory_engine.profile_data.get("personal", {}).get("full_name", "Dev Mehta")
        sig = GmailTool.get_social_signature()

        if "availab" in reply_intent.lower() or "tomorrow" in reply_intent.lower():
            body = f"Hi {sender.split()[0] if sender else 'there'},\n\nThank you for reaching out! I would be delighted to connect. I am available tomorrow after 3:00 PM IST (or any time this week that works best for you).\n\nPlease let me know if you would like me to share any additional details.\n{sig}"
        elif "interest" in reply_intent.lower() or "apply" in reply_intent.lower():
            body = f"Hi {sender.split()[0] if sender else 'there'},\n\nThank you for reaching out regarding the opportunity! I am very interested in learning more about the role and how my background in backend systems and software engineering can contribute to your team.\n\nI have attached my updated resume for your review.\n{sig}"
            attach_resume = True
        else:
            body = f"Hi {sender.split()[0] if sender else 'there'},\n\nThank you for your message. {reply_intent.capitalize()}.\n\nLooking forward to hearing from you!\n{sig}"

        attached_file = None
        if attach_resume:
            attached_file = memory_engine.profile_data.get("documents", {}).get("active_resume_path") or file_tool.get_best_resume_path()

        draft_payload = {
            "recipient": sender,
            "subject": reply_subj,
            "body": body,
            "action_id": action_id,
            "action_kind": "REPLY",
            "original_snippet": snippet,
            "attached_file": attached_file,
            "account": "Primary Chrome Logged-in Google Account"
        }

        perm_check = permission_engine.check_action(
            action_id=action_id,
            action_type="compose_email",
            payload=draft_payload
        )

        return {
            "status": "DRAFT_READY",
            "action_id": action_id,
            "payload": draft_payload,
            "permission": perm_check,
            "thread_found": bool(thread)
        }

    @staticmethod
    async def create_forward_draft(query: str, forward_to: str, explanation: str = "") -> Dict[str, Any]:
        """Finds matching email thread and drafts a forward message for user approval."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"

        search_res = await GmailTool.search_and_read_thread(query)
        thread = search_res.get("thread", {})

        subject = thread.get("subject", "Forwarded Message")
        fwd_subj = subject if subject.lower().startswith("fwd:") else f"Fwd: {subject}"
        snippet = thread.get("snippet", "")
        sig = GmailTool.get_social_signature()

        body = f"Hi,\n\n{explanation or 'Forwarding this email for your review.'}\n\n--- Forwarded message ---\nFrom: {thread.get('sender', '')}\nSubject: {subject}\n\n{snippet}\n{sig}"

        draft_payload = {
            "recipient": forward_to,
            "subject": fwd_subj,
            "body": body,
            "action_id": action_id,
            "action_kind": "FORWARD",
            "original_snippet": snippet,
            "account": "Primary Chrome Logged-in Google Account"
        }

        perm_check = permission_engine.check_action(
            action_id=action_id,
            action_type="compose_email",
            payload=draft_payload
        )

        return {
            "status": "DRAFT_READY",
            "action_id": action_id,
            "payload": draft_payload,
            "permission": perm_check
        }

    @staticmethod
    async def send_draft(action_id: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Opens Gmail compose in Chrome, fills recipient, subject, body, attaches files, and sends."""
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "ERROR", "sent_on_chrome": False, "message": "Email send action was not approved."}

        recipient = payload.get("recipient", "") if payload else ""
        subject = payload.get("subject", "") if payload else ""
        body = payload.get("body", "") if payload else ""
        attached_file = payload.get("attached_file") if payload else None

        if not recipient:
            return {"status": "ERROR", "sent_on_chrome": False, "message": "No recipient email address provided."}

        logger.info(f"[Gmail] Starting send: to={recipient}, subject={subject}")

        if not browser_tool.context:
            logger.error("[Gmail] No browser context available")
            return {"status": "ERROR", "sent_on_chrome": False, "message": "No browser context"}

        page = None
        try:
            page = await browser_tool.get_active_page()
            await page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3.5)

            # Step 1: Click Compose
            compose_clicked = False
            compose_selectors = [
                'div.T-I.T-I-KE.L3',
                'div[gh="cm"]',
                '[aria-label="Compose"]',
            ]
            for sel in compose_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=5000)
                    if btn:
                        await btn.click()
                        compose_clicked = True
                        break
                except Exception:
                    continue

            if not compose_clicked:
                await page.keyboard.press("c")
                compose_clicked = True

            await asyncio.sleep(2.0)

            # Step 2: Fill To field
            to_filled = False
            to_selectors = [
                'input[aria-label="To recipients"]',
                'input[aria-label="To"]',
                'textarea[name="to"]',
                'input[name="to"]',
                'input[peoplekit-id]',
            ]
            for sel in to_selectors:
                try:
                    to_field = await page.wait_for_selector(sel, timeout=3000)
                    if to_field:
                        await to_field.click()
                        await to_field.fill("")
                        # Use fill() instead of keyboard.type() — keyboard.type() sends chars
                        # one at a time and Gmail autocomplete garbles the email address
                        await to_field.fill(recipient)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Tab")
                        to_filled = True
                        break
                except Exception:
                    continue

            if not to_filled:
                return {"status": "ERROR", "sent_on_chrome": False, "message": "Could not find To field on Gmail"}

            await asyncio.sleep(0.8)

            # Step 3: Fill Subject
            for sel in ['input[name="subjectbox"]', 'input[aria-label="Subject"]']:
                try:
                    subj = await page.wait_for_selector(sel, timeout=3000)
                    if subj:
                        await subj.click()
                        await subj.fill(subject)
                        break
                except Exception:
                    continue

            await asyncio.sleep(0.5)

            # Step 4: Fill Body — use innerHTML injection instead of keyboard.type()
            # keyboard.type() sends one character at a time which triggers Gmail Smart Compose
            # auto-suggestions, causing catastrophic text garbling.
            for sel in ['div[aria-label="Message Body"]', 'div[role="textbox"]', 'div[contenteditable="true"]']:
                try:
                    body_el = await page.wait_for_selector(sel, timeout=3000)
                    if body_el:
                        await body_el.click()
                        # Convert plain text body to HTML paragraphs for Gmail's contenteditable div
                        escaped_body = body.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
                        html_body = "<br>".join(
                            line if line.strip() else "<br>"
                            for line in escaped_body.split("\n")
                        )
                        await page.evaluate(f"""(sel) => {{
                            const el = document.querySelector(sel);
                            if (el) {{
                                el.innerHTML = `{html_body}`;
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }}
                        }}""", sel)
                        break
                except Exception:
                    continue

            await asyncio.sleep(1.0)

            # Step 5: Attach file if requested
            if attached_file and os.path.exists(attached_file):
                logger.info(f"[Gmail] Attaching file to email: {attached_file}")
                try:
                    attach_btn = await page.query_selector('div[command="Files"], div[aria-label*="Attach files"], div[data-tooltip*="Attach files"]')
                    if attach_btn:
                        async with page.expect_file_chooser(timeout=8000) as fc_info:
                            await attach_btn.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(attached_file)
                        logger.info("[Gmail] ✅ File attached successfully")
                        await asyncio.sleep(4.0)  # Wait for upload
                except Exception as attach_err:
                    logger.warning(f"[Gmail] File attach error: {attach_err}")

            # Step 6: Click Send or Native Gmail Schedule Send
            schedule_time = payload.get("schedule_time") if payload else None
            send_clicked = False

            if schedule_time:
                # ─── Native Gmail Schedule Send ───
                logger.info(f"[Gmail] Setting native Gmail Schedule Send: {schedule_time}")
                try:
                    # Click dropdown arrow next to Send button
                    more_send_btn = await page.query_selector(
                        'div[aria-label="More send options"], '
                        'div[data-tooltip="More send options"], '
                        'div[aria-haspopup="true"][data-tooltip*="send"], '
                        'div.T-I.J-J5-Ji.aoO.v7.T-I-atl'
                    )
                    if more_send_btn:
                        await more_send_btn.click()
                        await asyncio.sleep(1.0)

                        # Click "Schedule send" menu option
                        schedule_menu_opt = await page.wait_for_selector(
                            'div[role="menuitem"]:has-text("Schedule send"), '
                            'div.J-N:has-text("Schedule send"), '
                            'span:has-text("Schedule send")',
                            timeout=4000
                        )
                        if schedule_menu_opt:
                            await schedule_menu_opt.click()
                            await asyncio.sleep(1.5)

                            # Pick preset option or first available schedule slot (e.g. "Tomorrow morning")
                            slot_opt = await page.query_selector(
                                'div[role="menuitem"]:has-text("Tomorrow"), '
                                'div[role="menuitem"]:has-text("morning"), '
                                'div[role="menuitem"]:has-text("afternoon"), '
                                'div.J-N:has-text("Tomorrow")'
                            )
                            if slot_opt:
                                await slot_opt.click()
                                send_clicked = True
                                logger.info("[Gmail] ✅ Native Gmail Schedule Send configured via preset slot.")
                                await asyncio.sleep(2.0)
                            else:
                                # Try clicking confirm button in schedule dialog
                                confirm_btn = await page.query_selector('button:has-text("Schedule send"), div[role="button"]:has-text("Schedule send")')
                                if confirm_btn:
                                    await confirm_btn.click()
                                    send_clicked = True
                                    logger.info("[Gmail] ✅ Native Gmail Schedule Send confirmed.")
                                    await asyncio.sleep(2.0)
                except Exception as sched_err:
                    logger.warning(f"[Gmail] Native schedule send failed: {sched_err}. Falling back to normal send.")

            # Fallback / Normal Send
            if not send_clicked:
                send_selectors = [
                    'div[aria-label*="Send"][role="button"]',
                    'div[data-tooltip*="Send"][role="button"]',
                    'div.T-I.J-J5-Ji.aoO.v7.T-I-atl.L3',
                ]
                for sel in send_selectors:
                    try:
                        send_btn = await page.wait_for_selector(sel, timeout=3000)
                        if send_btn:
                            await send_btn.click()
                            send_clicked = True
                            break
                    except Exception:
                        continue

            if not send_clicked:
                try:
                    await page.keyboard.press("Meta+Enter")
                    send_clicked = True
                except Exception:
                    pass

            await asyncio.sleep(2.5)

            status_msg = "scheduled in Gmail" if schedule_time else "sent successfully"
            return {
                "status": "SENT" if send_clicked else "ERROR",
                "action_id": action_id,
                "sent_on_chrome": send_clicked,
                "message": f"Email to {recipient} {status_msg}." if send_clicked else "Could not click Send"
            }

        except Exception as e:
            logger.error(f"[Gmail] Fatal error: {e}")
            return {
                "status": "ERROR",
                "action_id": action_id,
                "sent_on_chrome": False,
                "message": f"Gmail error: {str(e)}"
            }


gmail_tool = GmailTool()
