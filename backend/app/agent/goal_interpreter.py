import re
from typing import Dict, Any, List, Optional
from app.agent.agent_state import GoalType
import logging

logger = logging.getLogger(__name__)

class GoalInterpreter:
    """Interprets freeform user prompts into structured Goal models and parameters."""

    @staticmethod
    def interpret(goal_text: str) -> Dict[str, Any]:
        text_clean = goal_text.strip()
        text_lower = text_clean.lower()

        # 1. Extract URL if present
        url_match = re.search(r'https?://[^\s\'"<>]+', text_clean)
        target_url = url_match.group(0).strip(".,'\"") if url_match else None

        # 2. Extract Email if present
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text_clean)
        email_recipient = email_match.group(0) if email_match else None

        # ─── Case 1: Direct Web / Job Application URL ───
        if target_url and not any(k in text_lower for k in ["search google for", "google search"]):
            portal_kind = "google_form" if ("docs.google.com/forms" in target_url or "forms.gle" in target_url) else "web_portal"
            return {
                "goal_type": GoalType.JOB_APPLICATION,
                "action_kind": "APPLY_JOB",
                "target_url": target_url,
                "portal_kind": portal_kind,
                "attach_resume": "resume" in text_lower or "cv" in text_lower or True,
                "original_prompt": text_clean,
                "requires_hitl": True
            }

        # ─── Case 2: Deep Research / Multi-Hop Comparison ───
        # e.g., "Research Stripe vs Razorpay pricing", "Compare X and Y", "Deep research on NVIDIA"
        is_deep_research = (
            any(k in text_lower for k in ["vs", "compare", "versus", "deep research", "dossier", "competitor", "pricing of", "pros and cons", "detailed research"]) or
            (text_lower.startswith("research ") and len(text_lower.split()) > 2)
        )
        if is_deep_research:
            # Extract entities (e.g. "Stripe vs Razorpay", "NVIDIA AI")
            entities = []
            if " vs " in text_lower or " versus " in text_lower or " compare " in text_lower:
                parts = re.split(r'\b(?:vs|versus|compare|and)\b', text_clean, flags=re.IGNORECASE)
                entities = [p.replace("Research", "").replace("research", "").strip() for p in parts if p.strip()]

            return {
                "goal_type": GoalType.DEEP_RESEARCH,
                "action_kind": "MULTI_HOP_RESEARCH",
                "query": text_clean,
                "entities": entities,
                "original_prompt": text_clean,
                "requires_hitl": False
            }

        # ─── Case 3: Proactive Recruiter Inbox Pipeline ───
        # e.g., "Check recruiter emails", "Recruiter pipeline", "Reply to all recruiters", "Scan inbox for recruiters"
        is_pipeline = any(k in text_lower for k in ["recruiter pipeline", "check recruiter", "all recruiter", "scan inbox", "triage recruiter", "recruiter queue", "pending recruiter"])
        if is_pipeline:
            return {
                "goal_type": GoalType.RECRUITER_PIPELINE,
                "action_kind": "TRIAGE_RECRUITERS",
                "original_prompt": text_clean,
                "requires_hitl": True
            }

        # ─── Case 4: Gmail Single Action (Reply / Forward / Compose) ───
        if any(k in text_lower for k in ["email", "mail", "gmail", "inbox", "recruiter", "hr"]):
            action_kind = "COMPOSE"
            search_query = ""

            if any(k in text_lower for k in ["reply", "respond", "answer to"]):
                action_kind = "REPLY"
                if "from" in text_lower:
                    search_query = text_clean.split("from")[-1].split("and")[0].strip()
                elif "about" in text_lower:
                    search_query = text_clean.split("about")[-1].strip()
                else:
                    search_query = "recruiter"

            elif any(k in text_lower for k in ["forward", "fwd"]):
                action_kind = "FORWARD"
                if "about" in text_lower:
                    search_query = text_clean.split("about")[-1].split("to")[0].strip()
                else:
                    search_query = "interview"

            return {
                "goal_type": GoalType.GMAIL_ACTION,
                "action_kind": action_kind,
                "recipient": email_recipient or "mehtadev2004@gmail.com",
                "search_query": search_query,
                "attach_resume": any(k in text_lower for k in ["resume", "cv", "pdf", "attach"]),
                "original_prompt": text_clean,
                "requires_hitl": True
            }

        # ─── Case 5: Job / Form without direct URL in text ───
        if any(k in text_lower for k in ["form", "from", "apply", "register", "signup", "sign up", "book", "application"]):
            return {
                "goal_type": GoalType.JOB_APPLICATION,
                "action_kind": "URL_REQUIRED",
                "target_url": None,
                "original_prompt": text_clean,
                "requires_hitl": False
            }

        # ─── Case 6: Universal Web Search & Direct Answer ───
        clean_query = text_clean.replace("search for", "").replace("search", "").replace("find out", "").replace("who is", "who is").strip()
        return {
            "goal_type": GoalType.WEB_SEARCH,
            "action_kind": "WEB_SEARCH",
            "query": clean_query or text_clean,
            "original_prompt": text_clean,
            "requires_hitl": False
        }

goal_interpreter = GoalInterpreter()
