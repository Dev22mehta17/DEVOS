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
        """Navigates to Gmail and stages draft for HITL approval."""
        action_id = f"email_{uuid.uuid4().hex[:8]}"

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
        """Opens Gmail compose, fills To/Subject/Body ON the browser, then clicks Send."""
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "ERROR", "sent_on_chrome": False, "message": "Email send action was not approved."}

        recipient = payload.get("recipient", "") if payload else ""
        subject = payload.get("subject", "") if payload else ""
        body = payload.get("body", "") if payload else ""

        if not recipient:
            return {"status": "ERROR", "sent_on_chrome": False, "message": "No recipient email address provided."}

        logger.info(f"[Gmail] Starting real send: to={recipient}, subject={subject}")

        if not browser_tool.context:
            logger.error("[Gmail] No browser context available")
            return {"status": "ERROR", "sent_on_chrome": False, "message": "No browser context"}

        page = None
        try:
            # Open a dedicated new tab for Gmail
            page = await browser_tool.context.new_page()
            logger.info("[Gmail] Opened new tab for Gmail")

            # Navigate — use domcontentloaded (Gmail never reaches networkidle)
            await page.goto("https://mail.google.com/mail/u/0/#inbox", wait_until="domcontentloaded", timeout=30000)
            logger.info("[Gmail] Gmail page loaded (domcontentloaded)")
            # Wait for Gmail UI to render
            await asyncio.sleep(4.0)

            # Step 1: Click Compose
            compose_clicked = False
            compose_selectors = [
                'div.T-I.T-I-KE.L3',      # Gmail's actual Compose button class
                'div[gh="cm"]',             # Gmail Compose attribute
                '[aria-label="Compose"]',
            ]
            for sel in compose_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=5000)
                    if btn:
                        await btn.click()
                        compose_clicked = True
                        logger.info(f"[Gmail] Clicked Compose: {sel}")
                        break
                except Exception:
                    continue

            if not compose_clicked:
                # Fallback: press 'c' keyboard shortcut which opens Compose in Gmail
                await page.keyboard.press("c")
                compose_clicked = True
                logger.info("[Gmail] Opened Compose via 'c' keyboard shortcut")

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
                        await page.keyboard.type(recipient, delay=30)
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Tab")
                        to_filled = True
                        logger.info(f"[Gmail] Filled To: {recipient}")
                        break
                except Exception:
                    continue

            if not to_filled:
                logger.error("[Gmail] Could not find To field")
                await page.close()
                return {"status": "ERROR", "sent_on_chrome": False, "message": "Could not find To field on Gmail"}

            await asyncio.sleep(0.8)

            # Step 3: Fill Subject
            subject_filled = False
            for sel in ['input[name="subjectbox"]', 'input[aria-label="Subject"]']:
                try:
                    subj = await page.wait_for_selector(sel, timeout=3000)
                    if subj:
                        await subj.click()
                        await subj.fill(subject)
                        subject_filled = True
                        logger.info(f"[Gmail] Filled Subject: {subject}")
                        break
                except Exception:
                    continue

            await asyncio.sleep(0.5)

            # Step 4: Fill Body
            body_filled = False
            for sel in ['div[aria-label="Message Body"]', 'div[role="textbox"]', 'div[contenteditable="true"]']:
                try:
                    body_el = await page.wait_for_selector(sel, timeout=3000)
                    if body_el:
                        await body_el.click()
                        await page.keyboard.type(body, delay=15)
                        body_filled = True
                        logger.info("[Gmail] Filled Body")
                        break
                except Exception:
                    continue

            await asyncio.sleep(1.0)

            # Step 5: Click Send — try button first, then keyboard shortcut
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
                        logger.info(f"[Gmail] Clicked Send: {sel}")
                        break
                except Exception:
                    continue

            if not send_clicked:
                # Fallback: Cmd+Enter (Mac) / Ctrl+Enter (Windows)
                try:
                    await page.keyboard.press("Meta+Enter")
                    send_clicked = True
                    logger.info("[Gmail] Sent via Cmd+Enter")
                except Exception:
                    pass

            await asyncio.sleep(3.0)

            if send_clicked:
                logger.info(f"[Gmail] ✅ Email to {recipient} sent successfully")
            else:
                logger.error("[Gmail] Could not send email")

            await page.close()

            return {
                "status": "SENT" if send_clicked else "ERROR",
                "action_id": action_id,
                "sent_on_chrome": send_clicked,
                "message": f"Email sent to {recipient} via Gmail." if send_clicked else "Could not click Send"
            }

        except Exception as e:
            logger.error(f"[Gmail] Fatal error: {e}")
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            return {
                "status": "ERROR",
                "action_id": action_id,
                "sent_on_chrome": False,
                "message": f"Gmail error: {str(e)}"
            }


gmail_tool = GmailTool()
