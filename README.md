# Hardnessware

Provider-agnostic agent harness implemented in Python 3.
Orchestrate multi-step LLM tasks with a disciplined loop, tool safety, memory, and a live workbench UI.

## Features

- **Provider-agnostic** — OpenAI, Groq, OpenRouter, or mock adapter; swap without touching core logic
- **Disciplined loop** — think → act → verify → update, with guardrails (turn limits, failure caps, redundancy detection)
- **5 tools** — `read`, `write`, `search`, `py_check` (auto-invoked after every Python write), `list`
- **Memory** — session state + indexed notes persisted across runs within a session
- **Workbench UI** — React frontend with live activity stream, conversation log, inspector, pause/resume
- **REST API** — FastAPI backend with SSE event streaming, interrupt, and per-run `max_turns` control

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/<your-org>/hardnessware
cd hardnessware
pip install -e .

# 2. Configure API keys
cp .env.example .env
# Edit .env and add your keys

# 3. Start backend
start_backend.bat         # Windows
# or: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 4. Start frontend (separate terminal)
start_frontend.bat        # Windows
# or: cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** in your browser.

## Configuration

Copy `.env.example` to `.env` and fill in your keys:

```env
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
```

At least one provider key is required. The workbench defaults to OpenRouter.

## Tools

| Tool | Risk | Description |
|---|---|---|
| `read` | low | Read a UTF-8 file from the workspace |
| `write` | medium | Write UTF-8 text to a workspace file |
| `search` | low | Search for a substring across workspace files |
| `py_check` | low | Syntax-check a `.py` file — auto-invoked after every write |
| `list` | low | List files and subdirectories at a workspace path |

## Memory defaults

| Setting | Value |
|---|---|
| `max_notes_in_context` | 12 |
| `max_events_in_session` | 20 |
| `max_turns` per run (default) | 8, configurable 1–50 |

## Key behaviors

- **Auto py_check** — after writing any `.py` file, the loop runs `py_check` automatically. Syntax errors are fed back to the agent as an error message so it can fix them before continuing.
- **Pause / Continue** — when `max_turns` is reached, the session enters `paused` state. Click **Continue** in the Workbench to resume from where the agent left off, without restarting.
- **Interrupt** — click **Stop** during a run to request a clean interrupt between turns.

## Project structure

```
src/hardness/       Core agent engine (agent, tools, memory, policy, router, prompting)
app/                FastAPI backend + WorkbenchService
frontend/           React/Vite workbench UI
tests/              Unit tests
docs/               Validation reports and design notes
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
