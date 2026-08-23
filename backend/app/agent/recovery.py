from typing import Dict, Any, Optional
from app.tools.browser_tool import browser_tool
import logging

logger = logging.getLogger(__name__)

class RecoveryEngine:
    """Self-healing engine for recovering from runtime browser, DOM, and context errors."""

    @staticmethod
    async def recover_browser_context() -> bool:
        """Recovers from stale or closed Chrome CDP browser contexts."""
        try:
            logger.info("[Recovery] Attempting browser CDP reconnection...")
            await browser_tool.initialize()
            page = await browser_tool.get_active_page()
            return page is not None and not page.is_closed()
        except Exception as e:
            logger.error(f"[Recovery] Failed to recover browser context: {e}")
            return False

    @staticmethod
    async def dismiss_overlay_or_cookies(page) -> bool:
        """Dismisses common cookie banners or modal backdrops that obstruct clicks."""
        if not page:
            return False
        try:
            dismissed = await page.evaluate("""() => {
                const cookieBtns = Array.from(document.querySelectorAll(
                    'button, a, div[role="button"]'
                )).filter(b => {
                    const t = (b.innerText || '').toLowerCase();
                    return t.includes('accept all') || t.includes('accept cookies') || t.includes('i agree') || t.includes('got it');
                });
                if (cookieBtns.length > 0) {
                    cookieBtns[0].click();
                    return true;
                }
                return false;
            }""")
            return dismissed
        except Exception:
            return False

    @staticmethod
    async def retry_with_fallback(action_name: str, primary_coroutine, fallback_coroutine=None) -> Dict[str, Any]:
        """Executes a coroutine with automatic context recovery on failure."""
        try:
            return await primary_coroutine()
        except Exception as primary_err:
            logger.warning(f"[Recovery] Action '{action_name}' failed: {primary_err}. Attempting self-healing...")
            
            # Step 1: Reconnect CDP
            recovered = await RecoveryEngine.recover_browser_context()
            if recovered and fallback_coroutine:
                try:
                    logger.info(f"[Recovery] Retrying '{action_name}' with fallback handler...")
                    return await fallback_coroutine()
                except Exception as fb_err:
                    logger.error(f"[Recovery] Fallback failed for '{action_name}': {fb_err}")
            
            return {
                "status": "ERROR",
                "message": f"Action '{action_name}' encountered an error: {str(primary_err)}"
            }

recovery_engine = RecoveryEngine()
