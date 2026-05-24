from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


@dataclass
class AgentEvent:
    event_type: str
    agent_name: str
    agent_display_name: str
    status: str
    message: str = ''
    progress: dict[str, Any] | None = None
    token_used: int = 0
    task_summary: str | None = None
    to_agent: str | None = None
    detail: dict[str, Any] | None = None
    result_summary: str | None = None
    total_token_used: int | None = None
    duration_ms: int | None = None

    def to_json_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['event_id'] = f"evt_{uuid4().hex[:10]}"
        payload['timestamp'] = datetime.now(timezone.utc).isoformat()
        return payload


class RunTaskRequest(BaseModel):
    user_request: str = Field(min_length=1, max_length=3000)


class SimulateRequest(BaseModel):
    user_request: str = Field(default='帮我整理本周会议纪要并产出执行清单', min_length=1, max_length=3000)


class ConfirmationDecisionRequest(BaseModel):
    confirmation_id: str
    approved: bool


class PendingConfirmation(BaseModel):
    confirmation_id: str
    agent_name: str
    agent_display_name: str
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)
