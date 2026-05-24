from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from .constants import AGENTS
from .event_bus import EventBus
from .schemas import AgentEvent


@dataclass
class ConfirmationSlot:
    confirmation_id: str
    agent_name: str
    action: str
    detail: dict[str, Any]
    event: asyncio.Event = field(default_factory=asyncio.Event)
    approved: bool | None = None


class RuntimeState:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.task_lock = asyncio.Lock()
        self.current_task_id: str | None = None
        self.tokens_by_agent: dict[str, int] = {name: 0 for name in AGENTS.keys()}
        self.pending_confirmations: dict[str, ConfirmationSlot] = {}

    def reset(self) -> None:
        self.tokens_by_agent = {name: 0 for name in AGENTS.keys()}
        self.pending_confirmations.clear()

    def total_tokens(self) -> int:
        return sum(self.tokens_by_agent.values())

    async def add_tokens(self, agent_name: str, tokens: int) -> int:
        if tokens <= 0:
            return self.total_tokens()
        self.tokens_by_agent[agent_name] = self.tokens_by_agent.get(agent_name, 0) + tokens
        total = self.total_tokens()
        await self.event_bus.publish(
            AgentEvent(
                event_type='token_update',
                agent_name=agent_name,
                agent_display_name=AGENTS[agent_name],
                status='working',
                token_used=total,
            )
        )
        return total

    async def create_confirmation(self, agent_name: str, action: str, detail: dict[str, Any]) -> ConfirmationSlot:
        cid = f"cfm_{uuid.uuid4().hex[:8]}"
        slot = ConfirmationSlot(
            confirmation_id=cid,
            agent_name=agent_name,
            action=action,
            detail=detail,
        )
        self.pending_confirmations[cid] = slot

        await self.event_bus.publish(
            AgentEvent(
                event_type='confirmation_required',
                agent_name=agent_name,
                agent_display_name=AGENTS[agent_name],
                status='paused',
                message=f'等待确认: {action}',
                detail={
                    'confirmation_id': cid,
                    'action': action,
                    'detail': detail,
                },
            )
        )
        return slot

    async def resolve_confirmation(self, confirmation_id: str, approved: bool) -> bool:
        slot = self.pending_confirmations.get(confirmation_id)
        if not slot:
            return False

        slot.approved = approved
        slot.event.set()
        self.pending_confirmations.pop(confirmation_id, None)

        await self.event_bus.publish(
            AgentEvent(
                event_type='confirmation_resolved',
                agent_name=slot.agent_name,
                agent_display_name=AGENTS[slot.agent_name],
                status='working' if approved else 'idle',
                message='用户已确认继续执行' if approved else '用户拒绝执行',
                detail={'confirmation_id': confirmation_id, 'approved': approved},
            )
        )
        return True
