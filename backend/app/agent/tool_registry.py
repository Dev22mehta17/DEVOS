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
        self._ensure_default_tools()
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        self._ensure_default_tools()
        return list(self._tools.values())

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Returns all registered tool schemas formatted for Gemini function calling."""
        self._ensure_default_tools()
        return [t.to_gemini_declaration() for t in self._tools.values()]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Returns all registered tool schemas formatted for OpenAI / vLLM function calling."""
        self._ensure_default_tools()
        return [t.to_openai_declaration() for t in self._tools.values()]

    def _ensure_default_tools(self):
        """Lazy-registers default tools if empty."""
        if self._tools:
            return

        from app.tools.browser_tool import browser_tool
        from app.core.memory_engine import memory_engine
        from app.tools.form_tool import form_tool
        from app.tools.ats_adapters import greenhouse_adapter, lever_adapter, linkedin_adapter
        from app.tools.email_campaign_tool import email_campaign_tool
        from app.tools.recruiter_pipeline_tool import recruiter_pipeline_tool
        from app.tools.deep_research_tool import deep_research_tool

        self.register(
            name="open_url",
            description="Navigates Chrome browser to a given web URL.",
            parameters={"url": {"type": "string", "description": "The full URL to open", "required": True}},
            risk_level=ActionRiskLevel.LOW,
            handler=browser_tool.navigate,
            category="browser"
        )
        self.register(
            name="search_memory",
            description="Searches candidate vector memory and resume achievements for relevant context.",
            parameters={"query": {"type": "string", "description": "Query topic", "required": True}},
            risk_level=ActionRiskLevel.LOW,
            handler=lambda query: memory_engine.query_semantic_memory(query, top_k=4),
            category="memory"
        )
        self.register(
            name="get_candidate_profile",
            description="Retrieves candidate structured profile (education, CGPA, Amazon Pay internship, skills, links).",
            parameters={},
            risk_level=ActionRiskLevel.LOW,
            handler=lambda: memory_engine.profile_data,
            category="memory"
        )
        self.register(
            name="fill_greenhouse_form",
            description="Autofills a job application on Greenhouse ATS (boards.greenhouse.io).",
            parameters={"url": {"type": "string", "description": "Greenhouse application URL", "required": True}},
            risk_level=ActionRiskLevel.HIGH,
            handler=greenhouse_adapter.fill_application,
            category="ats"
        )
        self.register(
            name="fill_lever_form",
            description="Autofills a job application on Lever ATS (jobs.lever.co).",
            parameters={"url": {"type": "string", "description": "Lever application URL", "required": True}},
            risk_level=ActionRiskLevel.HIGH,
            handler=lever_adapter.fill_application,
            category="ats"
        )
        self.register(
            name="start_linkedin_easy_apply",
            description="Automates LinkedIn Easy Apply wizard with screening questions.",
            parameters={"job_url": {"type": "string", "description": "LinkedIn job URL", "required": True}},
            risk_level=ActionRiskLevel.HIGH,
            handler=linkedin_adapter.apply_to_job,
            category="ats"
        )
        self.register(
            name="autofill_job_application",
            description="Autofills Google Forms or general web job applications.",
            parameters={"url": {"type": "string", "description": "Target application URL", "required": True}},
            risk_level=ActionRiskLevel.HIGH,
            handler=form_tool.process_form,
            category="form"
        )
        self.register(
            name="prepare_recruiter_email_campaign",
            description="Prepares a personalized recruiter outreach email campaign with schedule.",
            parameters={"goal_text": {"type": "string", "description": "Prompt with recipient emails", "required": True}},
            risk_level=ActionRiskLevel.HIGH,
            handler=email_campaign_tool.prepare_campaign,
            category="email"
        )
        self.register(
            name="triage_recruiter_inbox",
            description="Scans Gmail for recruiter emails and generates actionable reply drafts.",
            parameters={},
            risk_level=ActionRiskLevel.HIGH,
            handler=recruiter_pipeline_tool.scan_and_triage_recruiter_threads,
            category="email"
        )
        self.register(
            name="perform_web_search",
            description="Searches Google and extracts technical summaries and comparison dossiers.",
            parameters={"query": {"type": "string", "description": "Search query", "required": True}},
            risk_level=ActionRiskLevel.LOW,
            handler=deep_research_tool.research_topic_or_comparison,
            category="search"
        )

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
