from __future__ import annotations

import asyncio
import difflib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from hardness.agent import AgentLoop
from hardness.config import HardnessConfig, ProviderConfig, RuntimeConfig
from hardness.types import Message


@dataclass(slots=True)
class SessionState:
    session_id: str
    created_at: str
    workspace_root: Path
    storage_root: Path
    provider: str
    model: str
    run_ids: list[str] = field(default_factory=list)
    messages: list[dict[str, str]] = field(default_factory=list)
    interrupt_requested: bool = False
    latest_result: dict[str, Any] | None = None
    baseline_files: dict[str, str] = field(default_factory=dict)
    status: str = "idle"
    pending_task: str | None = None
    pending_max_turns: int = 8
    waiting_question: str | None = None
    waiting_options: list[str] = field(default_factory=list)
    last_user_reply: str | None = None


class WorkbenchService:
    def __init__(self, workspace_root: Path, storage_base: Path, api_file: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.storage_base = storage_base.resolve()
        self.api_file = api_file.resolve()
        self.sessions: dict[str, SessionState] = {}

    def create_session(self, provider: str, model: str, workspace: str = ".") -> SessionState:
        workspace_root = Path(workspace).resolve()
        if not workspace_root.exists():
            raise ValueError(f"Workspace path does not exist: {workspace}")
        session_id = f"session-{uuid4().hex[:12]}"
        state = SessionState(
            session_id=session_id,
            created_at=datetime.now(UTC).isoformat(),
            workspace_root=workspace_root,
            storage_root=self.storage_base / session_id,
            provider=provider,
            model=model,
        )
        state.storage_root.mkdir(parents=True, exist_ok=True)
        self.sessions[session_id] = state
        return state

    def get_session(self, session_id: str) -> SessionState:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown session_id: {session_id}") from exc

    def post_message(self, session_id: str, role: str, content: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        state.messages.append(entry)
        return entry

    def get_session_status(self, session_id: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        return {
            "session_id": state.session_id,
            "status": state.status,
            "pending_task": state.pending_task,
            "waiting_question": state.waiting_question,
            "waiting_options": state.waiting_options,
            "run_count": len(state.run_ids),
            "last_run_id": state.run_ids[-1] if state.run_ids else None,
        }

    def run_task(self, session_id: str, task: str, max_turns: int = 8) -> dict[str, Any]:
        state = self.get_session(session_id)
        if state.interrupt_requested:
            state.interrupt_requested = False

        state.status = "running"
        state.pending_task = task
        state.pending_max_turns = max_turns
        state.waiting_question = None
        state.waiting_options = []
        self.post_message(session_id, "user", task)
        provider = ProviderConfig(
            name=state.provider,
            model=state.model,
            api_key=self._resolve_api_key(state.provider),
        )
        config = HardnessConfig(
            workspace_root=state.workspace_root,
            storage_root=state.storage_root,
            provider=provider,
            runtime=RuntimeConfig(max_turns=max_turns),
        )
        session_context = [
            Message(role=str(entry.get("role", "user")), content=str(entry.get("content", "")))
            for entry in state.messages[-10:]
        ]
        result = AgentLoop(config).run(
            task,
            session_messages=session_context,
            should_interrupt=lambda: state.interrupt_requested,
        )
        run_id = str(result.get("run_id", ""))
        if run_id:
            state.run_ids.append(run_id)
        state.latest_result = result
        self.post_message(session_id, "assistant", str(result.get("final_text", "")))
        self._update_state_from_result(state, result)
        self._save_checkpoint(state, task=task)
        result["session_status"] = state.status
        if state.waiting_question:
            result["waiting_question"] = state.waiting_question
            result["waiting_options"] = state.waiting_options
        return result

    def post_reply(self, session_id: str, content: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        state.last_user_reply = content
        entry = self.post_message(session_id, "user", content)
        return {
            "session_id": session_id,
            "status": state.status,
            "message": entry,
        }

    def resume_task(self, session_id: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        if state.status != "waiting_for_input" or not state.pending_task:
            raise ValueError("Session is not waiting for user input")

        reply = state.last_user_reply or "No additional clarification provided."
        question = state.waiting_question or "Need additional user clarification."
        resumed_task = (
            f"{state.pending_task}\n\n"
            f"Clarification requested: {question}\n"
            f"User reply: {reply}\n"
            "Continue from current progress without repeating already completed steps."
        )
        return self.run_task(session_id=session_id, task=resumed_task)

    def continue_task(self, session_id: str, max_turns: int | None = None) -> dict[str, Any]:
        state = self.get_session(session_id)
        if state.status != "paused" or not state.pending_task:
            raise ValueError("Session is not in paused state")
        turns = max_turns if max_turns is not None else state.pending_max_turns
        continuation = (
            f"{state.pending_task}\n\n"
            "CONTINUATION: The previous run was cut off at the turn limit. "
            "Continue from where it left off. Do not repeat steps already completed. "
            "Check what files already exist and build only what is missing."
        )
        return self.run_task(session_id=session_id, task=continuation, max_turns=turns)

    def request_interrupt(self, session_id: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        state.interrupt_requested = True
        return {
            "session_id": session_id,
            "interrupt_requested": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _update_state_from_result(self, state: SessionState, result: dict[str, Any]) -> None:
        stop_reason = str(result.get("stop_reason", ""))
        if stop_reason == "needs_clarification":
            state.status = "waiting_for_input"
            state.waiting_question = str(result.get("final_text", "Need additional clarification."))
            state.waiting_options = []
            return
        if stop_reason == "user_interrupted":
            state.status = "interrupted"
            state.interrupt_requested = False
            return
        if stop_reason == "max_turns_reached":
            state.status = "paused"
            # pending_task intentionally kept so continue_task can resume
            return
        state.status = "completed"
        state.pending_task = None
        state.waiting_question = None
        state.waiting_options = []
        state.last_user_reply = None

    def _save_checkpoint(self, state: SessionState, task: str) -> None:
        checkpoint_dir = state.storage_root / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        payload = {
            "session_id": state.session_id,
            "status": state.status,
            "task": task,
            "pending_task": state.pending_task,
            "waiting_question": state.waiting_question,
            "last_user_reply": state.last_user_reply,
            "run_ids": state.run_ids,
            "saved_at": datetime.now(UTC).isoformat(),
        }
        (checkpoint_dir / f"checkpoint-{timestamp}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def collect_events(self, session_id: str, run_id: str | None = None, after: int = 0) -> list[dict[str, Any]]:
        state = self.get_session(session_id)
        run_ids = [run_id] if run_id else list(state.run_ids)
        events: list[dict[str, Any]] = []
        for rid in run_ids:
            if not rid:
                continue
            run_file = state.storage_root / "runs" / f"{rid}.json"
            if not run_file.exists():
                continue
            payload = json.loads(run_file.read_text(encoding="utf-8"))
            for idx, event in enumerate(payload.get("events", [])):
                item = {
                    "session_id": session_id,
                    "run_id": rid,
                    "index": idx,
                    **event,
                }
                events.append(item)
        events.sort(key=lambda item: (item.get("timestamp", ""), item.get("run_id", ""), item.get("index", 0)))
        return [event for event in events if int(event.get("index", 0)) > after]

    async def stream_events(self, session_id: str, run_id: str | None = None, after: int = 0):
        cursor = after
        while True:
            batch = self.collect_events(session_id=session_id, run_id=run_id, after=cursor)
            for event in batch:
                cursor = max(cursor, int(event.get("index", cursor)))
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.8)

    def list_files(self, session_id: str, path: str = ".", recursive: bool = False) -> list[dict[str, Any]]:
        state = self.get_session(session_id)
        workspace_root = state.workspace_root
        target = (workspace_root / path).resolve()
        if not target.is_relative_to(workspace_root):
            raise ValueError("Requested path is outside workspace root")
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        results: list[dict[str, Any]] = []
        iterator = target.rglob("*") if recursive else target.iterdir()
        for item in sorted(iterator):
            results.append(
                {
                    "path": str(item.relative_to(workspace_root)).replace("\\", "/"),
                    "name": item.name,
                    "is_dir": item.is_dir(),
                }
            )
        return results

    def get_diff(self, session_id: str, path: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        workspace_root = state.workspace_root
        target = (workspace_root / path).resolve()
        if not target.is_relative_to(workspace_root):
            raise ValueError("Requested path is outside workspace root")
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        normalized = str(target.relative_to(workspace_root)).replace("\\", "/")
        current_text = target.read_text(encoding="utf-8")
        baseline = state.baseline_files.get(normalized)
        if baseline is None:
            state.baseline_files[normalized] = current_text
            return {
                "session_id": session_id,
                "path": normalized,
                "diff": "",
                "has_changes": False,
                "note": "Baseline captured. Re-run after edits to see diff.",
            }

        diff_lines = list(
            difflib.unified_diff(
                baseline.splitlines(),
                current_text.splitlines(),
                fromfile=f"a/{normalized}",
                tofile=f"b/{normalized}",
                lineterm="",
            )
        )
        return {
            "session_id": session_id,
            "path": normalized,
            "diff": "\n".join(diff_lines),
            "has_changes": bool(diff_lines),
        }

    def collect_metrics(self, session_id: str, run_id: str | None = None) -> dict[str, Any]:
        state = self.get_session(session_id)
        if run_id:
            run_file = state.storage_root / "runs" / f"{run_id}.json"
            if run_file.exists():
                payload = json.loads(run_file.read_text(encoding="utf-8"))
                events = payload.get("events", [])
                completed = [event for event in events if event.get("kind") == "run_completed"]
                if completed:
                    return {
                        "session_id": session_id,
                        "run_id": run_id,
                        "metrics": completed[-1].get("payload", {}).get("metrics", {}),
                    }
            return {"session_id": session_id, "run_id": run_id, "metrics": {}}

        latest = state.latest_result or {}
        return {
            "session_id": session_id,
            "run_id": latest.get("run_id"),
            "metrics": latest.get("metrics", {}),
        }

    def export_session(self, session_id: str) -> dict[str, Any]:
        state = self.get_session(session_id)
        return {
            "hardnessware_version": "0.1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "workspace": str(state.workspace_root),
            "provider": state.provider,
            "model": state.model,
            "status": state.status,
            "pending_task": state.pending_task,
            "pending_max_turns": state.pending_max_turns,
            "messages": state.messages,
        }

    def import_session(self, data: dict[str, Any]) -> SessionState:
        workspace = data.get("workspace", ".")
        provider = data.get("provider", "openrouter")
        model = data.get("model", "minimax/minimax-m2.7")
        state = self.create_session(provider=provider, model=model, workspace=workspace)
        messages = data.get("messages", [])
        if isinstance(messages, list):
            state.messages = [m for m in messages if isinstance(m, dict)]
        if data.get("status") == "paused" and data.get("pending_task"):
            state.pending_task = data["pending_task"]
            state.status = "paused"
            state.pending_max_turns = int(data.get("pending_max_turns", 8))
        return state

    def _resolve_api_key(self, provider: str) -> str | None:
        mapping = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_key = mapping.get(provider)
        if env_key:
            import os

            if os.environ.get(env_key):
                return os.environ[env_key]
        if not self.api_file.exists():
            return None
        parsed = self._parse_api_file(self.api_file)
        return parsed.get(provider.lower())

    @staticmethod
    def _parse_api_file(path: Path) -> dict[str, str]:
        content = path.read_text(encoding="utf-8")
        parsed: dict[str, str] = {}
        current_key: str | None = None
        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.endswith(":"):
                current_key = line[:-1].strip().lower()
                continue
            if current_key:
                parsed[current_key] = line
                current_key = None
        return parsed
