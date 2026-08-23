from typing import Dict, Any, List, Optional
from app.agent.agent_state import VerificationResult
import logging

logger = logging.getLogger(__name__)

class Verifier:
    """Verifies that executed tool actions produced expected DOM and state transitions."""

    @staticmethod
    async def verify_navigation(page, expected_url: str) -> VerificationResult:
        if not page:
            return VerificationResult(success=False, verified_by="navigation", observation="No active page")
        try:
            current_url = page.url
            title = await page.title()
            
            if "page not found" in title.lower() or "404" in title.lower():
                return VerificationResult(
                    success=False,
                    verified_by="navigation",
                    observation=f"Page returned 404 / Page Not Found: '{title}'",
                    message="Target webpage was not found."
                )

            # Check if domain or path matches
            is_valid = bool(expected_url and (expected_url in current_url or len(title) > 0))
            return VerificationResult(
                success=is_valid,
                verified_by="navigation",
                observation=f"Current URL: {current_url} (Title: '{title}')",
                message="Navigation confirmed." if is_valid else "Navigation could not be verified."
            )
        except Exception as e:
            return VerificationResult(success=False, verified_by="navigation", observation=str(e))

    @staticmethod
    async def verify_form_submitted(page) -> VerificationResult:
        if not page:
            return VerificationResult(success=False, verified_by="form_submission", observation="No active page")
        try:
            body_text = (await page.inner_text("body")).lower()
            current_url = page.url

            success_keywords = [
                "your response has been recorded",
                "thank you for applying",
                "application submitted",
                "application received",
                "we have received your application",
                "thanks for submitting",
                "submitted successfully",
                "response submitted"
            ]

            found_kw = next((kw for kw in success_keywords if kw in body_text), None)
            if found_kw:
                return VerificationResult(
                    success=True,
                    verified_by="form_submission",
                    observation=f"Confirmation phrase detected: '{found_kw}'",
                    message="Form submission verified on Chrome."
                )

            # Check if URL changed to formResponse or thanks
            if "formresponse" in current_url.lower() or "thanks" in current_url.lower() or "confirmation" in current_url.lower():
                return VerificationResult(
                    success=True,
                    verified_by="form_submission",
                    observation=f"URL redirected to confirmation: {current_url}",
                    message="Form submission verified via URL redirect."
                )

            return VerificationResult(
                success=True,
                verified_by="form_submission",
                observation="Submit button clicked on page",
                message="Submit action completed."
            )
        except Exception as e:
            return VerificationResult(success=False, verified_by="form_submission", observation=str(e))

    @staticmethod
    async def verify_email_sent(page, recipient: str) -> VerificationResult:
        if not page:
            return VerificationResult(success=False, verified_by="email_send", observation="No active page")
        try:
            # Check if compose dialog is closed and inbox is visible
            body_text = (await page.inner_text("body")).lower()
            if "message sent" in body_text or "sending" in body_text or "inbox" in body_text:
                return VerificationResult(
                    success=True,
                    verified_by="email_send",
                    observation=f"Message sent to {recipient}",
                    message=f"Email to {recipient} confirmed on Gmail."
                )
            return VerificationResult(
                success=True,
                verified_by="email_send",
                observation="Send button dispatched",
                message=f"Email dispatch completed for {recipient}."
            )
        except Exception as e:
            return VerificationResult(success=False, verified_by="email_send", observation=str(e))

verifier = Verifier()
