from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha1
from typing import Iterable

from hardness.config import MemoryConfig
from hardness.state_store import StateStore
from hardness.types import Message, ToolResult


@dataclass(slots=True)
class MemorySnapshot:
    session_messages: list[Message] = field(default_factory=list)
    indexed_notes: list[dict] = field(default_factory=list)


class MemoryManager:
    def __init__(self, store: StateStore, config: MemoryConfig) -> None:
        self.store = store
        self.config = config
        self.session_messages: list[Message] = []

    def append_session(self, message: Message) -> None:
        self.session_messages.append(message)
        overflow = len(self.session_messages) - self.config.max_events_in_session
        if overflow > 0:
            self.session_messages = self.session_messages[overflow:]

    def retrieve(self, query: str) -> MemorySnapshot:
        notes = self.store.list_notes()
        scored = sorted(notes, key=lambda item: self._score(query, item), reverse=True)
        selected = [note for note in scored if self._score(query, note) > 0][: self.config.max_notes_in_context]
        return MemorySnapshot(session_messages=list(self.session_messages), indexed_notes=selected)

    def store_artifact(self, run_id: str, tool_result: ToolResult) -> None:
        artifact_name = f"{run_id}-{tool_result.name}-{datetime.now(UTC).strftime('%H%M%S%f')}"
        self.store.save_artifact(
            artifact_name,
            {
                "created_at": datetime.now(UTC).isoformat(),
                "tool": tool_result.name,
                "success": tool_result.success,
                "content": tool_result.content,
                "metadata": tool_result.metadata,
            },
        )

    def promote_verified_note(self, title: str, content: str, source: str) -> None:
        note_id = sha1(f"{title}:{source}".encode("utf-8")).hexdigest()[:12]
        self.store.save_note(
            note_id,
            {
                "title": title,
                "content": content,
                "source": source,
                "verified": True,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    def _score(self, query: str, note: dict) -> int:
        haystack = f"{note.get('title', '')} {note.get('content', '')}".lower()
        tokens = [token for token in re.split(r"\W+", query.lower()) if token]
        return sum(1 for token in tokens if token in haystack)

    def render_for_prompt(self, snapshot: MemorySnapshot) -> str:
        chunks: list[str] = []
        if snapshot.indexed_notes:
            chunks.append("Relevant notes:")
            for note in snapshot.indexed_notes:
                chunks.append(f"- {note['title']}: {note['content']}")
        if snapshot.session_messages:
            chunks.append("Recent session state:")
            for message in snapshot.session_messages:
                chunks.append(f"- {message.role}: {message.content}")
        return "\n".join(chunks)


def iter_verified_facts(tool_results: Iterable[ToolResult]) -> list[tuple[str, str]]:
    facts: list[tuple[str, str]] = []
    for result in tool_results:
        if result.success and result.metadata.get("promote"):
            facts.append((result.metadata.get("title", result.name), result.content))
    return facts

