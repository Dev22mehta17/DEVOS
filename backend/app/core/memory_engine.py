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
            "Dev Mehta is a Computer Engineering student at Thapar University graduating in 2026 with a GPA of 3.8.",
            "Dev Mehta worked as a Software Development Engineer (SDE) Intern at Amazon building cloud microservices.",
            "Dev Mehta's GitHub profile is https://github.com/devmehta and LinkedIn is https://linkedin.com/in/devmehta.",
            "Dev Mehta is authorized to work in India and Remote roles with immediate or 15 days notice period.",
            "Skills include Python, FastAPI, JavaScript, React, Playwright, PostgreSQL, System Design, and Docker."
        ]
        ids = [f"doc_{i}" for i in range(len(docs))]
        try:
            self.collection.upsert(documents=docs, ids=ids)
        except Exception as e:
            logger.error(f"Error seeding ChromaDB: {e}")

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
                if any(u in l_lower for u in ["university", "college", "institute", "thapar"]):
                    self.profile_data["education"]["university"] = line
                if any(d in l_lower for d in ["b.e.", "b.tech", "bachelor", "degree", "computer engineering", "computer science"]):
                    self.profile_data["education"]["degree"] = line

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
        
        # Personal
        if any(k in field_lower for k in ["name", "full name", "first name", "applicant"]):
            return self.profile_data.get("personal", {}).get("full_name")
        if "email" in field_lower:
            return self.profile_data.get("personal", {}).get("email_primary")
        if any(k in field_lower for k in ["phone", "mobile", "contact number"]):
            return self.profile_data.get("personal", {}).get("phone")
        if "location" in field_lower or "address" in field_lower:
            return self.profile_data.get("personal", {}).get("location")
            
        # Education
        if any(k in field_lower for k in ["university", "college", "school", "institution"]):
            return self.profile_data.get("education", {}).get("university")
        if any(k in field_lower for k in ["degree", "major", "qualification"]):
            return self.profile_data.get("education", {}).get("degree")
        if any(k in field_lower for k in ["graduation", "grad year", "passing year"]):
            return self.profile_data.get("education", {}).get("graduation_year")
        if "gpa" in field_lower or "cgpa" in field_lower:
            return self.profile_data.get("education", {}).get("gpa")

        # Links
        if "github" in field_lower:
            return self.profile_data.get("links", {}).get("github")
        if "linkedin" in field_lower:
            return self.profile_data.get("links", {}).get("linkedin")
        if "portfolio" in field_lower or "website" in field_lower:
            return self.profile_data.get("links", {}).get("portfolio")

        # Professional
        if "experience" in field_lower or "role" in field_lower:
            return self.profile_data.get("professional", {}).get("current_role")
        if "company" in field_lower or "current employer" in field_lower:
            return self.profile_data.get("professional", {}).get("current_company")
        if "notice" in field_lower:
            return self.profile_data.get("professional", {}).get("notice_period")
        if "salary" in field_lower or "ctc" in field_lower:
            return self.profile_data.get("professional", {}).get("expected_salary")
        if "authorized" in field_lower or "sponsorship" in field_lower:
            return self.profile_data.get("personal", {}).get("work_authorization")

        return None

# Global instance
memory_engine = MemoryEngine()
