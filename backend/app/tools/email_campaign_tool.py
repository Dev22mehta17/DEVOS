import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.core.memory_engine import memory_engine
from app.core.answer_generator import answer_generator

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────
# ROLE-SPECIFIC SKILL LINES (tailored to role)
# ──────────────────────────────────────────────────
SKILL_PROFILES = {
    "ml_ai": {
        "keywords": ["ml", "machine learning", "ai", "artificial intelligence", "data science",
                     "deep learning", "nlp", "computer vision", "llm", "neural", "tensorflow",
                     "pytorch", "model", "genai", "gen ai"],
        "skill_lines": (
            "I have hands-on experience with Python, TensorFlow, PyTorch, and building ML pipelines, "
            "with a solid foundation in DSA, mathematics, statistics, and algorithm design."
        ),
        "relevant_skills": "Python, TensorFlow, PyTorch, Machine Learning, Data Pipelines"
    },
    "backend": {
        "keywords": ["backend", "back-end", "server", "api", "microservices", "distributed",
                     "java", "spring", "django", "flask", "fastapi", "node", "golang", "go",
                     "rest", "grpc", "kafka", "redis", "database", "sde-1", "sde 1"],
        "skill_lines": (
            "I have strong proficiency in Java, Python, REST APIs, and building scalable backend microservices, "
            "along with hands-on experience in database optimization, distributed systems, and system design."
        ),
        "relevant_skills": "Java, Python, Microservices, REST APIs, Distributed Systems"
    },
    "frontend": {
        "keywords": ["frontend", "front-end", "react", "angular", "vue", "ui", "ux",
                     "javascript", "typescript", "css", "html", "web developer", "nextjs", "next.js"],
        "skill_lines": (
            "I have hands-on experience with React, TypeScript, modern frontend frameworks, and responsive UI design, "
            "along with expertise in state management and building performant user interfaces."
        ),
        "relevant_skills": "React, TypeScript, JavaScript, HTML/CSS, UI/UX"
    },
    "devops_cloud": {
        "keywords": ["devops", "cloud", "aws", "azure", "gcp", "docker", "kubernetes", "k8s",
                     "ci/cd", "terraform", "infrastructure", "sre", "site reliability"],
        "skill_lines": (
            "I have hands-on experience with Docker, AWS, CI/CD pipeline design, and cloud-native architectures, "
            "with deep familiarity with infrastructure automation and operational excellence."
        ),
        "relevant_skills": "Docker, AWS, CI/CD, Kubernetes, Infrastructure"
    },
    "fullstack": {
        "keywords": ["full stack", "fullstack", "full-stack", "mern", "mean"],
        "skill_lines": (
            "I have hands-on experience across the full stack with React, Node.js, Python, and SQL/NoSQL databases, "
            "along with experience building end-to-end production features spanning both client UIs and backend microservices."
        ),
        "relevant_skills": "React, Python, Node.js, PostgreSQL, Full-Stack"
    },
    "general_sde": {
        "keywords": [],  # fallback
        "skill_lines": (
            "I have a strong foundation in C++, Java, Python, DSA, OOP, DBMS, and Computer Networks, "
            "along with experience building full-stack projects."
        ),
        "relevant_skills": "C++, Java, Python, DSA, OOP, DBMS, Networks"
    }
}


# ──────────────────────────────────────────────────
# MASTER EMAIL TEMPLATE (Dev Mehta's Proven Format)
# ──────────────────────────────────────────────────
MASTER_TEMPLATE = """Hi {{name}},

I hope you're doing well.

I'm Dev Mehta, a Computer Engineering graduate from Thapar Institute of Engineering & Technology, and I recently completed a 6-month Software Development Engineer internship at Amazon Pay India.

During my internship, I worked on production backend and customer-facing systems, including a multi-marketplace runtime configuration migration and payment-related features using Java, runtime configuration, and feature flagging. I also worked on debugging distributed-system issues and contributed to design documents, code reviews, and operational dashboards.

I'm reaching out to explore {{role}} opportunities at {{company}}. {{skill_lines}}

I would really appreciate it if you could consider my profile for any relevant current or upcoming openings at {{company}}.

I've attached my resume for your consideration and would be happy to discuss my profile further.

Thank you for your time.

Best regards,
Dev Mehta
{{contact_block}}"""


class EmailCampaignTool:
    """Bulk email campaign engine with deterministic templates and role-specific skill matching."""

    def __init__(self):
        self._personalization_cache = {}  # company -> personalized_line

    # ───────────────────────────────────────
    # 1. RECIPIENT PARSER
    # ───────────────────────────────────────
    @staticmethod
    def parse_recipients(goal_text: str) -> List[Dict[str, str]]:
        """Extract recipient list from the user's prompt.

        Supports formats:
          - ananya@atlys.com (AI Engineer at Atlys)
          - rahul@microsoft.com, name: Rahul, role: SDE
          - name@company.com
          - Bare emails with company inferred from domain
        """
        recipients = []
        text = goal_text

        # Pattern 1: "email (Role at Company)" or "email - Role at Company"
        # e.g. ananya@atlys.com (AI Engineer at Atlys)
        pattern_rich = re.finditer(
            r'([\w\.\-\+]+@[\w\.\-]+\.\w+)\s*[\(\-–—]\s*([^)@\n]+?)\s*(?:at|@)\s*([^)@,\n]+?)[\)\-–—]?(?:\s*,|\s*$|\s+)',
            text, re.IGNORECASE
        )
        found_emails = set()
        for m in pattern_rich:
            email = m.group(1).strip()
            role = m.group(2).strip().rstrip(',.')
            company = m.group(3).strip().rstrip(',.')
            name_guess = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
            recipients.append({
                "email": email,
                "name": name_guess,
                "company": company,
                "role": role
            })
            found_emails.add(email.lower())

        # Pattern 2: Bare emails — infer company from domain
        bare_emails = re.findall(r'[\w\.\-\+]+@[\w\.\-]+\.\w+', text)
        for email in bare_emails:
            if email.lower() not in found_emails:
                domain = email.split('@')[1].split('.')[0].title()
                name_guess = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                recipients.append({
                    "email": email,
                    "name": name_guess,
                    "company": domain,
                    "role": "Software Development Engineer"
                })
                found_emails.add(email.lower())

        return recipients

    # ───────────────────────────────────────
    # 2. SKILL LINE MATCHER (deterministic)
    # ───────────────────────────────────────
    @staticmethod
    def match_skill_lines(role: str) -> Dict[str, str]:
        """Match 2-3 skill-specific lines based on the role keywords.

        Returns {"skill_lines": "...", "relevant_skills": "..."}
        """
        role_lower = role.lower() if role else ""

        best_profile = "general_sde"
        best_score = 0

        for profile_key, profile_data in SKILL_PROFILES.items():
            if profile_key == "general_sde":
                continue
            score = sum(1 for kw in profile_data["keywords"] if kw in role_lower)
            if score > best_score:
                best_score = score
                best_profile = profile_key

        matched = SKILL_PROFILES[best_profile]
        logger.info(f"[Campaign] Role '{role}' matched skill profile: {best_profile}")
        return {
            "skill_lines": matched["skill_lines"],
            "relevant_skills": matched["relevant_skills"],
            "profile_key": best_profile
        }

    # ───────────────────────────────────────
    # 3. TEMPLATE POPULATION
    # ───────────────────────────────────────
    @staticmethod
    def populate_template(recipient: Dict[str, str], template: str = None) -> Dict[str, str]:
        """Fill {{variables}} in the master template with recipient data.

        Returns {"subject": "...", "body": "..."}
        """
        tmpl = template or MASTER_TEMPLATE
        name = recipient.get("name", "Hiring Team")
        company = recipient.get("company", "your company")
        role = recipient.get("role", "Software Engineer")
        email = recipient.get("email", "")

        # Get role-specific skill lines
        skill_match = EmailCampaignTool.match_skill_lines(role)

        # Build contact block dynamically from profile.json
        p = memory_engine.profile_data
        contact_lines = []
        user_email = p.get("personal", {}).get("email_primary", "mehtadev2004@gmail.com")
        user_phone = p.get("personal", {}).get("phone", "")
        github_url = p.get("links", {}).get("github", "")
        linkedin_url = p.get("links", {}).get("linkedin", "")
        portfolio_url = p.get("links", {}).get("portfolio", "")

        if user_email:
            contact_lines.append(f"📧 {user_email}")
        if user_phone:
            contact_lines.append(f"📱 {user_phone}")
        if linkedin_url:
            contact_lines.append(f"🔗 LinkedIn: {linkedin_url}")
        if github_url:
            contact_lines.append(f"💻 GitHub: {github_url}")
        if portfolio_url:
            contact_lines.append(f"🌐 Portfolio: {portfolio_url}")

        contact_block = "\n".join(contact_lines)

        body = tmpl.replace("{{name}}", name)
        body = body.replace("{{company}}", company)
        body = body.replace("{{role}}", role)
        body = body.replace("{{skill_lines}}", skill_match["skill_lines"])
        body = body.replace("{{relevant_skills}}", skill_match["relevant_skills"])
        body = body.replace("{{contact_block}}", contact_block)

        # Remove any leftover template vars
        body = re.sub(r'\{\{[^}]+\}\}', '', body)

        subject = f"Application for {role} – Dev Mehta"

        return {
            "email": email,
            "name": name,
            "company": company,
            "role": role,
            "subject": subject,
            "body": body.strip(),
            "skill_profile": skill_match["profile_key"],
            "relevant_skills": skill_match["relevant_skills"]
        }

    # ───────────────────────────────────────
    # 4. SCHEDULE TIME PARSER
    # ───────────────────────────────────────
    @staticmethod
    def parse_schedule_time(goal_text: str) -> Optional[datetime]:
        """Parse schedule time from natural language.

        Handles: 'tomorrow at 10 AM', 'Aug 27 at 3 PM', 'in 2 hours',
                 'tonight at 9', 'today at 5 PM', specific dates.
        Returns None if no schedule time found (= send immediately).
        """
        text_lower = goal_text.lower()
        now = datetime.now()

        # Pattern: "in X hours/minutes"
        m = re.search(r'in\s+(\d+)\s*(hour|hr|minute|min)s?', text_lower)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            if 'hour' in unit or 'hr' in unit:
                return now + timedelta(hours=amount)
            else:
                return now + timedelta(minutes=amount)

        # Pattern: "tomorrow at HH:MM AM/PM" or "tomorrow at H AM/PM" or "tomorrow at 4.21 PM"
        m = re.search(r'tomorrow\s+(?:at\s+)?(\d{1,2})(?:[:\.](\d{2}))?\s*(am|pm)?', text_lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            ampm = m.group(3)
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Pattern: "today at HH AM/PM" or "tonight at H" or "today at 4.21 PM"
        m = re.search(r'(?:today|tonight)\s+(?:at\s+)?(\d{1,2})(?:[:\.](\d{2}))?\s*(am|pm)?', text_lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            ampm = m.group(3)
            if 'tonight' in text_lower and not ampm:
                ampm = 'pm'
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Pattern: "Aug 27 at 3 PM" or "August 27 at 10 AM" or "27 Aug at 3 PM"
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        m = re.search(
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)'
            r'\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            text_lower
        )
        if not m:
            m = re.search(
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)'
                r'\s+(\d{1,2})\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
                text_lower
            )
            if m:
                month_str, day_str, hour_str, min_str, ampm = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                month = months.get(month_str, now.month)
                day = int(day_str)
                hour = int(hour_str)
                minute = int(min_str or 0)
                if ampm == 'pm' and hour < 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                year = now.year if month >= now.month else now.year + 1
                return datetime(year, month, day, hour, minute, 0)
        elif m:
            day_str, month_str, hour_str, min_str, ampm = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            month = months.get(month_str, now.month)
            day = int(day_str)
            hour = int(hour_str)
            minute = int(min_str or 0)
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            year = now.year if month >= now.month else now.year + 1
            return datetime(year, month, day, hour, minute, 0)

        # Pattern: bare time "at 4.21 PM" or "4:30 pm" or "4.21PM" (no today/tomorrow prefix)
        m = re.search(r'(?:at\s+)?(\d{1,2})[:\.](\d{2})\s*(am|pm)', text_lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
            ampm = m.group(3)
            if ampm == 'pm' and hour < 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If time is already past, schedule for tomorrow
            if target <= now:
                target += timedelta(days=1)
            return target

        return None

    # ───────────────────────────────────────
    # 5. PREPARE FULL CAMPAIGN
    # ───────────────────────────────────────
    async def prepare_campaign(
        self,
        goal_text: str,
        recipients: List[Dict[str, str]] = None,
        custom_template: str = None
    ) -> Dict[str, Any]:
        """Orchestrates full campaign preparation.

        1. Parse recipients from goal text (if not provided)
        2. Parse schedule time
        3. For each recipient: populate template with role-specific skill lines
        4. Return preview data for frontend
        """
        campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"

        # Parse recipients
        if not recipients:
            recipients = self.parse_recipients(goal_text)

        if not recipients:
            return {
                "status": "NO_RECIPIENTS",
                "message": "No recipient email addresses found in your message. Please provide emails like: ananya@atlys.com (AI Engineer at Atlys)"
            }

        # Parse schedule time
        schedule_time = self.parse_schedule_time(goal_text)

        # Get resume path
        resume_path = (
            memory_engine.profile_data.get("documents", {}).get("active_resume_path")
            or None
        )

        # Build personalized drafts
        drafts = []
        for i, recipient in enumerate(recipients):
            populated = self.populate_template(recipient, custom_template)
            drafts.append({
                "draft_index": i,
                "email": populated["email"],
                "name": populated["name"],
                "company": populated["company"],
                "role": populated["role"],
                "subject": populated["subject"],
                "body": populated["body"],
                "skill_profile": populated["skill_profile"],
                "relevant_skills": populated["relevant_skills"],
                "attached_file": resume_path
            })

        campaign_data = {
            "campaign_id": campaign_id,
            "action_id": campaign_id,
            "total_recipients": len(drafts),
            "drafts": drafts,
            "schedule_time": schedule_time.isoformat() if schedule_time else None,
            "schedule_display": (
                schedule_time.strftime("%b %d, %I:%M %p") if schedule_time
                else "Send immediately after approval"
            ),
            "attach_resume": bool(resume_path),
            "resume_filename": resume_path.split('/')[-1] if resume_path else None,
            "status": "PREVIEW_READY"
        }

        logger.info(
            f"[Campaign] Prepared {len(drafts)} personalized drafts for campaign {campaign_id}. "
            f"Schedule: {campaign_data['schedule_display']}"
        )

        return campaign_data


email_campaign_tool = EmailCampaignTool()
