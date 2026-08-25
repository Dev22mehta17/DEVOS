from typing import Dict, Any, List
from app.agent.agent_state import ExecutionPlan, TaskStep, GoalType, StepStatus
import logging

logger = logging.getLogger(__name__)

class Planner:
    """Generates dynamic multi-step Execution Plans tailored to the goal and portal type."""

    @staticmethod
    def create_plan(interpreted_goal: Dict[str, Any]) -> ExecutionPlan:
        goal_type = interpreted_goal.get("goal_type", GoalType.CUSTOM_TASK)
        goal_text = interpreted_goal.get("original_prompt", "")
        steps: List[TaskStep] = []

        # ─── 1. Job Application Plan ───
        if goal_type == GoalType.JOB_APPLICATION:
            target_url = interpreted_goal.get("target_url")
            steps = [
                TaskStep(
                    step_index=1,
                    title="Navigate to Job Portal",
                    description=f"Opening target application URL: {target_url}",
                    action_type="NAVIGATE",
                    payload={"url": target_url}
                ),
                TaskStep(
                    step_index=2,
                    title="Inspect Form Controls",
                    description="Scanning candidate input fields, dropdowns, radio groups, and file uploaders",
                    action_type="INSPECT_FORM",
                    payload={"url": target_url}
                ),
                TaskStep(
                    step_index=3,
                    title="Retrieve Profile & Resume",
                    description="Matching profile attributes and selecting active candidate resume from memory",
                    action_type="RETRIEVE_MEMORY",
                    payload={"attach_resume": interpreted_goal.get("attach_resume", True)}
                ),
                TaskStep(
                    step_index=4,
                    title="Populate Candidate Details",
                    description="Auto-filling text inputs, selecting radio options, and staging resume live on Chrome",
                    action_type="FILL_DOM",
                    payload={"url": target_url}
                ),
                TaskStep(
                    step_index=5,
                    title="Human-in-the-Loop Review",
                    description="Presenting editable application review sheet for user approval",
                    action_type="STAGING_HITL",
                    payload={"requires_approval": True}
                ),
                TaskStep(
                    step_index=6,
                    title="Submit Application",
                    description="Executing live form submission on Chrome upon approval",
                    action_type="SUBMIT_FORM",
                    payload={"url": target_url}
                ),
                TaskStep(
                    step_index=7,
                    title="Verify Submission",
                    description="Confirming success confirmation page / response recorded banner",
                    action_type="VERIFY_SUBMISSION",
                    payload={}
                )
            ]

        # ─── 2. Deep Research & Dossier Plan ───
        elif goal_type == GoalType.DEEP_RESEARCH:
            query = interpreted_goal.get("query", goal_text)
            entities = interpreted_goal.get("entities", [])
            steps = [
                TaskStep(
                    step_index=1,
                    title="Deconstruct Research Vectors",
                    description=f"Generating multi-hop queries for '{query}' across pricing, features, and official docs",
                    action_type="DECONSTRUCT_QUERIES",
                    payload={"query": query, "entities": entities}
                ),
                TaskStep(
                    step_index=2,
                    title="Crawl Official Sources in Chrome",
                    description="Navigating to primary documentation and pricing pages",
                    action_type="CRAWL_SOURCES",
                    payload={"query": query}
                ),
                TaskStep(
                    step_index=3,
                    title="Extract Metrics & Feature Matrices",
                    description="Scraping structured tables, fee schedules, and verified data points",
                    action_type="EXTRACT_METRICS",
                    payload={}
                ),
                TaskStep(
                    step_index=4,
                    title="Synthesize Research Dossier",
                    description="Synthesizing comparison matrix, pros/cons, and citation links",
                    action_type="SYNTHESIZE_DOSSIER",
                    payload={"query": query, "entities": entities}
                )
            ]

        # ─── 3. Proactive Recruiter Pipeline Plan ───
        elif goal_type == GoalType.RECRUITER_PIPELINE:
            steps = [
                TaskStep(
                    step_index=1,
                    title="Scan Recruiter Inbox",
                    description="Searching Gmail for active recruiter threads, interview invites, and OAs",
                    action_type="SCAN_GMAIL_PIPELINE",
                    payload={}
                ),
                TaskStep(
                    step_index=2,
                    title="Classify & Generate Drafts",
                    description="Categorizing threads into invites/assessments and tailoring response drafts",
                    action_type="GENERATE_PIPELINE_DRAFTS",
                    payload={}
                ),
                TaskStep(
                    step_index=3,
                    title="Present Batch Approval Queue",
                    description="Displaying multi-card triage queue for 1-click review and dispatch",
                    action_type="PRESENT_PIPELINE_QUEUE",
                    payload={"requires_approval": True}
                )
            ]

        # ─── 3.5. Email Campaign Plan ───
        elif goal_type == GoalType.EMAIL_CAMPAIGN:
            steps = [
                TaskStep(
                    step_index=1,
                    title="Extract Recipients & Roles",
                    description="Parsing email addresses, names, companies, and roles from prompt",
                    action_type="PARSE_RECIPIENTS",
                    payload=interpreted_goal
                ),
                TaskStep(
                    step_index=2,
                    title="Match Role-Specific Skills",
                    description="Selecting skill lines based on role type (ML/Backend/Frontend/General)",
                    action_type="MATCH_SKILLS",
                    payload={}
                ),
                TaskStep(
                    step_index=3,
                    title="Populate Email Templates",
                    description="Filling master template with personalized name, company, role, and skill lines",
                    action_type="POPULATE_TEMPLATE",
                    payload={}
                ),
                TaskStep(
                    step_index=4,
                    title="Campaign Preview for Approval",
                    description="Presenting all personalized email drafts for user review",
                    action_type="STAGING_HITL",
                    payload={"requires_approval": True}
                ),
                TaskStep(
                    step_index=5,
                    title="Schedule Campaign Jobs",
                    description="Enqueueing approved emails into the persistent job scheduler",
                    action_type="SCHEDULE_CAMPAIGN",
                    payload={}
                ),
                TaskStep(
                    step_index=6,
                    title="Execute & Track Delivery",
                    description="Background worker sends emails at scheduled time with rate limiting",
                    action_type="EXECUTE_CAMPAIGN",
                    payload={}
                )
            ]

        # ─── 4. Gmail Action Plan ───
        elif goal_type == GoalType.GMAIL_ACTION:
            action_kind = interpreted_goal.get("action_kind", "COMPOSE")
            recipient = interpreted_goal.get("recipient", "")
            steps = [
                TaskStep(
                    step_index=1,
                    title=f"Prepare {action_kind} Draft",
                    description=f"Drafting context-aware email for {recipient}",
                    action_type="PREPARE_EMAIL_DRAFT",
                    payload=interpreted_goal
                ),
                TaskStep(
                    step_index=2,
                    title="Human-in-the-Loop Approval",
                    description=f"Reviewing draft and attachments before sending",
                    action_type="STAGING_HITL",
                    payload={"requires_approval": True}
                ),
                TaskStep(
                    step_index=3,
                    title="Dispatch Live on Chrome",
                    description="Opening Gmail compose and clicking Send",
                    action_type="DISPATCH_EMAIL",
                    payload=interpreted_goal
                )
            ]

        # ─── 5. Universal Search Plan ───
        else:
            query = interpreted_goal.get("query", goal_text)
            steps = [
                TaskStep(
                    step_index=1,
                    title="Submit Google Search Query",
                    description=f"Navigating to Google Search for '{query}'",
                    action_type="EXECUTE_SEARCH",
                    payload={"query": query}
                ),
                TaskStep(
                    step_index=2,
                    title="Extract AI Overview & Top Sources",
                    description="Scraping featured snippets, key facts, and verified URLs",
                    action_type="EXTRACT_SEARCH_SUMMARY",
                    payload={"query": query}
                )
            ]

        return ExecutionPlan(
            goal_type=goal_type,
            goal_text=goal_text,
            steps=steps,
            requires_hitl=interpreted_goal.get("requires_hitl", False),
            status=StepStatus.PENDING,
            metadata=interpreted_goal
        )

planner = Planner()
