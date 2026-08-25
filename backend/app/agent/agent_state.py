from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid
import time

class GoalType(str, Enum):
    JOB_APPLICATION = "JOB_APPLICATION"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    RECRUITER_PIPELINE = "RECRUITER_PIPELINE"
    GMAIL_ACTION = "GMAIL_ACTION"
    EMAIL_CAMPAIGN = "EMAIL_CAMPAIGN"
    LOCAL_FILE_TASK = "LOCAL_FILE_TASK"
    WEB_SEARCH = "WEB_SEARCH"
    CUSTOM_TASK = "CUSTOM_TASK"

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SKIPPED = "SKIPPED"

class TaskStep(BaseModel):
    id: str = Field(default_factory=lambda: f"step_{uuid.uuid4().hex[:6]}")
    step_index: int
    title: str
    description: str
    action_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

class ExecutionPlan(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    goal_type: GoalType
    goal_text: str
    steps: List[TaskStep] = Field(default_factory=list)
    current_step_index: int = 0
    requires_hitl: bool = False
    status: StepStatus = StepStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_step(self) -> Optional[TaskStep]:
        self.current_step_index += 1
        return self.get_current_step()

    def is_complete(self) -> bool:
        return self.current_step_index >= len(self.steps)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal_type": self.goal_type.value,
            "goal_text": self.goal_text,
            "total_steps": len(self.steps),
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "steps": [
                {
                    "id": s.id,
                    "index": s.step_index,
                    "title": s.title,
                    "status": s.status.value,
                    "error": s.error_message
                }
                for s in self.steps
            ]
        }

class VerificationResult(BaseModel):
    success: bool
    verified_by: str
    observation: str = ""
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
