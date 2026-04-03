from __future__ import annotations

from hardness.memory import MemorySnapshot
from hardness.types import Message


SYSTEM_PROMPT = """You are HARDNESS, a provider-agnostic software agent harness.
Follow a disciplined loop: think, act, verify, update.
Use tools only when necessary and stay within policy constraints.

Output contract (strict):
- Choose exactly one of: tool, final, needs_clarification, stop
- If a successful tool already satisfies the task, use final
- Do not repeat the same read/search action unless new information justifies it

Multi-file development rules:
- Before writing a file that imports from another module, read that module first
  to verify the exact attribute names, class names, and method signatures you will reference
- After writing any .py file, call py_check on it immediately to catch syntax errors
- If py_check reports an error, fix it in the next tool call before moving on
- Use list to discover existing files before writing, to avoid overwriting work or missing context
- When writing file B that depends on file A, explicitly confirm the attribute/method names
  from file A are consistent with what you write in file B

Cross-file consistency checklist (apply mentally before each write):
1. What does this file import? → Read those files first
2. What attributes/methods does this file reference? → Verify they exist in the source
3. After writing → call py_check
"""


def build_messages(task: str, memory: MemorySnapshot, tool_schemas: list[dict]) -> list[Message]:
    parts = [SYSTEM_PROMPT.strip()]
    if memory.indexed_notes:
        parts.append("Relevant durable memory:")
        parts.extend(f"- {note['title']}: {note['content']}" for note in memory.indexed_notes)
    if memory.session_messages:
        parts.append("Recent session state:")
        parts.extend(f"- {message.role}: {message.content}" for message in memory.session_messages)
    parts.append("Available tools:")
    parts.extend(f"- {tool['name']}: {tool['description']} ({tool['risk_level']})" for tool in tool_schemas)
    return [Message(role="system", content="\n".join(parts)), Message(role="user", content=task)]


def build_followup_user_message(task: str, recent_tool_summary: str, require_final: bool = False) -> Message:
    instructions = [
        f"Original task: {task}",
        f"Recent tool result: {recent_tool_summary}",
        "Decide using exactly one mode: tool, final, needs_clarification, or stop.",
    ]
    if require_final:
        instructions.extend(
            [
                "The goal appears to be achieved.",
                "Do NOT use any tool unless strictly necessary and materially different from the successful action.",
                "Provide a final answer that:",
                "- clearly states the result",
                "- references the action/tool that led to the result",
                "- explicitly confirms task completion",
                "- does not introduce new steps",
            ]
        )
    return Message(role="user", content="\n".join(instructions))
