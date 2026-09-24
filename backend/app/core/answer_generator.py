import os
import re
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from app.core.memory_engine import memory_engine

logger = logging.getLogger(__name__)

KNOWN_COMPANIES = {
    "microsoft": {
        "name": "Microsoft",
        "focus": "cloud infrastructure (Azure), developer tools, TypeScript, scalable enterprise software, and OpenAI/Copilot integration.",
        "why": "I am deeply inspired by Microsoft's mission of empowering every developer and enterprise to achieve more. Given my strong background in backend systems, Python, and TypeScript/JavaScript, I am thrilled by the scale of Azure cloud services and developer tooling."
    },
    "amazon": {
        "name": "Amazon",
        "focus": "high-scale distributed systems, AWS cloud primitives, customer obsession, and microservice architectures.",
        "why": "Having worked as an SDE Intern at Amazon building scalable cloud microservices, I have firsthand experience with Amazon's culture of ownership and customer obsession. I am eager to continue engineering mission-critical backend systems at Amazon scale."
    },
    "google": {
        "name": "Google",
        "focus": "world-class engineering standards, distributed systems (Spanner, Bigtable, Borg), search/information retrieval, and cutting-edge AI.",
        "why": "Google's culture of technical excellence and massive-scale distributed infrastructure has always been the standard for engineering. My background in systems engineering and autonomous agents makes me eager to tackle complex algorithmic and backend challenges at Google."
    },
    "meta": {
        "name": "Meta",
        "focus": "open-source engineering (React, PyTorch), ultra-high-throughput backend architectures, and AI innovation.",
        "why": "Meta's fast-paced engineering culture and foundational contributions to open source (like React and PyTorch) deeply resonate with me. I love building systems with high engineering velocity and massive user reach."
    },
    "apple": {
        "name": "Apple",
        "focus": "seamless user experience, privacy, high-performance systems engineering, and hardware-software synergy.",
        "why": "Apple's relentless commitment to craft, privacy, and performance aligns with my standard for building reliable, polished software systems."
    },
    "netflix": {
        "name": "Netflix",
        "focus": "high-availability distributed streaming architecture, Chaos Engineering, and culture of freedom and responsibility.",
        "why": "Netflix's pioneering work in distributed systems resilience and microservices architecture is a benchmark for backend engineers. I thrive in high-trust, high-ownership engineering environments."
    },
    "uber": {
        "name": "Uber",
        "focus": "real-time marketplace matching, distributed geo-spatial routing, high concurrency, and event-driven architecture.",
        "why": "Uber's real-time matching algorithms and high-throughput event processing present some of the most exciting distributed systems challenges in tech."
    },
    "stripe": {
        "name": "Stripe",
        "focus": "financial infrastructure, developer-first API design, high-availability transactions, and reliability.",
        "why": "Stripe's exceptional API ergonomics and 99.999% availability standards inspire my approach to backend engineering and API design."
    }
}


class AnswerGenerator:
    """Generates personalized, high-quality answers for open-ended job/form questions."""

    @staticmethod
    def extract_company_or_topic(text: str, context_hints: str = "") -> Optional[Dict[str, str]]:
        combined = f"{text} {context_hints}".lower()
        for key, info in KNOWN_COMPANIES.items():
            if key in combined:
                return info
        
        # Generic company extraction via regex (e.g. "join XYZ", "work at XYZ", "at XYZ")
        match = re.search(r'(?:join|work at|work for|at|role at)\s+([A-Z][a-zA-Z0-9_\-\.\&]+)', f"{text} {context_hints}")
        if match:
            c_name = match.group(1).strip()
            if c_name.lower() not in ["us", "this", "our", "a", "the", "an", "here"]:
                return {
                    "name": c_name,
                    "focus": f"innovative technology, industry leadership, and solving impactful problems.",
                    "why": f"I am deeply excited about {c_name}'s technical mission, engineering impact, and the opportunity to build scalable software that serves a broad user base."
                }
        return None

    @classmethod
    def generate_answer(cls, question: str, context_hints: str = "", max_words: int = 150) -> Dict[str, Any]:
        """Synthesizes a tailored, personalized answer using Gemini API or intelligent semantic synthesis."""
        company_info = cls.extract_company_or_topic(question, context_hints)
        
        # 1. Retrieve relevant vector memory snippets from ChromaDB
        relevant_chunks = memory_engine.query_semantic_memory(question, top_k=4)
        profile_summary = memory_engine.get_full_candidate_summary()
        extra_ctx = memory_engine.get_extra_context()
        
        # 2. Check for Gemini API key
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                llm_ans = cls._call_gemini_api(api_key, question, profile_summary, relevant_chunks, company_info, extra_ctx, max_words)
                if llm_ans:
                    return {
                        "answer": llm_ans,
                        "source": "GEMINI_2.0_FLASH",
                        "company": company_info["name"] if company_info else None,
                        "confidence": "high"
                    }
            except Exception as e:
                logger.warning(f"[AnswerGenerator] Gemini API call failed: {e}. Falling back to semantic synthesis.")

        # 3. Intelligent Local Semantic Synthesis Engine
        synth_ans = cls._synthesize_locally(question, profile_summary, relevant_chunks, company_info, extra_ctx, max_words)
        return {
            "answer": synth_ans,
            "source": "SEMANTIC_SYNTHESIS",
            "company": company_info["name"] if company_info else None,
            "confidence": "high" if company_info or relevant_chunks else "medium"
        }

    @classmethod
    def _call_gemini_api(cls, api_key: str, question: str, profile_summary: str, relevant_chunks: List[str], company_info: Optional[Dict[str, str]], extra_ctx: Dict[str, Any], max_words: int) -> Optional[str]:
        """Calls Google Gemini REST API directly."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        company_prompt = ""
        if company_info:
            company_prompt = f"Target Company: {company_info['name']}\nCompany Focus: {company_info['focus']}\n"

        prompt = f"""You are Dev Mehta, an engineering candidate filling out a job application.
Answer the following application question in first-person ("I", "my") with a confident, articulate, authentic, and professional tone.

Candidate Background:
{profile_summary}

Relevant Achievements & Resume Excerpts:
{chr(10).join(relevant_chunks)}

{company_prompt}

Question: "{question}"

Instructions:
- READ THE QUESTION CAREFULLY. Answer EXACTLY what is being asked. Do not give a generic "why I want to join" answer for every question.
- If the question asks about "reason for job change/leaving", explain that you completed your Amazon internship and are now a final-year student seeking full-time roles.
- If the question asks "why join [company]", then tailor your answer to that specific company.
- If the question asks about a "challenge" or "project", describe a specific technical project.
- If the question asks about "strengths/weaknesses", give genuine self-aware answers.
- If the question asks about "salary/compensation", say you are flexible and open to industry-standard packages.
- If the question asks about "availability/notice period", say you can start immediately.
- Highlight relevant experience only when it naturally answers the question.
- Keep length around {max_words} words.
- Do not use markdown headers or generic fluff; return ONLY the response text ready to paste into a form.
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 400
            }
        }

        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                if content:
                    return content
        else:
            logger.warning(f"[AnswerGenerator] Gemini HTTP error: {resp.status_code} - {resp.text}")
        return None

    @classmethod
    def _synthesize_locally(cls, question: str, profile_summary: str, relevant_chunks: List[str], company_info: Optional[Dict[str, str]], extra_ctx: Dict[str, Any], max_words: int) -> str:
        """Local high-intelligence synthesis combining structured profile, vector chunks, and company context."""
        q_lower = question.lower()
        
        prof = memory_engine.profile_data.get("professional", {})
        edu = memory_engine.profile_data.get("education", {})
        role = prof.get("current_role", "Software Engineer")
        skills = ", ".join(prof.get("skills", ["Python", "FastAPI", "React", "Playwright", "Distributed Systems"])[:5])
        uni = edu.get("university", "Thapar Institute of Engineering & Technology")
        comp_name = company_info["name"] if company_info else "your organization"
        
        # 1. "Why didn't you get PPO" / "Internship full-time conversion / offer"
        if any(k in q_lower for k in ["ppo", "return offer", "conversion", "why didn't you get", "why not join amazon"]):
            return "During my 6-month SDE internship at Amazon Pay, I had a very rewarding stint delivering production microservices and optimizing customer-facing payment platforms. Headcount allocations for full-time return offers were constrained across our business unit for the 2026 fresher batch due to organizational headcount limits. However, I earned strong feedback from my manager and mentors for technical ownership, code quality, and rapid delivery, and I am now actively seeking full-time SDE-1 roles where I can leverage my distributed systems experience."

        # 2. "Proudest thing in your internship / Achievement"
        if any(k in q_lower for k in ["proud", "proudest", "did in your internship", "internship achievement", "best achievement"]):
            return "The proudest achievement during my Amazon SDE internship was engineering and optimizing high-throughput backend services that directly improved payment transaction reliability. I took end-to-end ownership of identifying latency bottlenecks, resolving distributed race conditions, and delivering a customer-facing feature ahead of schedule with comprehensive test coverage and zero production regressions."

        # 3. "Reason for job change / leaving / looking for new opportunity"
        if any(k in q_lower for k in ["reason for looking", "job change", "reason for change", "leaving current", "why leaving",
                                       "reason for leaving", "looking for a change", "switching", "reason for job"]):
            return f"I recently completed a 6-month SDE internship at Amazon where I gained valuable production engineering experience with distributed microservices and cloud infrastructure. As a final-year Computer Engineering student at {uni} graduating in 2026, I am actively seeking full-time SDE roles to apply and grow my skills in backend systems, scalable APIs, and cloud architecture. I am looking for a role that offers strong engineering challenges and mentorship in a high-ownership environment."

        # 4. "Why join [Company]" / "Why do you want to work here"
        if any(k in q_lower for k in ["why do you want to join", "why do you want to work", "why this company",
                                       "why us", "why work here", "what excites you about",
                                       "what attracts you", "why are you interested in this"]):
            if company_info:
                return f"{company_info['why']} As a Computer Engineering student at {uni} and former SDE Intern at Amazon, I bring hands-on experience with scalable backend systems, cloud microservices, and autonomous agent engineering using {skills}. I am eager to contribute my technical ownership and problem-solving skills to {comp_name}'s engineering team."
            else:
                return f"I am excited about this opportunity because of your team's focus on engineering excellence and solving impactful problems at scale. My experience as an SDE Intern at Amazon building cloud microservices, combined with my Computer Engineering studies at {uni}, has prepared me to contribute meaningfully to your engineering team using {skills}."

        # 5. "Tell us about a challenging problem / project / bug"
        if any(k in q_lower for k in ["challenging", "challenge", "difficult", "hardest problem", "complex project", "bug you fixed", "tough situation"]):
            return f"During my engineering work, one of the most challenging projects was architecting the DevOS autonomous execution engine to control browser sessions via Chrome DevTools Protocol with real-time SSE streaming. The core challenge was handling asynchronous DOM rendering states and complex multi-frame interactions reliably. I implemented resilient state-synchronization protocols and fallback keyboard automation in Python and Playwright, achieving seamless sub-second automation. This strengthened my ability to diagnose distributed race conditions and build resilient systems."

        # 6. "Tell us about yourself / Walk through your resume / Background"
        if any(k in q_lower for k in ["about yourself", "background", "introduce", "summary", "walk us through", "tell us about you", "describe yourself"]):
            return f"I am a passionate Software Engineer and Computer Engineering student at {uni} graduating in 2026. I worked as an SDE Intern at Amazon, where I engineered scalable cloud microservices and optimized backend API latencies. My core technical strengths include {skills}. I am a hands-on builder with strong ownership who loves solving complex technical problems."

        # 7. "Why should we hire you / What sets you apart"
        if any(k in q_lower for k in ["hire you", "why you", "sets you apart", "what makes you unique", "fit for this role", "stand out"]):
            return f"What sets me apart is my strong combination of algorithmic foundation, hands-on production experience from my Amazon SDE internship, and a bias for rapid execution. I have architected full-stack systems from scratch using {skills} and possess a deep curiosity for high-scale backend engineering. I ramp up quickly, take end-to-end ownership, and deliver robust solutions."

        # 8. Strengths / Weaknesses
        if any(k in q_lower for k in ["strength", "weakness", "strong suit", "area of improvement"]):
            if "weakness" in q_lower or "improvement" in q_lower:
                return "One area I am actively improving is delegation. As someone who takes deep ownership of technical problems, I sometimes try to solve everything myself rather than leveraging team collaboration early. I have been working on this by proactively seeking code reviews and pair programming to produce better solutions faster."
            else:
                return f"My key strengths are technical problem-solving, rapid learning, and taking end-to-end ownership of engineering challenges. During my Amazon SDE internship, I delivered production-grade microservices with comprehensive testing and zero regressions. I am proficient in {skills} and thrive in fast-paced environments."

        # 9. Interest / motivation / passion (generic)
        if any(k in q_lower for k in ["interest in", "motivation", "passion for", "what drives you", "what inspires"]):
            return f"I am deeply motivated by building software that solves real problems at scale. My passion for backend engineering and distributed systems was cemented during my Amazon SDE internship, where I saw firsthand how well-architected services handle millions of transactions reliably. I want to continue building systems with high engineering standards, strong ownership, and measurable user impact."

        # 10. Cover letter / general "why" (broad catch-all, but not as greedy)
        if any(k in q_lower for k in ["cover letter", "letter of interest", "why apply", "reason for applying"]):
            if company_info:
                return f"I am applying because {company_info['why']} With my hands-on experience as an SDE Intern at Amazon and my Computer Engineering degree from {uni}, I bring production-grade skills in {skills}. I am eager to contribute to {comp_name}'s mission and grow as a software engineer in a high-impact environment."
            else:
                return f"I am applying for this role because it aligns closely with my skills and career goals as a software engineer. My experience at Amazon building scalable cloud microservices, combined with my technical foundation in {skills} from {uni}, positions me well to contribute meaningfully from day one."

        # 11. Availability / start date / notice period
        if any(k in q_lower for k in ["availability", "when can you start", "start date", "earliest date", "notice period", "immediate"]):
            notice = prof.get("notice_period", "Immediate")
            return f"I am available to start {notice.lower()}. As a final-year student at {uni} graduating in 2026, I have full flexibility for immediate joining."

        # 12. Salary / compensation expectations
        if any(k in q_lower for k in ["salary", "compensation", "ctc", "pay expectation", "remuneration"]):
            return "I am flexible on compensation and open to discussing a package that is competitive and in line with industry standards for a fresh SDE-1 / entry-level software engineering role. My primary focus is on the technical challenge, growth opportunity, and engineering culture."

        # 13. Generic fallback leveraging vector context
        if relevant_chunks:
            context_text = " ".join([c.strip() for c in relevant_chunks[:2]])
            return f"Based on my engineering background at Amazon and {uni}: {context_text}"

        return f"As a Software Engineer with experience at Amazon and a strong foundation in {skills} from {uni}, I bring strong technical problem-solving, high ownership, and a proven track record of building reliable software systems."


answer_generator = AnswerGenerator()
