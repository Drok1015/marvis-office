from __future__ import annotations

import asyncio
import time
from typing import Any

from ..constants import AGENTS
from ..schemas import AgentEvent
from .app_agent import AppAgent
from .base import BaseAgent
from .browser_agent import BrowserAgent
from .computer_agent import ComputerAgent
from .file_agent import FileAgent
from .search_agent import SearchAgent


class Orchestrator(BaseAgent):
    def __init__(self, llm, runtime, workspace_root) -> None:
        super().__init__(name='main-agent', llm=llm, runtime=runtime)
        self.sub_agents = {
            'file-agent': FileAgent(llm=llm, runtime=runtime, workspace_root=workspace_root),
            'computer-agent': ComputerAgent(llm=llm, runtime=runtime, workspace_root=workspace_root),
            'app-agent': AppAgent(llm=llm, runtime=runtime),
            'browser-agent': BrowserAgent(llm=llm, runtime=runtime),
            'search-agent': SearchAgent(llm=llm, runtime=runtime),
        }

    async def execute(self, user_request: str, simulation_mode: bool = False) -> dict[str, Any]:
        started_at = time.perf_counter()
        await self.report_status('dispatching', '正在理解需求并拆解任务...')
        await self.maybe_simulate_delay(simulation_mode, base=0.8)

        plan = await self._plan_tasks(user_request, simulation_mode=simulation_mode)
        await self.report_status('dispatching', f'已拆解为 {len(plan)} 个子任务，开始分配')
        await self.maybe_simulate_delay(simulation_mode, base=0.75)

        for step in plan:
            await self.runtime.event_bus.publish(
                AgentEvent(
                    event_type='task_dispatched',
                    agent_name=self.name,
                    agent_display_name=self.display_name,
                    status='dispatching',
                    message=f"派发给 {AGENTS[step['agent']]}: {step['task']}",
                    to_agent=step['agent'],
                    task_summary=step['task'],
                )
            )

        async def run_step(step: dict[str, str]) -> dict[str, Any]:
            agent = self.sub_agents[step['agent']]
            return await agent.execute(step['task'], user_request=user_request, simulation_mode=simulation_mode)

        if simulation_mode:
            results: list[dict[str, Any] | Exception] = []
            for step in plan:
                results.append(await run_step(step))
        else:
            results = await asyncio.gather(*(run_step(step) for step in plan), return_exceptions=True)

        normalized_results: list[dict[str, Any]] = []
        for step, result in zip(plan, results, strict=True):
            if isinstance(result, Exception):
                await self.runtime.event_bus.publish(
                    AgentEvent(
                        event_type='agent_error',
                        agent_name=step['agent'],
                        agent_display_name=AGENTS[step['agent']],
                        status='error',
                        message=f'执行失败: {result}',
                        detail={'task': step['task']},
                    )
                )
                normalized_results.append({'agent': step['agent'], 'summary': f'失败: {result}'})
            else:
                normalized_results.append(result)

        await self.report_status('working', '正在汇总所有结果...')
        await self.maybe_simulate_delay(simulation_mode, base=0.8)
        summary = await self._summarize(user_request, normalized_results, simulation_mode=simulation_mode)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        total_tokens = self.runtime.total_tokens()

        await self.runtime.event_bus.publish(
            AgentEvent(
                event_type='task_completed',
                agent_name=self.name,
                agent_display_name=self.display_name,
                status='done',
                message='全部任务完成',
                result_summary=summary,
                total_token_used=total_tokens,
                duration_ms=duration_ms,
                token_used=total_tokens,
            )
        )

        await self.report_status('done', '汇总完成')
        await asyncio.sleep(0.8)
        await self.report_status('idle', '等待新任务')

        return {
            'plan': plan,
            'results': normalized_results,
            'summary': summary,
            'total_tokens': total_tokens,
            'duration_ms': duration_ms,
        }

    async def _plan_tasks(self, user_request: str, simulation_mode: bool = False) -> list[dict[str, str]]:
        fallback = {'steps': self._heuristic_plan(user_request)}
        if simulation_mode or not self.llm.enabled:
            return fallback['steps']

        prompt = (
            '请把用户请求拆成 2-5 个并行子任务，返回 JSON。\\n'
            '格式: {"steps":[{"agent":"file-agent|computer-agent|app-agent|browser-agent|search-agent","task":"..."}]}'
            f'\\n用户请求: {user_request}'
        )
        parsed, tokens = await self.llm.complete_json(
            system_prompt='你是多智能体调度助手，只输出 JSON。',
            user_prompt=prompt,
            fallback=fallback,
        )
        self._token_used += tokens
        await self.runtime.add_tokens(self.name, tokens)

        steps = parsed.get('steps', []) if isinstance(parsed, dict) else []
        cleaned_steps: list[dict[str, str]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            agent = step.get('agent')
            task = step.get('task')
            if agent in self.sub_agents and isinstance(task, str) and task.strip():
                cleaned_steps.append({'agent': agent, 'task': task.strip()})

        return cleaned_steps or fallback['steps']

    async def _summarize(
        self,
        user_request: str,
        results: list[dict[str, Any]],
        simulation_mode: bool = False,
    ) -> str:
        fallback = '任务执行完成，已汇总各 Agent 结果。'
        if simulation_mode or not self.llm.enabled:
            return self._fallback_summary(results)

        summary_text = '\\n'.join(
            f"- {item.get('agent', 'unknown')}: {item.get('summary', '')}" for item in results
        )
        text, tokens = await self.llm.complete_text(
            system_prompt='你是项目经理，请输出清晰的中文执行总结。',
            user_prompt=f'用户请求: {user_request}\\n子任务结果:\\n{summary_text}',
            temperature=0.2,
        )
        self._token_used += tokens
        await self.runtime.add_tokens(self.name, tokens)
        return text or fallback

    def _heuristic_plan(self, user_request: str) -> list[dict[str, str]]:
        lowered = user_request.lower()
        steps = [{'agent': 'file-agent', 'task': '检索并分析相关文件'}]

        if any(keyword in lowered for keyword in ['网页', '网站', 'http', '链接', '浏览器']):
            steps.append({'agent': 'browser-agent', 'task': '访问并提取网页关键信息'})

        if any(keyword in lowered for keyword in ['搜索', '调研', '资料', '文献', '趋势']):
            steps.append({'agent': 'search-agent', 'task': '输出检索策略与核验清单'})

        if any(keyword in lowered for keyword in ['系统', '环境', '配置', '性能']):
            steps.append({'agent': 'computer-agent', 'task': '检查系统环境并提出建议'})

        if any(keyword in lowered for keyword in ['应用', 'app', '安装', '卸载', '启动']):
            steps.append({'agent': 'app-agent', 'task': '检查应用执行路径和风险'})

        if len(steps) == 1:
            steps.extend(
                [
                    {'agent': 'search-agent', 'task': '补充检索关键词和信息源建议'},
                    {'agent': 'computer-agent', 'task': '检查执行环境约束'},
                ]
            )

        return steps[:5]

    def _fallback_summary(self, results: list[dict[str, Any]]) -> str:
        lines = []
        for item in results:
            agent = item.get('agent', 'unknown')
            summary = item.get('summary', '')
            lines.append(f'{agent}: {summary}')
        return ' | '.join(lines) if lines else '任务执行完成。'
