from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseAgent


class AppAgent(BaseAgent):
    def __init__(self, llm, runtime) -> None:
        super().__init__(name='app-agent', llm=llm, runtime=runtime)

    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        await self.report_status('thinking', f'分析应用任务: {task}')
        await self.maybe_simulate_delay(simulation_mode, base=0.8)

        ok = await self.check_sensitive_and_confirm(
            f'{task} {user_request}',
            action='执行可能影响应用的操作',
            detail={'task': task},
        )
        if not ok:
            return {'cancelled': True}

        await self.report_status(
            'working',
            '检查本机可用应用...',
            progress={'current_step': 1, 'total_steps': 2, 'step_name': '扫描应用'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=1.0)

        apps = []
        app_dir = Path('/Applications')
        if app_dir.exists():
            for app in app_dir.glob('*.app'):
                apps.append(app.name)
                if len(apps) >= 10:
                    break

        await self.report_status(
            'working',
            '整理应用执行建议...',
            progress={'current_step': 2, 'total_steps': 2, 'step_name': '整理结果'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.9)

        summary = ''
        if self.llm.enabled and not simulation_mode:
            summary = await self.call_llm_text(
                '你是桌面应用自动化助手。',
                f'用户请求: {user_request}\n子任务: {task}\n应用样本: {apps}\n给出执行建议。',
            )

        if not summary:
            summary = f'应用检查完成，共识别 {len(apps)} 个应用样本。'

        await self.report_status('done', '应用任务完成')
        return {'agent': self.name, 'summary': summary, 'apps': apps}
