from __future__ import annotations

import ast
import json
import py_compile
from dataclasses import dataclass
from typing import Any, Protocol

from hardness.policy import PolicyEngine, PolicyError
from hardness.types import ToolDefinition, ToolResult


class Tool(Protocol):
    name: str
    description: str
    risk_level: str
    parameters: dict[str, Any]

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        ...


@dataclass(slots=True)
class ReadTool:
    policy: PolicyEngine
    name: str = "read"
    description: str = "Read a UTF-8 text file from the workspace."
    risk_level: str = "low"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path = self.policy.authorize_path(str(arguments["path"]))
        self.policy.validate_read_size(path.stat().st_size)
        return ToolResult(name=self.name, success=True, content=path.read_text(encoding="utf-8"), metadata={"path": str(path)})


@dataclass(slots=True)
class WriteTool:
    policy: PolicyEngine
    name: str = "write"
    description: str = "Write UTF-8 text to a workspace file."
    risk_level: str = "medium"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path = self.policy.authorize_path(str(arguments["path"]), write=True)
        content = str(arguments["content"])
        self.policy.validate_write_size(len(content.encode("utf-8")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(name=self.name, success=True, content=f"Wrote {len(content)} chars", metadata={"path": str(path), "verify_path": str(path)})


@dataclass(slots=True)
class SearchTool:
    policy: PolicyEngine
    name: str = "search"
    description: str = "Search for a substring inside workspace text files."
    risk_level: str = "low"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        root = self.policy.authorize_path(str(arguments.get("path", ".")))
        query = str(arguments["query"])
        matches: list[dict[str, Any]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if query in text:
                matches.append({"path": str(path), "count": text.count(query)})
                if len(matches) >= self.policy.config.max_search_results:
                    break
        self.policy.validate_search_budget(len(matches))
        return ToolResult(name=self.name, success=True, content=json.dumps(matches, ensure_ascii=False), metadata={"query": query, "promote": True, "title": f"search:{query}", "result_count": len(matches)})


@dataclass(slots=True)
class PythonCheckTool:
    """Syntax-checks a .py file via AST parse + py_compile.
    Safe: pure Python, no execution of user code."""

    policy: PolicyEngine
    name: str = "py_check"
    description: str = (
        "Check a Python file for syntax errors using AST parse and py_compile. "
        "Call this after writing any .py file to catch errors immediately."
    )
    risk_level: str = "low"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        raw = str(arguments["path"])
        try:
            path = self.policy.authorize_path(raw)
        except PolicyError as exc:
            return ToolResult(name=self.name, success=False, content=f"Policy error: {exc}", metadata={"path": raw})

        if not path.exists():
            return ToolResult(name=self.name, success=False, content=f"File not found: {raw}", metadata={"path": raw})
        if path.suffix != ".py":
            return ToolResult(name=self.name, success=False, content=f"Not a Python file: {raw}", metadata={"path": raw})

        try:
            source = path.read_text(encoding="utf-8")
        except Exception as exc:
            return ToolResult(name=self.name, success=False, content=f"Read error: {exc}", metadata={"path": raw})

        # AST parse — catches SyntaxError before any execution
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            msg = f"SyntaxError line {exc.lineno}: {exc.msg}"
            if exc.text:
                msg += f"\n  >> {exc.text.rstrip()}"
            return ToolResult(name=self.name, success=False, content=msg, metadata={"path": raw, "error_type": "SyntaxError", "line": exc.lineno})

        # py_compile — validates bytecode compilation
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            return ToolResult(name=self.name, success=False, content=f"CompileError: {exc}", metadata={"path": raw, "error_type": "CompileError"})

        lines = len(source.splitlines())
        return ToolResult(
            name=self.name,
            success=True,
            content=f"OK — {path.name} is valid Python ({lines} lines)",
            metadata={"path": raw, "lines": lines},
        )


@dataclass(slots=True)
class ListTool:
    """Lists files and directories at a given workspace path."""

    policy: PolicyEngine
    name: str = "list"
    description: str = (
        "List files and subdirectories at a workspace path. "
        "Use this to discover what files already exist before reading or writing."
    )
    risk_level: str = "low"
    parameters: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.parameters = {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        raw = str(arguments.get("path", "."))
        try:
            root = self.policy.authorize_path(raw)
        except PolicyError as exc:
            return ToolResult(name=self.name, success=False, content=f"Policy error: {exc}", metadata={"path": raw})

        if not root.exists():
            return ToolResult(name=self.name, success=False, content=f"Path not found: {raw}", metadata={})

        entries: list[dict[str, Any]] = []
        try:
            workspace = self.policy.config.workspace_root.resolve()
            for item in sorted(root.iterdir()):
                try:
                    rel = str(item.relative_to(workspace)).replace("\\", "/")
                except ValueError:
                    rel = str(item)
                entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file", "path": rel})
        except PermissionError as exc:
            return ToolResult(name=self.name, success=False, content=str(exc), metadata={})

        return ToolResult(
            name=self.name,
            success=True,
            content=json.dumps(entries, ensure_ascii=False),
            metadata={"path": raw, "count": len(entries)},
        )


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def schema(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "risk_level": tool.risk_level,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools[name]
        return tool.execute(arguments)

    def definitions(self) -> list[ToolDefinition]:
        return [ToolDefinition(**item) for item in self.schema()]
