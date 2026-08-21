import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

PROFILE_PATH = Path(__file__).parent.parent / "models" / "profile.json"

class MemoryEngine:
    def __init__(self, profile_file: Path = PROFILE_PATH):
        self.profile_file = profile_file
        self.profile_data: Dict[str, Any] = self._load_profile()
        self._init_vector_db()

    def _load_profile(self) -> Dict[str, Any]:
        if not self.profile_file.exists():
            logger.warning(f"Profile file not found at {self.profile_file}. Initializing default empty profile.")
            return {}
        try:
            with open(self.profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading profile JSON: {e}")
            return {}

    def save_profile(self, data: Dict[str, Any]) -> bool:
        try:
            self.profile_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.profile_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.profile_data = data
            logger.info("Profile updated successfully.")
            return True
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False

    def _init_vector_db(self):
        """Initializes ChromaDB vector memory for semantic context retrieval."""
        try:
            import chromadb
            self.db_client = chromadb.Client()
            self.collection = self.db_client.get_or_create_collection(name="jarvis_memory")
            self._seed_initial_context()
            logger.info("ChromaDB vector memory initialized.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization fallback: {e}")
            self.db_client = None
            self.collection = None

    def _seed_initial_context(self):
        if not self.collection:
            return
        # Flatten profile entries into semantic documents
        docs = [
            "Dev Mehta is a Computer Engineering student at Thapar University graduating in 2026 with a GPA of 3.8 and 8.7 CGPA.",
            "Dev Mehta worked as a Software Development Engineer (SDE) Intern at Amazon building scalable cloud microservices and optimizing API latency.",
            "Dev Mehta engineered the DevOS local autonomous agent execution engine controlling Chrome via CDP with real-time SSE telemetry.",
            "Dev Mehta's GitHub profile is https://github.com/Dev22mehta17 and LinkedIn is https://linkedin.com/in/DevMehta.",
            "Dev Mehta is authorized to work in India and Remote roles with immediate or 15 days notice period.",
            "Technical skills include Python, FastAPI, JavaScript, React, Playwright, PostgreSQL, System Design, Docker, and Git.",
            "Career narrative: Passionate Software Engineer specializing in backend distributed systems, high-performance APIs, and browser automation agents.",
            "Why join Microsoft: Excited about Microsoft's cloud infrastructure (Azure), TypeScript ecosystem, developer tooling, and modern AI innovations with Copilot.",
            "Why join Amazon: Deep appreciation for Amazon's Leadership Principles, Customer Obsession, and building high-scale distributed backend services.",
            "Why join Google: Drawn to Google's engineering excellence, distributed database architectures, and bleeding-edge AI agent frameworks."
        ]
        
        # Ingest custom extra context if present in profile
        extra = self.profile_data.get("extra_context", {})
        if extra.get("career_narrative"):
            docs.append(f"Career narrative: {extra['career_narrative']}")
        if extra.get("custom_user_notes"):
            docs.append(f"User career goals & notes: {extra['custom_user_notes']}")
        for ach in extra.get("key_achievements", []):
            docs.append(f"Key engineering achievement: {ach}")
        for comp, align in extra.get("company_alignments", {}).items():
            docs.append(f"Alignment with {comp}: {align}")

        ids = [f"seed_doc_{i}" for i in range(len(docs))]
        try:
            self.collection.upsert(documents=docs, ids=ids)
            logger.info(f"Seeded ChromaDB with {len(docs)} knowledge chunks.")
        except Exception as e:
            logger.error(f"Error seeding ChromaDB: {e}")

    def get_extra_context(self) -> Dict[str, Any]:
        """Returns the extra custom context notes and career narrative."""
        return self.profile_data.get("extra_context", {})

    def get_full_candidate_summary(self) -> str:
        """Returns a comprehensive text summary of the candidate for LLM prompt context."""
        p = self.profile_data
        personal = p.get("personal", {})
        edu = p.get("education", {})
        prof = p.get("professional", {})
        links = p.get("links", {})
        extra = p.get("extra_context", {})

        summary = f"""Candidate Name: {personal.get('full_name', 'Dev Mehta')}
Email: {personal.get('email_primary', '')} | Phone: {personal.get('phone', '')} | Location: {personal.get('location', '')}
Education: {edu.get('degree', '')} from {edu.get('university', '')} (Graduation: {edu.get('graduation_year', '2026')}, GPA: {edu.get('gpa', '3.8/4.0')})
Current/Recent Experience: {prof.get('current_role', '')} at {prof.get('current_company', '')}
Total Experience: {prof.get('total_experience', '1 year')}
Core Skills: {', '.join(prof.get('skills', []))}
Links: GitHub ({links.get('github', '')}), LinkedIn ({links.get('linkedin', '')}), Portfolio ({links.get('portfolio', '')})
Career Narrative: {extra.get('career_narrative', prof.get('experience_summary', ''))}
Key Achievements: {'; '.join(extra.get('key_achievements', []))}
Custom Notes: {extra.get('custom_user_notes', '')}
"""
        return summary.strip()

    def add_document_context(self, text: str, filename: str) -> bool:
        """Ingests text from uploaded PDF/Doc into vector memory and auto-extracts profile details."""
        try:
            import re
            if self.collection and text.strip():
                # Split text into chunks of 300 words
                words = text.split()
                chunks = [" ".join(words[i:i+300]) for i in range(0, len(words), 300)]
                ids = [f"upload_{filename}_{i}" for i in range(len(chunks))]
                self.collection.upsert(documents=chunks, ids=ids)
                logger.info(f"Ingested {len(chunks)} text chunks from document {filename} into ChromaDB.")

            # Auto-extract structured profile fields from text
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
            phone_match = re.search(r'\+?\d[\d\s\-]{8,}\d', text)
            linkedin_match = re.search(r'https?://[w\.]*linkedin\.com/in/[\w\-]+', text)
            github_match = re.search(r'https?://[w\.]*github\.com/[\w\-]+', text)

            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if "personal" not in self.profile_data: self.profile_data["personal"] = {}
            if "education" not in self.profile_data: self.profile_data["education"] = {}
            if "links" not in self.profile_data: self.profile_data["links"] = {}
            if "professional" not in self.profile_data: self.profile_data["professional"] = {}

            if email_match:
                self.profile_data["personal"]["email_primary"] = email_match.group(0)
            if phone_match:
                self.profile_data["personal"]["phone"] = phone_match.group(0).strip()
            if linkedin_match:
                self.profile_data["links"]["linkedin"] = linkedin_match.group(0)
            if github_match:
                self.profile_data["links"]["github"] = github_match.group(0)

            if lines and len(lines[0]) < 40 and not any(c in lines[0] for c in ['@', 'http', ':']):
                self.profile_data["personal"]["full_name"] = lines[0]

            for line in lines:
                l_lower = line.lower()
                # Skip bullet points or project lines when parsing university name
                if any(line.startswith(c) for c in ['•', '-', '*', '1.', '2.']):
                    continue
                if any(kw in l_lower for kw in ['activities', 'executed', 'built', 'project', 'developed', 'lead', 'worked']):
                    continue
                if any(u in l_lower for u in ["university", "college", "institute", "thapar", "iit", "nit", "school"]):
                    self.profile_data["education"]["university"] = line
                    break

            for line in lines:
                l_lower = line.lower()
                if any(line.startswith(c) for c in ['•', '-', '*', '1.', '2.']):
                    continue
                if any(kw in l_lower for kw in ['activities', 'executed', 'built', 'project', 'developed']):
                    continue
                if any(d in l_lower for d in ["b.e.", "b.tech", "bachelor", "m.tech", "master", "computer engineering", "computer science"]):
                    self.profile_data["education"]["degree"] = line
                    break

            self.profile_data["documents"]["active_resume_path"] = filename
            self.profile_data["professional"]["experience_summary"] = text[:400].replace("\n", " ").strip()
            self.save_profile(self.profile_data)

            return True
        except Exception as e:
            logger.error(f"Error adding document context: {e}")
            return False

    def query_semantic_memory(self, query: str, top_k: int = 3) -> List[str]:
        """Queries vector memory for context relevant to open-ended form questions."""
        if not self.collection:
            # Fallback simple string matching if ChromaDB not active
            return [self.profile_data.get("professional", {}).get("experience_summary", "")]
        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            documents = results.get("documents", [[]])[0]
            return documents
        except Exception as e:
            logger.error(f"Error querying semantic memory: {e}")
            return []

    def get_field_value(self, field_name: str) -> Optional[str]:
        """Maps standard form field keys to memory profile entries."""
        field_lower = field_name.lower().replace("_", " ").replace("-", " ")
        
        # 1. Offer in Hand / Other Offers (Specific check before general CTC/salary)
        if any(k in field_lower for k in ["offer in hand", "any offer", "holding offer", "holding any offer", "other offer", "competing offer", "current offer"]):
            return "No offer in hand / Currently interviewing"

        # 2. Education & College (Specific check before candidate name!)
        if any(k in field_lower for k in ["college", "university", "school", "institution", "institute", "alma mater"]):
            return self.profile_data.get("education", {}).get("university")
        if any(k in field_lower for k in ["degree", "major", "qualification", "branch", "stream"]):
            return self.profile_data.get("education", {}).get("degree")
        if any(k in field_lower for k in ["graduation", "grad year", "passing year", "pass out", "passout", "batch", "graduating year"]):
            return self.profile_data.get("education", {}).get("graduation_year")
        if "gpa" in field_lower or "cgpa" in field_lower:
            return self.profile_data.get("education", {}).get("gpa")

        # 3. Company & Employer (Specific check before candidate name!)
        if any(k in field_lower for k in ["company name", "current employer", "organization name", "current company", "firm name"]):
            return self.profile_data.get("professional", {}).get("current_company")

        # 4. Personal Contact & Candidate Name
        if "email" in field_lower:
            return self.profile_data.get("personal", {}).get("email_primary")
        if any(k in field_lower for k in ["phone", "mobile", "contact number", "whatsapp"]):
            return self.profile_data.get("personal", {}).get("phone")
        if any(k in field_lower for k in ["location", "address", "city", "state", "current location"]):
            return self.profile_data.get("personal", {}).get("location")
        if "gender" in field_lower:
            return self.profile_data.get("personal", {}).get("gender")

        # Candidate Name (Only if NOT college name, company name, school name)
        if any(k in field_lower for k in ["full name", "your name", "candidate name", "applicant name", "first name"]) or \
           (field_lower.strip() in ["name", "name *"] or ("name" in field_lower and not any(x in field_lower for x in ["college", "univ", "school", "comp", "employ", "org", "proj", "role", "file", "skill"]))):
            return self.profile_data.get("personal", {}).get("full_name")

        # 5. Links
        if "github" in field_lower:
            return self.profile_data.get("links", {}).get("github")
        if "linkedin" in field_lower:
            return self.profile_data.get("links", {}).get("linkedin")
        if "portfolio" in field_lower or "website" in field_lower:
            return self.profile_data.get("links", {}).get("portfolio")

        # 6. Professional Experience
        if any(k in field_lower for k in ["total years of experience", "years of experience", "total experience", "work experience", "experience in years"]):
            return "1"  # 1 year experience (Internship + Projects)
        if any(k in field_lower for k in ["current role", "job title", "position", "designation"]):
            return self.profile_data.get("professional", {}).get("current_role")
        if any(k in field_lower for k in ["company", "employer", "organization"]):
            return self.profile_data.get("professional", {}).get("current_company")
        if "notice" in field_lower:
            return self.profile_data.get("professional", {}).get("notice_period")
        
        # 7. CTC / Salary
        if "current ctc" in field_lower or "current salary" in field_lower or "fixed ctc" in field_lower:
            if any(k in field_lower for k in ["lakh", "lpa", "inr", "number", "annum", "(in inr"]):
                return "0"  # 0 for intern / student
            return "0 LPA (SDE Intern)"
        if "expected ctc" in field_lower or "expected salary" in field_lower or "target ctc" in field_lower:
            if any(k in field_lower for k in ["lakh", "lpa", "inr", "number", "annum", "(in inr"]):
                return "15"  # Standard 15 LPA for SDE-1
            return "15 LPA / Standard Industry Rate"
        if "salary" in field_lower or "ctc" in field_lower:
            return "15 LPA"

        if "authorized" in field_lower or "sponsorship" in field_lower:
            return self.profile_data.get("personal", {}).get("work_authorization")
        if any(k in field_lower for k in ["skill", "technologies", "tech stack"]):
            skills = self.profile_data.get("professional", {}).get("skills", [])
            return ", ".join(skills) if skills else None

        # 8. Open-ended / Comments
        if any(k in field_lower for k in ["comment", "anything else", "additional", "message", "note"]):
            return ""

        return None

    def match_option(self, question_label: str, options: List[str]) -> Optional[Dict[str, Any]]:
        """Intelligently matches a multiple-choice question's options against profile data."""
        q_lower = question_label.lower()
        
        # --- Offer in Hand (No) ---
        if any(k in q_lower for k in ["offer in hand", "any offer", "holding offer", "holding any offer", "other offers"]):
            for opt in options:
                if opt.lower().strip() in ["no", "no offer", "none"]:
                    return {"matched_option": opt, "confidence": "high"}

        # --- Yes/No Location & Office Relocation Questions ---
        # e.g., "Are you willing to work from our Gurgaon office 5 days a week?", "Are you comfortable working from Bengaluru?"
        if any(k in q_lower for k in ["willing to work", "comfortable working", "work from", "office", "gurgaon", "bengaluru", "bangalore", "pune", "hyderabad", "gurugram", "delhi", "noida", "mumbai", "relocate", "relocation", "on-site", "hybrid", "days a week", "5 days"]):
            for opt in options:
                if opt.lower().strip() in ["yes", "yes, comfortable", "yes, willing", "yes, open"]:
                    return {"matched_option": opt, "confidence": "high"}

        # --- Yes/No Technical & Experience Questions ---
        # e.g., "Have you built backend systems powering consumer-facing applications used by end customers?"
        if any(k in q_lower for k in ["built backend", "backend systems", "consumer-facing", "end customers", "built systems", "experience with python", "fastapi", "react", "playwright", "aws", "cloud", "microservices", "distributed systems", "full-time", "immediate", "comfortable with"]):
            for opt in options:
                if opt.lower().strip() in ["yes", "yes, I have", "yes, have built", "yes, available"]:
                    return {"matched_option": opt, "confidence": "high"}

        # --- Year / Pass out / Graduation ---
        if any(k in q_lower for k in ["pass out", "passout", "graduation year", "passing year", "batch", "graduating"]):
            grad_year = self.profile_data.get("education", {}).get("graduation_year", "")
            if grad_year:
                for opt in options:
                    if grad_year in opt or opt.strip() == grad_year:
                        return {"matched_option": opt, "confidence": "high"}
                for opt in options:
                    if any(c.isdigit() for c in opt) and grad_year in opt:
                        return {"matched_option": opt, "confidence": "medium"}

        # --- Gender ---
        if "gender" in q_lower:
            gender = self.profile_data.get("personal", {}).get("gender", "")
            if gender:
                for opt in options:
                    if opt.lower().strip() == gender.lower() or gender.lower() in opt.lower():
                        return {"matched_option": opt, "confidence": "high"}

        # --- Experience level ---
        if any(k in q_lower for k in ["years of experience", "experience level", "total experience"]):
            exp = self.profile_data.get("professional", {}).get("total_experience", "1")
            import re
            exp_num = re.search(r'(\d+)', exp)
            exp_val = int(exp_num.group(1)) if exp_num else 1
            for opt in options:
                opt_num = re.search(r'(\d+)', opt)
                if opt_num and int(opt_num.group(1)) == exp_val:
                    return {"matched_option": opt, "confidence": "high"}
            for opt in options:
                if any(k in opt.lower() for k in ["fresher", "0-1", "0 to 1", "1-2", "entry", "intern"]):
                    return {"matched_option": opt, "confidence": "medium"}

        # --- Work authorization / Visa ---
        if any(k in q_lower for k in ["authorized", "visa", "work permit", "sponsorship", "legally"]):
            auth = self.profile_data.get("personal", {}).get("work_authorization", "")
            if auth:
                for opt in options:
                    if "yes" in opt.lower() and ("authorized" in auth.lower() or "yes" in auth.lower()):
                        return {"matched_option": opt, "confidence": "high"}
                    if "no" in opt.lower() and "not" in auth.lower():
                        return {"matched_option": opt, "confidence": "high"}

        # --- Education level ---
        if any(k in q_lower for k in ["education", "highest degree", "qualification level"]):
            degree = self.profile_data.get("education", {}).get("degree", "")
            if degree:
                for opt in options:
                    ol = opt.lower()
                    if any(k in ol for k in ["bachelor", "b.e", "b.tech", "undergraduate", "ug"]) and \
                       any(k in degree.lower() for k in ["b.e", "b.tech", "bachelor"]):
                        return {"matched_option": opt, "confidence": "high"}
                    if any(k in ol for k in ["master", "m.tech", "m.s", "pg"]) and \
                       any(k in degree.lower() for k in ["m.tech", "master", "m.s"]):
                        return {"matched_option": opt, "confidence": "high"}

        # --- Notice period ---
        if "notice" in q_lower:
            notice = self.profile_data.get("professional", {}).get("notice_period", "")
            if notice:
                for opt in options:
                    if "immediate" in opt.lower() and "immediate" in notice.lower():
                        return {"matched_option": opt, "confidence": "high"}
                    if "15" in opt and "15" in notice:
                        return {"matched_option": opt, "confidence": "high"}

        # --- Generic fallback for Yes/No questions ---
        if len(options) == 2 and any(o.lower() == "yes" for o in options) and any(o.lower() == "no" for o in options):
            for opt in options:
                if opt.lower() == "yes":
                    return {"matched_option": opt, "confidence": "medium"}

        return None

        # --- Generic: try semantic memory for best match ---
        if self.collection:
            try:
                results = self.collection.query(query_texts=[question_label], n_results=1)
                if results and results.get("documents", [[]])[0]:
                    context = results["documents"][0][0].lower()
                    best_match = None
                    best_score = 0
                    for opt in options:
                        opt_words = opt.lower().split()
                        score = sum(1 for w in opt_words if w in context)
                        if score > best_score:
                            best_score = score
                            best_match = opt
                    if best_match and best_score >= 1:
                        return {"matched_option": best_match, "confidence": "low"}
            except Exception:
                pass

        return None

# Global instance
memory_engine = MemoryEngine()
