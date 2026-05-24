from __future__ import annotations

import asyncio
import json
from typing import Any

from .schemas import AgentEvent


class EventBus:
    def __init__(self) -> None:
        self._queues: list[asyncio.Queue[str]] = []

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        if queue in self._queues:
            self._queues.remove(queue)

    async def publish(self, event: AgentEvent | dict[str, Any]) -> None:
        payload = event.to_json_dict() if isinstance(event, AgentEvent) else event
        data = json.dumps(payload, ensure_ascii=False)
        for queue in list(self._queues):
            await queue.put(data)
