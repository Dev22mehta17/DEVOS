import asyncio
import time
import logging
from typing import Dict, Any, Optional
from app.agent.agent_state import ExecutionPlan, TaskStep, GoalType, StepStatus
from app.agent.goal_interpreter import goal_interpreter
from app.agent.planner import planner
from app.agent.verifier import verifier
from app.agent.recovery import recovery_engine

from app.tools.browser_tool import browser_tool
from app.tools.form_tool import form_tool
from app.tools.gmail_tool import gmail_tool
from app.tools.universal_web_tool import universal_web_tool
from app.tools.deep_research_tool import deep_research_tool
from app.tools.recruiter_pipeline_tool import recruiter_pipeline_tool

logger = logging.getLogger(__name__)

# Callback hook for pushing SSE telemetry events to frontend
_event_broadcaster = None

def set_event_broadcaster(fn):
    global _event_broadcaster
    _event_broadcaster = fn

async def emit_agent_event(step_type: str, message: str, details: Dict[str, Any] = None):
    global _event_broadcaster
    if _event_broadcaster:
        try:
            await _event_broadcaster(step_type, message, details or {})
        except Exception as e:
            logger.warning(f"[AgentExecutor] Failed to emit SSE event: {e}")

class AgentExecutor:
    """Executes dynamic multi-step plans with observe-act-verify loops and SSE telemetry."""

    @staticmethod
    async def execute_goal(goal_text: str) -> Dict[str, Any]:
        logger.info(f"[AgentExecutor] Starting autonomous execution for: '{goal_text}'")
        
        # Step 1: Goal Interpretation
        interpreted = goal_interpreter.interpret(goal_text)
        goal_type = interpreted["goal_type"]
        
        await emit_agent_event("THINKING", f"Interpreted goal: [{goal_type.value}] -> {interpreted.get('action_kind', '')}")

        # Handle URL required case
        if interpreted.get("action_kind") == "URL_REQUIRED":
            await emit_agent_event("COMPLETED", "Please provide a target form or job portal URL: e.g. 'Fill form at https://...'")
            return {"status": "URL_REQUIRED", "message": "Please provide a valid URL in prompt."}

        # Step 2: Plan Generation
        plan: ExecutionPlan = planner.create_plan(interpreted)
        plan.status = StepStatus.RUNNING
        
        await emit_agent_event("PLAN_INITIALIZED", f"Generated {len(plan.steps)}-step execution plan for {goal_type.value}", plan.to_summary())

        # Step 3: Execute Steps based on Goal Type
        try:
            # ─── A. Job Application Workflow ───
            if goal_type == GoalType.JOB_APPLICATION:
                target_url = interpreted["target_url"]
                
                # Step 1 & 2: Navigation & Form Inspection
                await emit_agent_event("DOM_ACTION", f"Step 1/7: Navigating to target portal: {target_url}")
                await emit_agent_event("DOM_ACTION", "Step 2/7: Inspecting input controls, radio groups, and file uploaders...")
                await emit_agent_event("MEMORY_QUERY", "Step 3/7: Retrieving candidate profile attributes & matching resume...")

                if "docs.google.com/forms" in target_url or "forms.gle" in target_url:
                    form_res = await form_tool.process_form(target_url)
                else:
                    form_res = await universal_web_tool.execute_web_task(target_url, goal_text)

                if form_res.get("status") == "PAGE_NOT_FOUND":
                    await emit_agent_event("COMPLETED", f"⚠️ Error: The target link returned 'Page not found' (404). Please verify that the link is accessible.")
                    return form_res

                filled_count = len(form_res.get("payload", {}).get("filled_fields", []))
                flagged_count = len(form_res.get("payload", {}).get("flagged_fields", []))

                if filled_count == 0 and flagged_count == 0:
                    await emit_agent_event("COMPLETED", f"⚠️ No form fields detected on {target_url}. Page may be restricted or require sign-in.")
                    return form_res

                await emit_agent_event("DOM_ACTION", f"Step 4/7: Populated {filled_count} fields directly on open Chrome page.")
                await emit_agent_event("APPROVAL_REQUIRED", f"Step 5/7: Review sheet ready ({filled_count} fields populated). Click Approve & Submit on Chrome.", form_res["payload"])
                return form_res

            # ─── B. Deep Research & Dossier Workflow ───
            elif goal_type == GoalType.DEEP_RESEARCH:
                query = interpreted.get("query", goal_text)
                entities = interpreted.get("entities", [])
                
                await emit_agent_event("DOM_ACTION", f"Step 1/4: Deconstructing research vectors for '{query}'...")
                await emit_agent_event("DOM_ACTION", f"Step 2/4: Crawling primary documentation and pricing sources on Chrome...")
                
                dossier = await deep_research_tool.research_topic_or_comparison(query, entities)
                
                await emit_agent_event("DOM_ACTION", f"Step 3/4: Scraped pricing models and feature matrices from {len(dossier.get('sources', []))} verified sources.")
                await emit_agent_event("RESEARCH_DOSSIER", f"Step 4/4: Deep Research Dossier generated for '{query}'", dossier)
                await emit_agent_event("COMPLETED", f"Deep Research completed: Interactive comparison dossier displayed in UI.", dossier)
                return {"status": "COMPLETED", "dossier": dossier}

            # ─── C. Proactive Recruiter Pipeline Workflow ───
            elif goal_type == GoalType.RECRUITER_PIPELINE:
                await emit_agent_event("DOM_ACTION", "Step 1/3: Scanning Gmail for active recruiter threads & interview invites...")
                
                pipeline_data = await recruiter_pipeline_tool.scan_and_triage_recruiter_threads()
                
                total_items = pipeline_data.get("total_threads", 0)
                await emit_agent_event("DOM_ACTION", f"Step 2/3: Triaged {total_items} recruiter threads into action categories & tailored draft replies.")
                await emit_agent_event("RECRUITER_QUEUE", f"Step 3/3: Recruiter Triage Queue ready ({total_items} pending actions). Review in drawer.", pipeline_data)
                return pipeline_data

            # ─── D. Single Gmail Action Workflow ───
            elif goal_type == GoalType.GMAIL_ACTION:
                action_kind = interpreted.get("action_kind", "COMPOSE")
                
                if action_kind == "REPLY":
                    sq = interpreted.get("search_query", "recruiter")
                    await emit_agent_event("DOM_ACTION", f"Step 1/3: Locating Gmail thread matching: '{sq}'...")
                    reply_res = await gmail_tool.create_reply_draft(sq, reply_intent=goal_text, attach_resume=interpreted.get("attach_resume", True))
                    await emit_agent_event("APPROVAL_REQUIRED", f"Step 2/3: Reply draft prepared for {reply_res['payload']['recipient']}. Review in modal.", reply_res["payload"])
                    return reply_res

                elif action_kind == "FORWARD":
                    sq = interpreted.get("search_query", "interview")
                    fwd_to = interpreted.get("recipient", "rahul@example.com")
                    await emit_agent_event("DOM_ACTION", f"Step 1/3: Locating thread to forward matching: '{sq}'...")
                    fwd_res = await gmail_tool.create_forward_draft(sq, forward_to=fwd_to, explanation=goal_text)
                    await emit_agent_event("APPROVAL_REQUIRED", f"Step 2/3: Forward draft staged to {fwd_to}. Review in modal.", fwd_res["payload"])
                    return fwd_res

                else:
                    recipient = interpreted.get("recipient", "mehtadev2004@gmail.com")
                    await emit_agent_event("MEMORY_QUERY", f"Step 1/3: Preparing email draft to: '{recipient}'...")
                    draft_res = await gmail_tool.create_draft(
                        recipient=recipient,
                        subject="Application / Availability Follow-up",
                        body=f"Hi,\n\nI am writing to express my interest and confirm my availability. Looking forward to connecting with your team!",
                        attach_resume=interpreted.get("attach_resume", False)
                    )
                    await emit_agent_event("APPROVAL_REQUIRED", f"Step 2/3: Email draft prepared for {recipient}. Review in popup.", draft_res["payload"])
                    return draft_res

            # ─── E. Universal Search Workflow ───
            else:
                query = interpreted.get("query", goal_text)
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                
                await emit_agent_event("DOM_ACTION", f"Step 1/2: Submitting query to Google Search: '{query}'")
                await browser_tool.navigate(search_url)
                
                await emit_agent_event("THINKING", "Step 2/2: Extracting AI Overview, Key Facts, and top sources from Google...")
                summary = await browser_tool.extract_search_summary()
                
                search_data = {
                    "query": query,
                    "search_url": search_url,
                    "direct_answer": summary.get("direct_answer", ""),
                    "key_facts": summary.get("key_facts", []),
                    "sources": summary.get("sources", [])
                }
                
                await emit_agent_event("SEARCH_RESULT", f"Found direct answer for '{query}'", search_data)
                await emit_agent_event("COMPLETED", f"Search completed: Answer & sources displayed in UI and Chrome.", search_data)
                return {"status": "COMPLETED", **search_data}

        except Exception as e:
            logger.error(f"[AgentExecutor] Execution error: {e}")
            await emit_agent_event("STEP_FAILED", f"Agent execution error: {str(e)}")
            return {"status": "ERROR", "message": str(e)}

agent_executor = AgentExecutor()
