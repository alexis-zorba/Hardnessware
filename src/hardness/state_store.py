from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.runs_root = self.root / "runs"
        self.notes_root = self.root / "memory" / "notes"
        self.artifacts_root = self.root / "memory" / "artifacts"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs_root.mkdir(parents=True, exist_ok=True)
        self.notes_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_run_id() -> str:
        return datetime.now(UTC).strftime("run-%Y%m%dT%H%M%S%fZ")

    def create_run(self, task: str, run_id: str | None = None) -> str:
        if run_id is None:
            run_id = self.new_run_id()
        payload = {
            "run_id": run_id,
            "task": task,
            "created_at": datetime.now(UTC).isoformat(),
            "events": [],
        }
        self._write_json(self.runs_root / f"{run_id}.json", payload)
        return run_id

    def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        path = self.runs_root / f"{run_id}.json"
        payload = self._read_json(path)
        payload.setdefault("events", []).append(event)
        self._write_json(path, payload)

    def save_note(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.notes_root / f"{name}.json"
        self._write_json(path, payload)
        return path

    def list_notes(self) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        for path in sorted(self.notes_root.glob("*.json")):
            note = self._read_json(path)
            note["_path"] = str(path)
            notes.append(note)
        return notes

    def save_artifact(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.artifacts_root / f"{name}.json"
        self._write_json(path, payload)
        return path

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = self._normalize(payload)
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _normalize(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._normalize(asdict(value))
        if isinstance(value, dict):
            return {key: self._normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize(item) for item in value]
        return value

