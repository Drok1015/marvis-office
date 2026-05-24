from __future__ import annotations

import platform
from pathlib import Path
from typing import Any

from .base import BaseAgent


class ComputerAgent(BaseAgent):
    def __init__(self, llm, runtime, workspace_root: Path) -> None:
        super().__init__(name='computer-agent', llm=llm, runtime=runtime)
        self.workspace_root = workspace_root

    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        await self.report_status('thinking', f'分析系统任务: {task}')
        await self.maybe_simulate_delay(simulation_mode, base=0.7)
        await self.report_status(
            'working',
            '采集系统环境信息...',
            progress={'current_step': 1, 'total_steps': 2, 'step_name': '读取系统信息'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=1.0)

        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'workspace': str(self.workspace_root),
        }

        await self.report_status(
            'working',
            '生成系统建议...',
            progress={'current_step': 2, 'total_steps': 2, 'step_name': '输出建议'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.9)

        summary = ''
        if self.llm.enabled and not simulation_mode:
            summary = await self.call_llm_text(
                '你是系统运维助手。',
                f'用户请求: {user_request}\n子任务: {task}\n环境: {info}\n请给出简短执行建议。',
            )

        if not summary:
            summary = f"系统信息采集完成: {info['platform']} / Python {info['python_version']}"

        await self.report_status('done', '系统任务完成')
        return {'agent': self.name, 'summary': summary, 'info': info}
