# Backend Service (FastAPI + SSE)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中配置：

```env
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_deepseek_api_key
# MARVIS_WORKSPACE_ROOT=/absolute/path/to/workspace
```

启动：

```bash
set -a
source .env
set +a
uvicorn main:app --reload --port 8000
```

## APIs

- `GET /api/health`：健康检查与 LLM 配置状态
- `GET /api/events/stream`：SSE 事件流
- `POST /api/task/run`：启动真实多 Agent 任务
- `POST /api/simulate/run`：启动模拟任务
- `GET /api/confirmations/pending`：查询待确认操作
- `POST /api/confirm`：提交确认结果

### Payload: `/api/task/run`

```json
{
  "user_request": "请整理项目文件并给出改进建议"
}
```

### Payload: `/api/confirm`

```json
{
  "confirmation_id": "cfm_xxxx",
  "approved": true
}
```
