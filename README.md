# Drvis Office (Multi-Agent Virtual Office)

一个可视化多 Agent 办公室示例项目：

- 前端：React + Vite（办公室场景、Agent 动画、任务日志、Token 面板）
- 后端：FastAPI + SSE（任务编排、状态流、确认机制、LLM 调用）
- LLM：通过环境变量接入 DeepSeek（或兼容 OpenAI SDK 的其他服务）

## Features

- 6 个 Agent 协作执行任务（Orchestrator + 专项 Agent）
- SSE 实时推送状态、日志、Token 消耗
- 敏感操作确认流（approve / reject）
- 办公室场景动画（Lottie）与公共区域移动逻辑
- 任务日志与 Token 使用可视化

## Project Structure

```txt
.
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── event_bus.py
│   │   ├── llm_client.py
│   │   ├── runtime.py
│   │   └── schemas.py
│   ├── .env.example
│   ├── main.py
│   ├── README.md
│   └── requirements.txt
├── src/
│   ├── assets/
│   ├── components/
│   ├── data/
│   ├── hooks/
│   ├── App.tsx
│   └── App.css
├── package.json
└── vite.config.ts
```

## Quick Start

### 1) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `backend/.env`：

```env
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_API_KEY=your_real_key_here
# 可选：指定 FileAgent 的扫描根目录
# MARVIS_WORKSPACE_ROOT=/absolute/path/to/workspace
```

启动后端：

```bash
set -a
source .env
set +a
uvicorn main:app --reload --port 8000
```

### 2) Frontend

```bash
cd ..
npm install
npm run dev
```

默认访问：`http://localhost:5173`

## API Endpoints

- `GET /api/health`
- `GET /api/events/stream`
- `POST /api/task/run`
- `POST /api/simulate/run`
- `GET /api/confirmations/pending`
- `POST /api/confirm`

## Security Notes (Open Source)

- 不要提交任何真实 `.env` 文件或 API Key。
- 仅提交 `.env.example`。
- 若密钥曾泄露，请立即在服务商控制台吊销并重建。

## License

如需开源发布，建议补充 `LICENSE`（例如 MIT）。
