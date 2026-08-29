import re
from enum import Enum
from typing import Dict, Any, Optional

class ATSPlatform(str, Enum):
    GREENHOUSE = "GREENHOUSE"
    LEVER = "LEVER"
    LINKEDIN = "LINKEDIN"
    GOOGLE_FORMS = "GOOGLE_FORMS"
    UNIVERSAL_WEB = "UNIVERSAL_WEB"

class ATSDetector:
    """Detects ATS platform signatures from target URLs or DOM snippets."""

    @staticmethod
    def detect_from_url(url: str) -> ATSPlatform:
        url_lower = url.lower()

        if "boards.greenhouse.io" in url_lower or "job-boards.greenhouse.io" in url_lower or "grnh.se" in url_lower:
            return ATSPlatform.GREENHOUSE

        if "jobs.lever.co" in url_lower or "lever.co" in url_lower:
            return ATSPlatform.LEVER

        if "linkedin.com/jobs" in url_lower or "linkedin.com/job" in url_lower:
            return ATSPlatform.LINKEDIN

        if "docs.google.com/forms" in url_lower or "forms.gle" in url_lower:
            return ATSPlatform.GOOGLE_FORMS

        return ATSPlatform.UNIVERSAL_WEB

    @staticmethod
    async def detect_from_page(page) -> ATSPlatform:
        """Inspects live DOM for embedded ATS iframes or containers."""
        if not page:
            return ATSPlatform.UNIVERSAL_WEB
        try:
            url = page.url
            url_platform = ATSDetector.detect_from_url(url)
            if url_platform != ATSPlatform.UNIVERSAL_WEB:
                return url_platform

            # Check DOM signatures
            is_greenhouse = await page.evaluate("""() => {
                return !!(
                    document.querySelector('#app_form') ||
                    document.querySelector('form[action*="greenhouse"]') ||
                    document.querySelector('div#application') ||
                    document.querySelector('#job_application_answers_attributes') ||
                    document.querySelector('iframe[src*="greenhouse.io"]')
                );
            }""")
            if is_greenhouse:
                return ATSPlatform.GREENHOUSE

            is_lever = await page.evaluate("""() => {
                return !!(
                    document.querySelector('.application-form') ||
                    document.querySelector('form[action*="lever.co"]') ||
                    document.querySelector('.application-page') ||
                    document.querySelector('iframe[src*="lever.co"]')
                );
            }""")
            if is_lever:
                return ATSPlatform.LEVER

            is_linkedin = await page.evaluate("""() => {
                return !!(
                    document.querySelector('.jobs-apply-button') ||
                    document.querySelector('.jobs-easy-apply-modal')
                );
            }""")
            if is_linkedin:
                return ATSPlatform.LINKEDIN

            return ATSPlatform.UNIVERSAL_WEB
        except Exception:
            return ATSPlatform.UNIVERSAL_WEB

ats_detector = ATSDetector()
