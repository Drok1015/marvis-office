from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents import Orchestrator
from app.config import load_settings
from app.constants import AGENTS
from app.event_bus import EventBus
from app.llm_client import DeepSeekClient
from app.runtime import RuntimeState
from app.schemas import ConfirmationDecisionRequest, PendingConfirmation, RunTaskRequest, SimulateRequest

settings = load_settings()
event_bus = EventBus()
runtime = RuntimeState(event_bus=event_bus)
llm = DeepSeekClient(settings=settings)
orchestrator = Orchestrator(llm=llm, runtime=runtime, workspace_root=settings.workspace_root)

app = FastAPI(title='Marvis Office Orchestrator API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


async def run_task(user_request: str, task_id: str, simulation_mode: bool = False) -> None:
    async with runtime.task_lock:
        runtime.current_task_id = task_id
        runtime.reset()

        try:
            await orchestrator.execute(user_request, simulation_mode=simulation_mode)
            await asyncio.sleep(0.8)
            for agent_name in AGENTS.keys():
                agent = orchestrator if agent_name == 'main-agent' else orchestrator.sub_agents[agent_name]
                await agent.report_status('idle', '等待新任务')
        except Exception as exc:  # noqa: BLE001
            await orchestrator.report_status('error', f'任务执行失败: {exc}')
        finally:
            runtime.current_task_id = None


@app.get('/api/events/stream')
async def stream_events(request: Request):
    queue = event_bus.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f'data: {data}\n\n'
                except asyncio.TimeoutError:
                    yield ': heartbeat\n\n'
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@app.post('/api/task/run')
async def run_real_task(payload: RunTaskRequest, background_tasks: BackgroundTasks):
    if runtime.task_lock.locked() or runtime.current_task_id:
        raise HTTPException(status_code=409, detail='已有任务执行中，请稍后再试')

    task_id = f"task_{uuid4().hex[:10]}"
    runtime.current_task_id = task_id
    background_tasks.add_task(run_task, payload.user_request, task_id, False)
    return {'ok': True, 'message': 'task started', 'task_id': task_id}


@app.post('/api/simulate/run')
async def run_simulation(payload: SimulateRequest, background_tasks: BackgroundTasks):
    if runtime.task_lock.locked() or runtime.current_task_id:
        raise HTTPException(status_code=409, detail='已有任务执行中，请稍后再试')

    task_id = f"task_{uuid4().hex[:10]}"
    runtime.current_task_id = task_id
    background_tasks.add_task(run_task, payload.user_request, task_id, True)
    return {'ok': True, 'message': 'simulation started', 'task_id': task_id}


@app.post('/api/confirm')
async def resolve_confirmation(payload: ConfirmationDecisionRequest):
    resolved = await runtime.resolve_confirmation(payload.confirmation_id, payload.approved)
    if not resolved:
        raise HTTPException(status_code=404, detail='confirmation_id 不存在或已过期')
    return {'ok': True}


@app.get('/api/confirmations/pending')
async def list_pending_confirmations() -> dict[str, Any]:
    items = [
        PendingConfirmation(
            confirmation_id=slot.confirmation_id,
            agent_name=slot.agent_name,
            agent_display_name=AGENTS[slot.agent_name],
            action=slot.action,
            detail=slot.detail,
        ).model_dump()
        for slot in runtime.pending_confirmations.values()
    ]
    return {'items': items}


@app.get('/api/health')
async def health_check():
    return {
        'ok': True,
        'llm_enabled': llm.enabled,
        'model': settings.deepseek_model,
        'base_url': settings.deepseek_api_base_url,
    }
