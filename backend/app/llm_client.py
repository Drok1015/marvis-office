from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from .config import Settings


class DeepSeekClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: AsyncOpenAI | None = None
        if settings.llm_enabled:
            self._client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_api_base_url)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def complete_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> tuple[str, int]:
        if not self._client:
            return '', 0

        response = await self._client.chat.completions.create(
            model=self.settings.deepseek_model,
            temperature=temperature,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        )

        content = response.choices[0].message.content or ''
        if isinstance(content, list):
            content = ''.join(part.get('text', '') for part in content if isinstance(part, dict))

        usage = getattr(response, 'usage', None)
        total_tokens = getattr(usage, 'total_tokens', 0) if usage else 0
        return content.strip(), int(total_tokens or 0)

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: dict[str, Any],
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], int]:
        text, tokens = await self.complete_text(system_prompt, user_prompt, temperature=temperature)
        if not text:
            return fallback, tokens

        cleaned = text.strip().replace('```json', '').replace('```', '').strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed, tokens
        except json.JSONDecodeError:
            pass

        return fallback, tokens
