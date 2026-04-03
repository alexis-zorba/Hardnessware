from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # carica .env se presente, senza sovrascrivere variabili già impostate

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.workbench import WorkbenchService


class CreateSessionRequest(BaseModel):
    provider: str = Field(default="openrouter")
    model: str = Field(default="minimax/minimax-m2.7")
    workspace: str = Field(default=".")


class RunRequest(BaseModel):
    task: str = Field(min_length=1)
    max_turns: int = Field(default=8, ge=1, le=50)


class ContinueRequest(BaseModel):
    max_turns: int | None = Field(default=None, ge=1, le=50)


class MessageRequest(BaseModel):
    role: str = Field(default="user")
    content: str = Field(min_length=1)


class ReplyRequest(BaseModel):
    content: str = Field(min_length=1)


class ImportRequest(BaseModel):
    data: dict


_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

app = FastAPI(title="HARDNESS Workbench API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service = WorkbenchService(
    workspace_root=Path("."),
    storage_base=Path(".hardness-workbench"),
    api_file=Path("secrets/API.txt"),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session")
def create_session(request: CreateSessionRequest) -> dict:
    try:
        state = _service.create_session(
            provider=request.provider,
            model=request.model,
            workspace=request.workspace,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "session_id": state.session_id,
        "created_at": state.created_at,
        "provider": state.provider,
        "model": state.model,
        "workspace": str(state.workspace_root),
    }


@app.post("/session/import")
def import_session(request: ImportRequest) -> dict:
    try:
        state = _service.import_session(data=request.data)
        return {
            "session_id": state.session_id,
            "created_at": state.created_at,
            "provider": state.provider,
            "model": state.model,
            "workspace": str(state.workspace_root),
            "status": state.status,
            "pending_task": state.pending_task,
            "message_count": len(state.messages),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/session/{session_id}/export")
def export_session(session_id: str) -> dict:
    try:
        return _service.export_session(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/session/{session_id}/run")
def run_task(session_id: str, request: RunRequest) -> dict:
    try:
        return _service.run_task(session_id=session_id, task=request.task, max_turns=request.max_turns)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/session/{session_id}/continue")
def continue_task(session_id: str, request: ContinueRequest) -> dict:
    try:
        return _service.continue_task(session_id=session_id, max_turns=request.max_turns)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/session/{session_id}/message")
def add_message(session_id: str, request: MessageRequest) -> dict:
    try:
        return _service.post_message(session_id=session_id, role=request.role, content=request.content)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/session/{session_id}/reply")
def reply(session_id: str, request: ReplyRequest) -> dict:
    try:
        return _service.post_reply(session_id=session_id, content=request.content)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/session/{session_id}/resume")
def resume(session_id: str) -> dict:
    try:
        return _service.resume_task(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/session/{session_id}/interrupt")
def interrupt(session_id: str) -> dict:
    try:
        return _service.request_interrupt(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/session/{session_id}/events")
def events(
    session_id: str,
    run_id: str | None = Query(default=None),
    after: int = Query(default=0),
):
    try:
        stream = _service.stream_events(session_id=session_id, run_id=run_id, after=after)
        return StreamingResponse(stream, media_type="text/event-stream")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/session/{session_id}")
def session_status(session_id: str) -> dict:
    try:
        return _service.get_session_status(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/session/{session_id}/files")
def files(
    session_id: str,
    path: str = Query(default="."),
    recursive: bool = Query(default=False),
) -> dict:
    try:
        rows = _service.list_files(session_id=session_id, path=path, recursive=recursive)
        return {"session_id": session_id, "path": path, "recursive": recursive, "files": rows}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/session/{session_id}/diffs")
def diffs(session_id: str, path: str = Query(...)) -> dict:
    try:
        return _service.get_diff(session_id=session_id, path=path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/session/{session_id}/metrics")
def metrics(session_id: str, run_id: str | None = Query(default=None)) -> dict:
    try:
        return _service.collect_metrics(session_id=session_id, run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
