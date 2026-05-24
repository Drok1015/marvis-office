from __future__ import annotations

from typing import Any

from .base import BaseAgent


class SearchAgent(BaseAgent):
    def __init__(self, llm, runtime) -> None:
        super().__init__(name='search-agent', llm=llm, runtime=runtime)

    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        await self.report_status('thinking', f'分析检索任务: {task}')
        await self.maybe_simulate_delay(simulation_mode, base=0.7)
        await self.report_status(
            'working',
            '生成检索关键词与提问路径...',
            progress={'current_step': 1, 'total_steps': 2, 'step_name': '关键词规划'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.95)

        summary = ''
        if self.llm.enabled and not simulation_mode:
            summary = await self.call_llm_text(
                '你是检索策略助手。',
                f'用户请求: {user_request}\n子任务: {task}\n请输出 5 条检索关键词和 3 条核验策略。',
            )

        await self.report_status(
            'working',
            '整理检索输出...',
            progress={'current_step': 2, 'total_steps': 2, 'step_name': '结果整理'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.85)

        if not summary:
            summary = '已生成基础检索关键词和核验策略。'

        await self.report_status('done', '检索任务完成')
        return {'agent': self.name, 'summary': summary}
