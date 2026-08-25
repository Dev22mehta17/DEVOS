import re
from typing import Dict, Any, List, Optional
from app.agent.agent_state import GoalType
import logging

logger = logging.getLogger(__name__)

# Word-boundary helper: checks if a keyword exists as a whole word (not substring)
def _has_word(text: str, word: str) -> bool:
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))

def _has_any_word(text: str, words: List[str]) -> bool:
    return any(_has_word(text, w) for w in words)

class GoalInterpreter:
    """Interprets freeform user prompts into structured Goal models and parameters."""

    @staticmethod
    def interpret(goal_text: str) -> Dict[str, Any]:
        text_clean = goal_text.strip()
        text_lower = text_clean.lower()

        # Split into real words for smarter matching
        words = set(re.findall(r'[a-z]+', text_lower))

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

        # ─── Case 2: Deep Research / Multi-Hop Comparison / Company Intel ───
        # Broad keyword set: catches "compare", "comparison", "comparision" (typo), "vs",
        # "difference between", "information about", "tell me about", "pros and cons", etc.
        deep_research_keywords = [
            "vs", "compare", "comparison", "comparision", "versus",
            "deep research", "dossier", "competitor", "pricing of",
            "pros and cons", "detailed research", "difference between",
            "tell me about", "information about", "everything about",
            "how to get job", "how to join", "research on", "intel on"
        ]
        is_deep_research = any(k in text_lower for k in deep_research_keywords)

        # Also trigger if the prompt mentions 2+ company/proper-noun-like entities with "and"
        # e.g. "Amazon and Apple for SDE", "Google and Microsoft comparison"
        if not is_deep_research:
            and_pattern = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+and\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text_clean)
            if and_pattern:
                # Two capitalized entities joined by "and" — likely a comparison/research query
                is_deep_research = True

        # Also trigger if starts with "research" or "compare"
        if not is_deep_research:
            if text_lower.startswith("research ") or text_lower.startswith("compare "):
                is_deep_research = True

        if is_deep_research:
            # Extract entities from patterns like "X vs Y", "X and Y", "compare X and Y"
            entities = []

            # Pattern 1: "X vs Y" or "X versus Y"
            if " vs " in text_lower or " versus " in text_lower:
                parts = re.split(r'\b(?:vs|versus)\b', text_clean, flags=re.IGNORECASE)
                entities = [p.strip().strip(",.") for p in parts if p.strip()]

            # Pattern 2: "X and Y" with capitalized proper nouns
            if not entities:
                and_match = re.search(r'(\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\s+and\s+(\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)', text_clean)
                if and_match:
                    entities = [and_match.group(1).strip(), and_match.group(2).strip()]

            # Clean entity names
            noise_words = ["research", "compare", "comparison", "deep", "about", "for", "sde", "fresher", "job", "information", "everything", "career", "hiring", "interview", "process", "salary", "difference", "between"]
            cleaned = []
            for e in entities:
                words_e = e.split()
                cleaned_words = [w for w in words_e if w.lower() not in noise_words]
                if cleaned_words:
                    cleaned.append(" ".join(cleaned_words))
            entities = cleaned if cleaned else entities

            return {
                "goal_type": GoalType.DEEP_RESEARCH,
                "action_kind": "MULTI_HOP_RESEARCH",
                "query": text_clean,
                "entities": entities[:2],
                "original_prompt": text_clean,
                "requires_hitl": False
            }

        # ─── Case 3: Proactive Recruiter Inbox Pipeline ───
        is_pipeline = any(k in text_lower for k in [
            "recruiter pipeline", "check recruiter", "all recruiter",
            "scan inbox", "triage recruiter", "recruiter queue",
            "pending recruiter", "triage my response"
        ])
        if is_pipeline:
            return {
                "goal_type": GoalType.RECRUITER_PIPELINE,
                "action_kind": "TRIAGE_RECRUITERS",
                "original_prompt": text_clean,
                "requires_hitl": True
            }
        # ─── Case 3.5: Email Campaign (Bulk Personalized Outreach) ───
        # Detect: multiple email addresses, or campaign keywords + email context
        email_addresses = re.findall(r'[\w\.\-\+]+@[\w\.\-]+\.\w+', text_clean)
        campaign_keywords = [
            "send to all", "send to these", "send each", "send intro to",
            "bulk email", "email campaign", "mail all", "send introduction",
            "send my intro", "mail to all", "mail these", "personalize",
            "send to the following", "send to following", "send emails to"
        ]
        is_campaign = (
            len(email_addresses) >= 2 or
            any(k in text_lower for k in campaign_keywords)
        )
        if is_campaign:
            return {
                "goal_type": GoalType.EMAIL_CAMPAIGN,
                "action_kind": "BULK_CAMPAIGN",
                "recipients_raw": email_addresses,
                "original_prompt": text_clean,
                "requires_hitl": True
            }

        # ─── Case 4: Gmail Single Action (Reply / Forward / Compose) ───
        if _has_any_word(text_lower, ["email", "mail", "gmail", "inbox", "recruiter", "hr"]):
            action_kind = "COMPOSE"
            search_query = ""

            if _has_any_word(text_lower, ["reply", "respond"]) or "answer to" in text_lower:
                action_kind = "REPLY"
                if _has_word(text_lower, "from"):
                    search_query = text_clean.split("from")[-1].split("and")[0].strip()
                elif "about" in text_lower:
                    search_query = text_clean.split("about")[-1].strip()
                else:
                    search_query = "recruiter"

            elif _has_any_word(text_lower, ["forward", "fwd"]):
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
                "attach_resume": _has_any_word(text_lower, ["resume", "cv", "pdf", "attach"]),
                "original_prompt": text_clean,
                "requires_hitl": True
            }

        # ─── Case 5: Job / Form without direct URL in text ───
        # IMPORTANT: Use word-boundary matching so "information" doesn't match "form"
        # and "front" doesn't match "from"
        form_keywords = ["form", "apply", "register", "signup", "sign up", "book", "application"]
        if _has_any_word(text_lower, form_keywords):
            return {
                "goal_type": GoalType.JOB_APPLICATION,
                "action_kind": "URL_REQUIRED",
                "target_url": None,
                "original_prompt": text_clean,
                "requires_hitl": False
            }

        # ─── Case 6: Universal Web Search & Direct Answer ───
        clean_query = text_clean
        for strip_phrase in ["search for", "search", "find out", "look up"]:
            clean_query = clean_query.replace(strip_phrase, "").strip()
        return {
            "goal_type": GoalType.WEB_SEARCH,
            "action_kind": "WEB_SEARCH",
            "query": clean_query or text_clean,
            "original_prompt": text_clean,
            "requires_hitl": False
        }

goal_interpreter = GoalInterpreter()

