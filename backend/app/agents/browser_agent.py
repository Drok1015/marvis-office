from __future__ import annotations

import re
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from .base import BaseAgent


class BrowserAgent(BaseAgent):
    def __init__(self, llm, runtime) -> None:
        super().__init__(name='browser-agent', llm=llm, runtime=runtime)

    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        await self.report_status('thinking', f'分析网页任务: {task}')
        await self.maybe_simulate_delay(simulation_mode, base=0.75)
        await self.report_status(
            'working',
            '提取并访问任务中的 URL...',
            progress={'current_step': 1, 'total_steps': 2, 'step_name': '抓取网页'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=1.0)

        urls = re.findall(r'https?://[^\s)]+', task + ' ' + user_request)
        fetched: list[str] = []
        for url in urls[:3]:
            try:
                with urlopen(url, timeout=6) as response:  # noqa: S310
                    fetched.append(f'{url} ({response.status})')
            except URLError:
                fetched.append(f'{url} (访问失败)')

        await self.report_status(
            'working',
            '输出网页处理建议...',
            progress={'current_step': 2, 'total_steps': 2, 'step_name': '整理结果'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.85)

        summary = ''
        if self.llm.enabled and not simulation_mode:
            summary = await self.call_llm_text(
                '你是网页自动化助手。',
                f'用户请求: {user_request}\n子任务: {task}\nURL访问结果: {fetched}\n总结后续建议。',
            )

        if not summary:
            summary = '网页任务完成，已完成基础 URL 访问检查。'

        await self.report_status('done', '网页任务完成')
        return {'agent': self.name, 'summary': summary, 'urls': fetched}
