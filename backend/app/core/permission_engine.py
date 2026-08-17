import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ActionRiskLevel(str, Enum):
    LOW = "LOW"             # Automatic: Read page, search web, inspect DOM, load memory
    MEDIUM = "MEDIUM"       # Informative: Local file reading, navigating URL
    HIGH = "HIGH"           # Approval Required: Compose email, upload file, fill form
    CRITICAL = "CRITICAL"   # Approval Required: Send email, submit form, delete file, run shell command

class ActionPolicy:
    RISK_MAP = {
        "browser_navigate": ActionRiskLevel.LOW,
        "browser_inspect": ActionRiskLevel.LOW,
        "memory_read": ActionRiskLevel.LOW,
        "file_search": ActionRiskLevel.MEDIUM,
        "compose_email": ActionRiskLevel.HIGH,
        "fill_form": ActionRiskLevel.HIGH,
        "upload_file": ActionRiskLevel.HIGH,
        "send_email": ActionRiskLevel.CRITICAL,
        "submit_form": ActionRiskLevel.CRITICAL,
        "run_command": ActionRiskLevel.CRITICAL,
    }

    @classmethod
    def get_risk_level(cls, action_type: str) -> ActionRiskLevel:
        return cls.RISK_MAP.get(action_type, ActionRiskLevel.HIGH)

    @classmethod
    def requires_approval(cls, action_type: str) -> bool:
        risk = cls.get_risk_level(action_type)
        return risk in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL)

class PermissionEngine:
    def __init__(self):
        # Support MULTIPLE pending approvals keyed by action_id
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
        self.approved_actions: set = set()

    def check_action(self, action_id: str, action_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates whether an action can execute immediately or requires HITL approval."""
        needs_approval = ActionPolicy.requires_approval(action_type)
        risk_level = ActionPolicy.get_risk_level(action_type)

        if not needs_approval or action_id in self.approved_actions:
            return {
                "status": "APPROVED",
                "risk_level": risk_level,
                "action_type": action_type,
                "action_id": action_id
            }

        # Stage action for approval (supports multiple concurrent actions)
        pending = {
            "action_id": action_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "payload": payload,
            "status": "PENDING_APPROVAL"
        }
        self.pending_approvals[action_id] = pending
        logger.info(f"Action {action_type} ({action_id}) paused for HITL approval.")
        return pending

    def approve_action(self, action_id: str) -> bool:
        if action_id in self.pending_approvals:
            self.approved_actions.add(action_id)
            del self.pending_approvals[action_id]
            logger.info(f"Action {action_id} explicitly approved by user.")
            return True
        # Also allow if already approved (idempotent)
        if action_id in self.approved_actions:
            logger.info(f"Action {action_id} was already approved (idempotent).")
            return True
        logger.warning(f"Action {action_id} not found in pending approvals.")
        return False

    def reject_action(self, action_id: str) -> bool:
        if action_id in self.pending_approvals:
            del self.pending_approvals[action_id]
            logger.info(f"Action {action_id} rejected by user.")
            return True
        return False

permission_engine = PermissionEngine()
