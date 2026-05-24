from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseAgent


class FileAgent(BaseAgent):
    def __init__(self, llm, runtime, workspace_root: Path) -> None:
        super().__init__(name='file-agent', llm=llm, runtime=runtime)
        self.workspace_root = workspace_root

    async def execute(self, task: str, user_request: str = '', simulation_mode: bool = False) -> dict[str, Any]:
        await self.report_status('thinking', f'分析文件任务: {task}')
        await self.maybe_simulate_delay(simulation_mode, base=0.8)

        ok = await self.check_sensitive_and_confirm(
            f'{task} {user_request}',
            action='执行可能影响文件的操作',
            detail={'task': task},
        )
        if not ok:
            return {'cancelled': True}

        await self.report_status(
            'working',
            '正在检索文件...',
            progress={'current_step': 1, 'total_steps': 3, 'step_name': '搜索文件'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=1.1)
        files = self._find_candidate_files(task)

        await self.report_status(
            'working',
            f'已找到 {len(files)} 个候选文件，正在抽样读取...',
            progress={'current_step': 2, 'total_steps': 3, 'step_name': '读取内容'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=1.0)
        snippets = self._read_snippets(files)

        await self.report_status(
            'working',
            '正在生成文件分析摘要...',
            progress={'current_step': 3, 'total_steps': 3, 'step_name': '总结结果'},
        )
        await self.maybe_simulate_delay(simulation_mode, base=0.9)

        summary = ''
        if self.llm.enabled and not simulation_mode:
            prompt = (
                f"用户请求: {user_request}\n"
                f"子任务: {task}\n"
                f"候选文件: {files[:8]}\n"
                f"内容片段: {snippets[:3]}\n"
                '请用简洁中文给出可执行结论。'
            )
            summary = await self.call_llm_text('你是文件分析助手。', prompt)

        if not summary:
            summary = f'检索到 {len(files)} 个文件，已读取 {len(snippets)} 个片段并完成基础分析。'

        await self.report_status('done', '文件任务完成')
        return {
            'agent': self.name,
            'summary': summary,
            'files': files[:12],
        }

    def _find_candidate_files(self, task: str) -> list[str]:
        keywords = [item.strip() for item in task.replace('，', ' ').replace(',', ' ').split() if item.strip()]
        candidates: list[str] = []

        for path in self.workspace_root.rglob('*'):
            if not path.is_file():
                continue
            if path.name.startswith('.'):
                continue
            rel = path.relative_to(self.workspace_root).as_posix()
            if any(ext in rel.lower() for ext in ['node_modules/', '.venv/', 'dist/']):
                continue
            if not keywords or any(keyword.lower() in rel.lower() for keyword in keywords):
                candidates.append(rel)
            if len(candidates) >= 80:
                break

        if not candidates:
            for path in self.workspace_root.rglob('*'):
                if path.is_file() and not path.name.startswith('.'):
                    rel = path.relative_to(self.workspace_root).as_posix()
                    if any(seg in rel for seg in ['node_modules/', '.venv/', 'dist/']):
                        continue
                    candidates.append(rel)
                if len(candidates) >= 20:
                    break

        return candidates

    def _read_snippets(self, relative_files: list[str]) -> list[str]:
        snippets: list[str] = []
        for rel in relative_files[:5]:
            file_path = self.workspace_root / rel
            try:
                raw = file_path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            text = raw.strip().replace('\n', ' ')
            if text:
                snippets.append(f'{rel}: {text[:280]}')
        return snippets
