import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, List, Optional
from app.core.permission_engine import ActionRiskLevel, permission_engine

logger = logging.getLogger(__name__)


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    risk_level: ActionRiskLevel
    handler: Callable
    category: str = "general"

    def to_gemini_declaration(self) -> Dict[str, Any]:
        """Converts to Google Gemini Function Declaration schema."""
        properties = {}
        required_fields = []

        for p_name, p_info in self.parameters.items():
            prop = {
                "type": p_info.get("type", "string").upper(),
                "description": p_info.get("description", "")
            }
            if "enum" in p_info:
                prop["enum"] = p_info["enum"]
            properties[p_name] = prop

            if p_info.get("required", True):
                required_fields.append(p_name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": required_fields
            }
        }

    def to_openai_declaration(self) -> Dict[str, Any]:
        """Converts to OpenAI / Open-Weight function calling JSON schema."""
        properties = {}
        required_fields = []

        for p_name, p_info in self.parameters.items():
            prop = {
                "type": p_info.get("type", "string").lower(),
                "description": p_info.get("description", "")
            }
            if "enum" in p_info:
                prop["enum"] = p_info["enum"]
            properties[p_name] = prop

            if p_info.get("required", True):
                required_fields.append(p_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_fields
                }
            }
        }


class ToolRegistry:
    """Central registry and execution dispatcher for all DevOS tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        risk_level: ActionRiskLevel,
        handler: Callable,
        category: str = "general"
    ):
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            risk_level=risk_level,
            handler=handler,
            category=category
        )
        self._tools[name] = tool_def
        logger.debug(f"[ToolRegistry] Registered tool: {name} (Risk: {risk_level.value})")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Returns all registered tool schemas formatted for Gemini function calling."""
        return [t.to_gemini_declaration() for t in self._tools.values()]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Returns all registered tool schemas formatted for OpenAI / vLLM function calling."""
        return [t.to_openai_declaration() for t in self._tools.values()]

    async def execute(self, tool_name: str, arguments: Dict[str, Any], action_id: Optional[str] = None) -> Dict[str, Any]:
        """Executes a registered tool with automated HITL risk verification."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "status": "ERROR",
                "error": f"Tool '{tool_name}' is not registered in ToolRegistry."
            }

        act_id = action_id or f"act_{tool_name}"

        # 1. Security Check via PermissionEngine
        if tool.risk_level in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL):
            perm_result = permission_engine.check_action(
                action_id=act_id,
                action_type=tool_name,
                payload=arguments
            )
            if perm_result.get("status") == "PENDING_APPROVAL":
                logger.info(f"[ToolRegistry] Tool '{tool_name}' halted for user approval (Action ID: {act_id})")
                return {
                    "status": "APPROVAL_REQUIRED",
                    "action_id": act_id,
                    "tool_name": tool_name,
                    "payload": arguments,
                    "permission": perm_result
                }

        # 2. Execute Handler (async or sync)
        try:
            logger.info(f"[ToolRegistry] Executing tool '{tool_name}' with args: {arguments}")
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)

            return {
                "status": "SUCCESS",
                "tool_name": tool_name,
                "result": result
            }
        except Exception as e:
            logger.error(f"[ToolRegistry] Error executing '{tool_name}': {e}", exc_info=True)
            return {
                "status": "ERROR",
                "tool_name": tool_name,
                "error": str(e)
            }


# Global Tool Registry Singleton
tool_registry = ToolRegistry()
