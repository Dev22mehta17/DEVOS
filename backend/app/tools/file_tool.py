import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

SEARCH_DIRECTORIES = [
    Path.home() / "Downloads",
    Path.home() / "Documents",
    Path.home() / "Desktop"
]

class LocalFileTool:
    @staticmethod
    def find_resume_files(target_name: str = "Dev_Resume.pdf") -> List[Dict[str, Any]]:
        """Searches local directories for target resume files or any matching PDF resume."""
        found_files = []
        
        for search_dir in SEARCH_DIRECTORIES:
            if not search_dir.exists():
                continue
            try:
                for file_path in search_dir.glob("*"):
                    if not file_path.is_file():
                        continue
                    fname_lower = file_path.name.lower()
                    if target_name.lower() in fname_lower or "resume" in fname_lower or "cv" in fname_lower:
                        if fname_lower.endswith(".pdf") or fname_lower.endswith(".docx"):
                            stat = file_path.stat()
                            found_files.append({
                                "filename": file_path.name,
                                "path": str(file_path.absolute()),
                                "size_bytes": stat.st_size,
                                "directory": str(search_dir),
                                "extension": file_path.suffix.lower()
                            })
            except Exception as e:
                logger.error(f"Error scanning directory {search_dir}: {e}")

        logger.info(f"LocalFileTool found {len(found_files)} potential resume files.")
        return found_files

    @staticmethod
    def get_best_resume_path() -> Optional[str]:
        resumes = LocalFileTool.find_resume_files()
        if resumes:
            return resumes[0]["path"]
        return None

file_tool = LocalFileTool()
