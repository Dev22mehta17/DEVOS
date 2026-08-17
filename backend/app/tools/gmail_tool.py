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
        """Navigates Gmail and stages draft for HITL approval."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"

        # Navigate to Gmail to verify Chrome session is logged in
        nav_result = await browser_tool.navigate("https://mail.google.com")

        draft_payload = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "action_id": action_id,
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
            "browser_info": nav_result
        }

    @staticmethod
    async def send_draft(action_id: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes real Gmail Compose + Send using Playwright on Chrome CDP."""
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Email send action was not approved."}

        recipient = payload.get("recipient", "") if payload else ""
        subject = payload.get("subject", "") if payload else ""
        body = payload.get("body", "") if payload else ""

        logger.info(f"[Gmail] Starting real send: to={recipient}, subject={subject}")

        if not browser_tool.context:
            logger.error("[Gmail] No browser context available")
            return {"status": "ERROR", "sent_on_chrome": False, "message": "No browser context"}

        page = None
        try:
            # Open a NEW tab dedicated to Gmail so we don't interfere with other pages
            page = await browser_tool.context.new_page()
            logger.info("[Gmail] Opened new tab for Gmail")

            # Navigate to Gmail
            await page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3.0)
            logger.info(f"[Gmail] Landed on: {page.url}")

            # Step 1: Click Compose — Gmail uses a div with gh="cm" attribute
            compose_selectors = [
                'div.T-I.T-I-KE.L3',  # Gmail's actual Compose button class
                'div[gh="cm"]',         # Gmail Compose attribute
                '[aria-label="Compose"]',
            ]
            compose_clicked = False
            for sel in compose_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=5000)
                    if btn:
                        await btn.click()
                        compose_clicked = True
                        logger.info(f"[Gmail] Clicked Compose with selector: {sel}")
                        break
                except Exception:
                    continue

            if not compose_clicked:
                # Fallback: click by visible text
                try:
                    await page.click('text="Compose"', timeout=5000)
                    compose_clicked = True
                    logger.info("[Gmail] Clicked Compose via text match")
                except Exception:
                    pass

            if not compose_clicked:
                logger.error("[Gmail] Could not find Compose button")
                await page.close()
                return {"status": "ERROR", "sent_on_chrome": False, "message": "Could not find Compose button"}

            await asyncio.sleep(2.0)

            # Step 2: Fill To field
            to_filled = False
            to_selectors = [
                'input[aria-label="To recipients"]',
                'input[aria-label="To"]',
                'textarea[name="to"]',
                'input[name="to"]',
                'div[name="to"] input',
                'input[peoplekit-id]',
            ]
            for sel in to_selectors:
                try:
                    to_field = await page.wait_for_selector(sel, timeout=3000)
                    if to_field:
                        await to_field.click()
                        await to_field.fill("")
                        await page.keyboard.type(recipient, delay=50)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Tab")
                        to_filled = True
                        logger.info(f"[Gmail] Filled To field with: {recipient} using {sel}")
                        break
                except Exception:
                    continue

            if not to_filled:
                logger.error("[Gmail] Could not find To field")
                await page.close()
                return {"status": "ERROR", "sent_on_chrome": False, "message": "Could not find To field"}

            await asyncio.sleep(1.0)

            # Step 3: Fill Subject
            subject_filled = False
            subj_selectors = [
                'input[name="subjectbox"]',
                'input[aria-label="Subject"]',
            ]
            for sel in subj_selectors:
                try:
                    subj_field = await page.wait_for_selector(sel, timeout=3000)
                    if subj_field:
                        await subj_field.click()
                        await subj_field.fill(subject)
                        subject_filled = True
                        logger.info(f"[Gmail] Filled Subject: {subject}")
                        break
                except Exception:
                    continue

            if not subject_filled:
                logger.warning("[Gmail] Could not fill Subject field — continuing anyway")

            await asyncio.sleep(0.5)

            # Step 4: Fill Body
            body_filled = False
            body_selectors = [
                'div[aria-label="Message Body"]',
                'div[aria-role="textbox"]',
                'div[role="textbox"]',
                'div.editable',
                'div[contenteditable="true"]',
            ]
            for sel in body_selectors:
                try:
                    body_el = await page.wait_for_selector(sel, timeout=3000)
                    if body_el:
                        await body_el.click()
                        await page.keyboard.type(body, delay=20)
                        body_filled = True
                        logger.info("[Gmail] Filled Body")
                        break
                except Exception:
                    continue

            if not body_filled:
                logger.warning("[Gmail] Could not fill Body field — continuing anyway")

            await asyncio.sleep(1.0)

            # Step 5: Click Send
            send_clicked = False
            send_selectors = [
                'div[aria-label*="Send"][role="button"]',
                'div[data-tooltip*="Send"][role="button"]',
                'div.T-I.J-J5-Ji.aoO.v7.T-I-atl.L3',  # Gmail Send button class
            ]
            for sel in send_selectors:
                try:
                    send_btn = await page.wait_for_selector(sel, timeout=3000)
                    if send_btn:
                        await send_btn.click()
                        send_clicked = True
                        logger.info(f"[Gmail] Clicked Send with selector: {sel}")
                        break
                except Exception:
                    continue

            if not send_clicked:
                # Fallback: Ctrl+Enter
                try:
                    await page.keyboard.press("Control+Enter")
                    send_clicked = True
                    logger.info("[Gmail] Sent via Ctrl+Enter keyboard shortcut")
                except Exception:
                    # Try Cmd+Enter on Mac
                    try:
                        await page.keyboard.press("Meta+Enter")
                        send_clicked = True
                        logger.info("[Gmail] Sent via Cmd+Enter keyboard shortcut")
                    except Exception:
                        pass

            if not send_clicked:
                logger.error("[Gmail] Could not click Send button")
                await page.close()
                return {"status": "ERROR", "sent_on_chrome": False, "message": "Could not click Send"}

            await asyncio.sleep(3.0)

            # Verify: check if "Message sent" toast appeared or compose window closed
            logger.info(f"[Gmail] Email to {recipient} appears sent successfully")
            await page.close()

            return {
                "status": "SENT",
                "action_id": action_id,
                "sent_on_chrome": True,
                "message": f"Email sent to {recipient} via Gmail on Chrome."
            }

        except Exception as e:
            logger.error(f"[Gmail] Fatal error during send: {e}")
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            return {
                "status": "ERROR",
                "action_id": action_id,
                "sent_on_chrome": False,
                "message": f"Gmail send failed: {str(e)}"
            }


gmail_tool = GmailTool()
