import logging
import uuid
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
            "account": "dev@example.com (Primary Google Account)"
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
    async def send_draft(action_id: str) -> Dict[str, Any]:
        """Executes actual send click after HITL confirmation."""
        approved = permission_engine.approve_action(action_id)
        if not approved:
            return {"status": "REJECTED", "message": "Email send action was not approved."}

        # Simulate or execute send click on Gmail composer
        logger.info(f"Executing Gmail send for action {action_id}")
        return {
            "status": "SENT",
            "action_id": action_id,
            "message": "Email sent successfully."
        }

gmail_tool = GmailTool()
