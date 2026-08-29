import os
import json
import logging
import asyncio
import requests
from typing import Dict, Any, List, Optional, Callable
from app.agent.tool_registry import tool_registry, ToolDefinition
from app.core.permission_engine import ActionRiskLevel
from app.core.memory_engine import memory_engine
from app.tools.browser_tool import browser_tool
from app.tools.form_tool import form_tool
from app.tools.gmail_tool import gmail_tool
from app.tools.email_campaign_tool import email_campaign_tool
from app.tools.recruiter_pipeline_tool import recruiter_pipeline_tool
from app.tools.deep_research_tool import deep_research_tool
from app.tools.universal_web_tool import universal_web_tool
from app.tools.ats_adapters import ats_detector, ATSPlatform, greenhouse_adapter, lever_adapter, linkedin_adapter
from app.core.answer_generator import answer_generator

logger = logging.getLogger(__name__)


class LLMAgentCore:
    """Autonomous ReAct / Function-Calling Agent Core powered by ToolRegistry & Gemini."""

    def __init__(self):
        self._broadcaster: Optional[Callable] = None
        self._register_all_tools()

    def set_broadcaster(self, broadcaster: Callable):
        self._broadcaster = broadcaster

    async def _emit(self, step_type: str, message: str, details: Dict[str, Any] = None):
        if self._broadcaster:
            await self._broadcaster(step_type, message, details or {})

    def _register_all_tools(self):
        """Registers all DevOS browser, email, form, ATS, memory, and search tools into ToolRegistry."""
        
        # 1. Browser Navigation
        tool_registry.register(
            name="open_url",
            description="Navigates the Chrome browser to a given web URL.",
            parameters={
                "url": {"type": "string", "description": "The full HTTP/HTTPS URL to open", "required": True}
            },
            risk_level=ActionRiskLevel.LOW,
            handler=browser_tool.navigate,
            category="browser"
        )

        # 2. Memory Lookup
        tool_registry.register(
            name="search_memory",
            description="Searches the candidate's vector memory and resume achievements for relevant context.",
            parameters={
                "query": {"type": "string", "description": "The topic or question to query in memory", "required": True}
            },
            risk_level=ActionRiskLevel.LOW,
            handler=lambda query: memory_engine.query_semantic_memory(query, top_k=4),
            category="memory"
        )

        # 3. Candidate Profile Summary
        tool_registry.register(
            name="get_candidate_profile",
            description="Retrieves the candidate's structured profile (education, CGPA, Amazon Pay experience, skills, social links).",
            parameters={},
            risk_level=ActionRiskLevel.LOW,
            handler=lambda: memory_engine.profile_data,
            category="memory"
        )

        # 4. Universal / Google Form Autofill
        tool_registry.register(
            name="autofill_job_application",
            description="Inspects and auto-fills a job application form (Google Forms, Greenhouse, Lever, LinkedIn, or Web Portal) with candidate details and resume.",
            parameters={
                "url": {"type": "string", "description": "The job post or form URL", "required": True}
            },
            risk_level=ActionRiskLevel.HIGH,
            handler=self._handle_smart_job_application,
            category="form"
        )

        # 5. Greenhouse Form Fill
        tool_registry.register(
            name="fill_greenhouse_form",
            description="Fills a job application on Greenhouse ATS (boards.greenhouse.io) with resume and custom question answers.",
            parameters={
                "url": {"type": "string", "description": "The Greenhouse job application URL", "required": True}
            },
            risk_level=ActionRiskLevel.HIGH,
            handler=greenhouse_adapter.fill_application,
            category="ats"
        )

        # 6. Lever Form Fill
        tool_registry.register(
            name="fill_lever_form",
            description="Fills a job application on Lever ATS (jobs.lever.co) with resume and candidate information.",
            parameters={
                "url": {"type": "string", "description": "The Lever job application URL", "required": True}
            },
            risk_level=ActionRiskLevel.HIGH,
            handler=lever_adapter.fill_application,
            category="ats"
        )

        # 7. LinkedIn Easy Apply
        tool_registry.register(
            name="start_linkedin_easy_apply",
            description="Steps through LinkedIn Easy Apply wizard for a job post, answers screening questions, and stages final review.",
            parameters={
                "job_url": {"type": "string", "description": "The LinkedIn job posting URL", "required": True}
            },
            risk_level=ActionRiskLevel.HIGH,
            handler=linkedin_adapter.apply_to_job,
            category="ats"
        )

        # 8. Email Campaign
        tool_registry.register(
            name="prepare_recruiter_email_campaign",
            description="Prepares a personalized cold outreach email campaign for recruiters with role-specific skills and schedule.",
            parameters={
                "goal_text": {"type": "string", "description": "Prompt containing recruiter emails, companies, roles, and schedule time", "required": True}
            },
            risk_level=ActionRiskLevel.HIGH,
            handler=email_campaign_tool.prepare_campaign,
            category="email"
        )

        # 9. Recruiter Inbox Triage
        tool_registry.register(
            name="triage_recruiter_inbox",
            description="Scans Gmail inbox for recruiter threads and generates categorized actionable response drafts.",
            parameters={},
            risk_level=ActionRiskLevel.HIGH,
            handler=recruiter_pipeline_tool.scan_and_triage_recruiter_threads,
            category="email"
        )

        # 10. Web Search / Deep Research
        tool_registry.register(
            name="perform_web_search",
            description="Searches Google and extracts technical summaries, comparison matrices, and citations.",
            parameters={
                "query": {"type": "string", "description": "The search or research query", "required": True}
            },
            risk_level=ActionRiskLevel.LOW,
            handler=deep_research_tool.research_topic_or_comparison,
            category="search"
        )

        logger.info(f"[LLMAgentCore] Initialized ToolRegistry with {len(tool_registry.list_tools())} tools.")

    async def _handle_smart_job_application(self, url: str) -> Dict[str, Any]:
        """Smart router that detects ATS platform and delegates to the specialized adapter."""
        platform = ats_detector.detect_from_url(url)
        logger.info(f"[LLMAgentCore] Smart Application Router detected platform: {platform.value} for {url}")

        if platform == ATSPlatform.GREENHOUSE:
            await self._emit("DOM_ACTION", "Detected Greenhouse ATS portal. Launching Greenhouse Adapter...")
            return await greenhouse_adapter.fill_application(url)

        elif platform == ATSPlatform.LEVER:
            await self._emit("DOM_ACTION", "Detected Lever ATS portal. Launching Lever Adapter...")
            return await lever_adapter.fill_application(url)

        elif platform == ATSPlatform.LINKEDIN:
            await self._emit("DOM_ACTION", "Detected LinkedIn Job. Launching LinkedIn Easy Apply Wizard...")
            return await linkedin_adapter.apply_to_job(url)

        elif platform == ATSPlatform.GOOGLE_FORMS:
            await self._emit("DOM_ACTION", "Detected Google Form. Launching Google Form Automation Engine...")
            return await form_tool.process_form(url)

        else:
            await self._emit("DOM_ACTION", "Launching Universal Web Form Engine...")
            return await universal_web_tool.execute_web_task(url, "Job Application")

    async def run(self, user_goal: str) -> Dict[str, Any]:
        """Executes an autonomous goal using LLM tool calling with Gemini or smart local dispatch."""
        await self._emit("THINKING", f"Agent reasoning over user goal: '{user_goal}'")

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        # Case 1: Gemini 2.0 Flash Tool-Calling Engine (if API key configured)
        if api_key:
            try:
                return await self._run_gemini_tool_loop(api_key, user_goal)
            except Exception as e:
                logger.warning(f"[LLMAgentCore] Gemini tool calling error: {e}. Falling back to Smart Dispatcher.")

        # Case 2: Smart Semantic Dispatcher Fallback (Zero-latency local engine)
        return await self._run_smart_dispatcher(user_goal)

    async def _run_gemini_tool_loop(self, api_key: str, user_goal: str) -> Dict[str, Any]:
        """Drives multi-step function calling loop via Gemini REST API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

        tools_declaration = [{"function_declarations": tool_registry.get_gemini_tools()}]
        candidate_summary = memory_engine.get_full_candidate_summary()

        system_instruction = f"""You are DevOS, an autonomous personal computer agent running on macOS.
You have tools to control Google Chrome via CDP, fill job applications (Greenhouse, Lever, LinkedIn, Google Forms), draft & send recruiter emails, and search memory.

Candidate Info:
{candidate_summary}

Rules:
1. When asked to apply for a job or fill a form, call 'autofill_job_application' with the URL.
2. When asked to send recruiter outreach, call 'prepare_recruiter_email_campaign'.
3. When asked to triage recruiter emails, call 'triage_recruiter_inbox'.
4. When asked a technical or comparison question, call 'perform_web_search'.
"""

        messages = [
            {"role": "user", "parts": [{"text": f"User Goal: {user_goal}"}]}
        ]

        payload = {
            "contents": messages,
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "tools": tools_declaration,
            "generationConfig": {"temperature": 0.1}
        }

        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Gemini API returned {resp.status_code}: {resp.text}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return await self._run_smart_dispatcher(user_goal)

        first_cand = candidates[0]
        parts = first_cand.get("content", {}).get("parts", [])

        for part in parts:
            if "functionCall" in part:
                fn_call = part["functionCall"]
                fn_name = fn_call.get("name")
                fn_args = fn_call.get("args", {})

                await self._emit("THINKING", f"LLM decided tool call: {fn_name}({json.dumps(fn_args)})")
                
                # Execute tool via ToolRegistry
                tool_res = await tool_registry.execute(fn_name, fn_args)
                
                if tool_res.get("status") == "APPROVAL_REQUIRED":
                    # Staged for HITL review in UI
                    review_details = tool_res.get("payload", {})
                    await self._emit("APPROVAL_REQUIRED", f"Tool '{fn_name}' requires approval.", review_details)
                    return tool_res

                return tool_res

        # If LLM returned text response directly
        text_reply = "".join([p.get("text", "") for p in parts]).strip()
        return {"status": "SUCCESS", "message": text_reply}

    async def _run_smart_dispatcher(self, user_goal: str) -> Dict[str, Any]:
        """Smart fallback dispatcher using intent detection & direct ToolRegistry execution."""
        import re
        goal_clean = user_goal.strip()
        goal_lower = goal_clean.lower()

        # 1. URL Detection
        url_match = re.search(r'https?://[^\s\'"<>]+', goal_clean)
        target_url = url_match.group(0).strip(".,'\"") if url_match else None

        if target_url:
            await self._emit("THINKING", f"Detected target URL: {target_url}. Invoking autofill_job_application...")
            return await self._handle_smart_job_application(target_url)

        # 2. Email Campaign Detection
        email_addresses = re.findall(r'[\w\.\-\+]+@[\w\.\-]+\.\w+', goal_clean)
        if len(email_addresses) >= 2 or any(k in goal_lower for k in ["campaign", "send to all", "bulk email", "send intro to"]):
            await self._emit("THINKING", "Detected bulk outreach campaign. Invoking prepare_recruiter_email_campaign...")
            return await tool_registry.execute("prepare_recruiter_email_campaign", {"goal_text": goal_clean})

        # 3. Recruiter Pipeline Triage
        if any(k in goal_lower for k in ["recruiter pipeline", "check recruiter", "triage recruiter", "scan inbox"]):
            await self._emit("THINKING", "Detected inbox triage request. Invoking triage_recruiter_inbox...")
            return await tool_registry.execute("triage_recruiter_inbox", {})

        # 4. Single Email Compose
        if any(k in goal_lower for k in ["email", "mail", "gmail"]):
            recipient = email_addresses[0] if email_addresses else "mehtadev2004@gmail.com"
            await self._emit("THINKING", f"Drafting email to {recipient}...")
            return await gmail_tool.create_draft(recipient, "Application – Dev Mehta", "Hi,\n\nPlease find my resume attached.\n\nBest regards,\nDev Mehta", attach_resume=True)

        # 5. Web Research
        await self._emit("THINKING", f"Performing web research for: {goal_clean}...")
        return await tool_registry.execute("perform_web_search", {"query": goal_clean})


llm_agent = LLMAgentCore()
