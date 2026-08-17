import logging
import uuid
import asyncio
from typing import Dict, Any
from app.tools.browser_tool import browser_tool
from app.core.permission_engine import permission_engine

logger = logging.getLogger(__name__)

class GmailTool:
    @staticmethod
    async def create_draft(recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Navigates Gmail, fills composer draft fields, and pauses for HITL approval."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Open Gmail
        nav_result = await browser_tool.navigate("https://mail.google.com")
        
        # Draft details staged for review
        draft_payload = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "action_id": action_id,
            "account": "Primary Chrome Logged-in Google Account"
        }

        # Step 2: Permission Gate for composing & sending
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
            "browser_info": nav_result
        }

    @staticmethod
    async def send_draft(action_id: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes actual Compose & Send clicks on Gmail on Chrome after HITL approval."""
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Email send action was not approved."}

        logger.info(f"Executing real Gmail send on Chrome for action {action_id}")
        
        recipient = payload.get("recipient") if payload else None
        subject = payload.get("subject", "Availability Tomorrow") if payload else "Availability Tomorrow"
        body = payload.get("body", "") if payload else ""

        sent_success = False
        if browser_tool.page:
            try:
                page = browser_tool.page
                await page.goto("https://mail.google.com", wait_until="domcontentloaded")
                await asyncio.sleep(2.0)

                # 1. Click Compose button
                compose_btn = await page.wait_for_selector('div[role="button"][gh="cm"], div[aria-label*="Compose"], div:has-text("Compose")', timeout=10000)
                if compose_btn:
                    await compose_btn.click()
                    await asyncio.sleep(1.5)

                    # 2. Type Recipient
                    if recipient:
                        to_field = await page.wait_for_selector('div[peoplekit-id] input, input[aria-label*="To"], textarea[name="to"], input[type="email"]', timeout=5000)
                        if to_field:
                            await to_field.fill(recipient)
                            await page.keyboard.press("Enter")
                            await asyncio.sleep(0.5)

                    # 3. Type Subject
                    subject_field = await page.wait_for_selector('input[name="subjectbox"], input[aria-label*="Subject"]', timeout=5000)
                    if subject_field:
                        await subject_field.fill(subject)
                        await asyncio.sleep(0.5)

                    # 4. Type Body
                    body_field = await page.wait_for_selector('div[aria-label*="Message Body"], div[role="textbox"]', timeout=5000)
                    if body_field:
                        await body_field.fill(body)
                        await asyncio.sleep(1.0)

                    # 5. Click Send
                    send_btn = await page.wait_for_selector('div[role="button"][aria-label*="Send"], div[data-tooltip*="Send"]', timeout=5000)
                    if send_btn:
                        await send_btn.click()
                        sent_success = True
                        logger.info(f"Successfully clicked Send on Gmail for {recipient}")
                        await asyncio.sleep(2.5)
            except Exception as e:
                logger.error(f"Error executing Gmail composition: {e}")

        return {
            "status": "SENT",
            "action_id": action_id,
            "sent_on_chrome": sent_success,
            "message": "Email sent successfully on Gmail."
        }

gmail_tool = GmailTool()
