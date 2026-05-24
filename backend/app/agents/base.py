from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

from ..constants import AGENTS, SENSITIVE_KEYWORDS
from ..llm_client import DeepSeekClient
from ..runtime import RuntimeState
from ..schemas import AgentEvent


class BaseAgent(ABC):
    SIMULATION_DELAY_MULTIPLIER = 1.8

    def __init__(self, name: str, llm: DeepSeekClient, runtime: RuntimeState) -> None:
        self.name = name
        self.display_name = AGENTS[name]
        self.llm = llm
        self.runtime = runtime
        self._status = 'idle'
        self._token_used = 0

    async def report_status(
        self,
        status: str,
        message: str = '',
        progress: dict[str, Any] | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._status = status
        await self.runtime.event_bus.publish(
            AgentEvent(
                event_type='agent_status_change',
                agent_name=self.name,
                agent_display_name=self.display_name,
                status=status,
                message=message,
                progress=progress,
                token_used=self._token_used,
                detail=detail,
            )
        )

    async def call_llm_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        text, tokens = await self.llm.complete_text(system_prompt, user_prompt, temperature=temperature)
        self._token_used += tokens
        await self.runtime.add_tokens(self.name, tokens)
        return text

    async def check_sensitive_and_confirm(self, task: str, action: str, detail: dict[str, Any]) -> bool:
        lowered = task.lower()
        if not any(keyword in lowered for keyword in SENSITIVE_KEYWORDS):
            return True

        await self.report_status('paused', f'等待确认: {action}')
        slot = await self.runtime.create_confirmation(self.name, action, detail)

        try:
            await asyncio.wait_for(slot.event.wait(), timeout=120)
        except asyncio.TimeoutError:
            await self.report_status('idle', '确认超时，已取消')
            return False

        if not slot.approved:
            await self.report_status('idle', '用户取消了敏感操作')
            return False

        await self.report_status('working', '已收到确认，继续执行')
        return True

    async def maybe_simulate_delay(self, simulation_mode: bool, base: float = 0.9, jitter: float = 0.35) -> None:
        if not simulation_mode:
            return
        scaled_base = base * self.SIMULATION_DELAY_MULTIPLIER
        scaled_jitter = jitter * self.SIMULATION_DELAY_MULTIPLIER
        duration = max(0.2, scaled_base + random.uniform(-scaled_jitter, scaled_jitter))
        await asyncio.sleep(duration)

    @abstractmethod
    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        raise NotImplementedError
