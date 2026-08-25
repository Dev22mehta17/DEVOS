import asyncio
import json
import uuid
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pathlib import Path

logger = logging.getLogger(__name__)

# Persistent storage path
DATA_DIR = Path(__file__).parent.parent.parent / "data"
CAMPAIGNS_FILE = DATA_DIR / "campaigns.json"


class CampaignJob(BaseModel):
    """Individual email job within a campaign."""
    job_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:8]}")
    campaign_id: str = ""
    draft_index: int = 0
    email: str = ""
    name: str = ""
    company: str = ""
    role: str = ""
    subject: str = ""
    body: str = ""
    attached_file: Optional[str] = None
    scheduled_at: Optional[str] = None  # ISO format datetime
    status: str = "PENDING"  # PENDING | SENDING | SENT | FAILED | RETRY | CANCELLED
    attempts: int = 0
    max_retries: int = 2
    sent_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Campaign(BaseModel):
    """A collection of email jobs forming a campaign."""
    campaign_id: str
    title: str = "Email Campaign"
    total_jobs: int = 0
    scheduled_at: Optional[str] = None  # ISO format datetime, None = send now
    schedule_display: str = "Immediately"
    status: str = "SCHEDULED"  # SCHEDULED | RUNNING | COMPLETED | CANCELLED | PAUSED
    jobs: List[CampaignJob] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def get_status_summary(self) -> Dict[str, Any]:
        sent = sum(1 for j in self.jobs if j.status == "SENT")
        failed = sum(1 for j in self.jobs if j.status == "FAILED")
        pending = sum(1 for j in self.jobs if j.status in ("PENDING", "RETRY"))
        sending = sum(1 for j in self.jobs if j.status == "SENDING")
        cancelled = sum(1 for j in self.jobs if j.status == "CANCELLED")

        return {
            "campaign_id": self.campaign_id,
            "title": self.title,
            "total": self.total_jobs,
            "sent": sent,
            "failed": failed,
            "pending": pending,
            "sending": sending,
            "cancelled": cancelled,
            "scheduled_at": self.scheduled_at,
            "schedule_display": self.schedule_display,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "jobs": [
                {
                    "job_id": j.job_id,
                    "email": j.email,
                    "name": j.name,
                    "company": j.company,
                    "role": j.role,
                    "subject": j.subject,
                    "status": j.status,
                    "sent_at": j.sent_at,
                    "error_message": j.error_message,
                    "attempts": j.attempts
                }
                for j in self.jobs
            ]
        }


class CampaignScheduler:
    """Persistent campaign scheduler with background worker.

    - Jobs are stored in data/campaigns.json for durability across restarts.
    - Background asyncio worker checks every 30s for due jobs.
    - Rate limit: 1 email per 15 seconds to avoid Gmail throttling.
    - Retry: Failed jobs retry up to 2 times with 60s backoff.
    """

    def __init__(self):
        self.campaigns: Dict[str, Campaign] = {}
        self._worker_running = False
        self._event_broadcaster = None
        self._load()

    def set_event_broadcaster(self, fn):
        self._event_broadcaster = fn

    async def _emit(self, step_type: str, message: str, details: Dict[str, Any] = None):
        if self._event_broadcaster:
            try:
                await self._event_broadcaster(step_type, message, details or {})
            except Exception as e:
                logger.warning(f"[Scheduler] SSE emit error: {e}")

    # ───────────────────────────────────────
    # PERSISTENCE
    # ───────────────────────────────────────
    def _persist(self):
        """Save all campaigns to JSON file."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {}
            for cid, campaign in self.campaigns.items():
                data[cid] = campaign.model_dump()
            with open(CAMPAIGNS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"[Scheduler] Persisted {len(data)} campaigns to disk.")
        except Exception as e:
            logger.error(f"[Scheduler] Persist error: {e}")

    def _load(self):
        """Load campaigns from JSON file on startup."""
        try:
            if CAMPAIGNS_FILE.exists():
                with open(CAMPAIGNS_FILE, 'r') as f:
                    data = json.load(f)
                for cid, cdata in data.items():
                    # Reconstruct CampaignJob objects
                    jobs = [CampaignJob(**j) for j in cdata.get("jobs", [])]
                    cdata["jobs"] = jobs
                    self.campaigns[cid] = Campaign(**cdata)
                logger.info(f"[Scheduler] Loaded {len(self.campaigns)} campaigns from disk.")
            else:
                logger.info("[Scheduler] No existing campaigns file found. Starting fresh.")
        except Exception as e:
            logger.error(f"[Scheduler] Load error: {e}")
            self.campaigns = {}

    # ───────────────────────────────────────
    # CAMPAIGN MANAGEMENT
    # ───────────────────────────────────────
    def schedule_campaign(self, campaign_data: Dict[str, Any]) -> str:
        """Create a new campaign from approved preview data and schedule it.

        Args:
            campaign_data: The preview data from email_campaign_tool.prepare_campaign()
                           with drafts, schedule_time, etc.

        Returns:
            campaign_id
        """
        campaign_id = campaign_data.get("campaign_id", f"campaign_{uuid.uuid4().hex[:8]}")
        schedule_time = campaign_data.get("schedule_time")  # ISO string or None
        schedule_display = campaign_data.get("schedule_display", "Immediately")

        jobs = []
        for draft in campaign_data.get("drafts", []):
            job = CampaignJob(
                campaign_id=campaign_id,
                draft_index=draft.get("draft_index", 0),
                email=draft.get("email", ""),
                name=draft.get("name", ""),
                company=draft.get("company", ""),
                role=draft.get("role", ""),
                subject=draft.get("subject", ""),
                body=draft.get("body", ""),
                attached_file=draft.get("attached_file"),
                scheduled_at=schedule_time,
                status="PENDING"
            )
            jobs.append(job)

        campaign = Campaign(
            campaign_id=campaign_id,
            title=f"Recruiter Outreach ({len(jobs)} emails)",
            total_jobs=len(jobs),
            scheduled_at=schedule_time,
            schedule_display=schedule_display,
            status="SCHEDULED",
            jobs=jobs
        )

        self.campaigns[campaign_id] = campaign
        self._persist()

        logger.info(
            f"[Scheduler] Campaign {campaign_id} scheduled with {len(jobs)} jobs. "
            f"Execution: {schedule_display}"
        )

        # If sending immediately, trigger processing instantly without waiting for loop
        if not schedule_time:
            asyncio.create_task(self._process_due_jobs())

        return campaign_id

    def get_campaign_status(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get the live status of a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        return campaign.get_status_summary()

    def cancel_campaign(self, campaign_id: str) -> bool:
        """Cancel all pending jobs in a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False

        for job in campaign.jobs:
            if job.status in ("PENDING", "RETRY"):
                job.status = "CANCELLED"

        campaign.status = "CANCELLED"
        self._persist()
        logger.info(f"[Scheduler] Campaign {campaign_id} cancelled.")
        return True

    # ───────────────────────────────────────
    # BACKGROUND WORKER
    # ───────────────────────────────────────
    async def start_worker(self):
        """Start the background worker that checks for due jobs every 5 seconds."""
        if self._worker_running:
            logger.warning("[Scheduler] Worker already running.")
            return

        self._worker_running = True
        logger.info("[Scheduler] ⏰ Background campaign worker started.")

        while self._worker_running:
            try:
                await self._process_due_jobs()
            except Exception as e:
                logger.error(f"[Scheduler] Worker loop error: {e}")

            await asyncio.sleep(5)  # Check every 5 seconds for fast execution

    async def _process_due_jobs(self):
        """Find and execute all due jobs across all campaigns."""
        now = datetime.now()

        for campaign_id, campaign in list(self.campaigns.items()):
            if campaign.status in ("COMPLETED", "CANCELLED"):
                continue

            # Check if campaign is due
            if campaign.scheduled_at:
                try:
                    scheduled_dt = datetime.fromisoformat(campaign.scheduled_at)
                    if scheduled_dt > now:
                        continue  # Not yet time
                except (ValueError, TypeError):
                    pass

            # Find pending jobs
            pending_jobs = [j for j in campaign.jobs if j.status in ("PENDING", "RETRY")]
            if not pending_jobs:
                # Check if campaign is complete
                all_done = all(j.status in ("SENT", "FAILED", "CANCELLED") for j in campaign.jobs)
                if all_done and campaign.status != "COMPLETED":
                    campaign.status = "COMPLETED"
                    campaign.completed_at = datetime.now().isoformat()
                    self._persist()
                    await self._emit(
                        "CAMPAIGN_PROGRESS",
                        f"✅ Campaign complete! {sum(1 for j in campaign.jobs if j.status == 'SENT')}/{campaign.total_jobs} emails sent.",
                        campaign.get_status_summary()
                    )
                continue

            # Mark campaign as running
            if campaign.status == "SCHEDULED":
                campaign.status = "RUNNING"
                await self._emit(
                    "CAMPAIGN_PROGRESS",
                    f"📧 Campaign started! Sending {len(pending_jobs)} emails...",
                    campaign.get_status_summary()
                )

            # Execute pending jobs with fast interval (4s)
            for job in pending_jobs:
                # Check retry backoff
                if job.status == "RETRY" and job.attempts > 0:
                    if job.sent_at:
                        try:
                            last_attempt = datetime.fromisoformat(job.sent_at)
                            if (now - last_attempt).total_seconds() < 30:
                                continue
                        except (ValueError, TypeError):
                            pass

                await self._execute_job(job, campaign)
                self._persist()

                # Emit progress update
                await self._emit(
                    "CAMPAIGN_PROGRESS",
                    f"Campaign update: {job.name} @ {job.company} — {job.status}",
                    campaign.get_status_summary()
                )

                # Rate limit: 4 seconds between sends
                await asyncio.sleep(4)

    async def _execute_job(self, job: CampaignJob, campaign: Campaign):
        """Execute a single email job via Gmail."""
        from app.tools.gmail_tool import gmail_tool
        from app.core.permission_engine import permission_engine

        job.status = "SENDING"
        job.attempts += 1

        try:
            logger.info(f"[Scheduler] Sending email to {job.email} ({job.name} @ {job.company})...")

            # Create and auto-approve the action
            action_id = f"campaign_job_{job.job_id}"
            permission_engine.check_action(
                action_id=action_id,
                action_type="compose_email",
                payload={"recipient": job.email, "subject": job.subject}
            )
            permission_engine.approve_action(action_id)

            # Send via Gmail tool
            result = await gmail_tool.send_draft(
                action_id=action_id,
                payload={
                    "recipient": job.email,
                    "subject": job.subject,
                    "body": job.body,
                    "attached_file": job.attached_file
                }
            )

            if result.get("sent_on_chrome"):
                job.status = "SENT"
                job.sent_at = datetime.now().isoformat()
                job.error_message = None
                logger.info(f"[Scheduler] ✅ Email sent to {job.email}")
            else:
                raise Exception(result.get("message", "Gmail send failed"))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Scheduler] ❌ Failed to send to {job.email}: {error_msg}")

            if job.attempts < job.max_retries:
                job.status = "RETRY"
                job.error_message = f"Attempt {job.attempts}/{job.max_retries}: {error_msg}"
                job.sent_at = datetime.now().isoformat()  # Track last attempt time for backoff
            else:
                job.status = "FAILED"
                job.error_message = f"Failed after {job.attempts} attempts: {error_msg}"

    def stop_worker(self):
        """Stop the background worker."""
        self._worker_running = False
        logger.info("[Scheduler] Background worker stopped.")


# Singleton
campaign_scheduler = CampaignScheduler()
