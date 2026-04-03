from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from hardness.config import ProviderConfig
from hardness.types import Message, ModelResponse, ToolCall


class ProviderError(Exception):
    pass


class ProviderCompatibilityError(ProviderError):
    pass


class ProviderAdapter(Protocol):
    def generate(self, messages: list[Message], tools: list[dict]) -> ModelResponse:
        ...

    def run_probe(self, probe_kind: str) -> dict[str, object]:
        ...


@dataclass(slots=True)
class MockProviderAdapter:
    SUPPORTED_TOOLS = {"read", "search"}

    def generate(self, messages: list[Message], tools: list[dict]) -> ModelResponse:
        last = messages[-1].content if messages else ""
        lowered = last.lower()
        supported = {t["name"] for t in tools} if tools else self.SUPPORTED_TOOLS
        if lowered.startswith("read "):
            tool_name = "read"
            if tool_name not in supported:
                raise ProviderError(f"Unsupported tool requested: {tool_name}")
            return ModelResponse(tool_calls=[ToolCall(name="read", arguments={"path": last[5:].strip()})], finish_reason="tool_call", decision_type="tool")
        if lowered.startswith("search "):
            tool_name = "search"
            if tool_name not in supported:
                raise ProviderError(f"Unsupported tool requested: {tool_name}")
            return ModelResponse(tool_calls=[ToolCall(name="search", arguments={"query": last[7:].strip(), "path": "."})], finish_reason="tool_call", decision_type="tool")
        if "recent tool result:" in lowered:
            return ModelResponse(text="Final answer based on the successful tool result.", finish_reason="stop", decision_type="final")
        return ModelResponse(text=f"Mock response: {last}", finish_reason="stop", decision_type="final")

    def run_probe(self, probe_kind: str) -> dict[str, object]:
        return {"probe_kind": probe_kind, "provider": "mock", "ok": True}


@dataclass(slots=True)
class OpenAICompatibleAdapter:
    config: ProviderConfig

    def generate(self, messages: list[Message], tools: list[dict]) -> ModelResponse:
        if not self.config.api_key:
            raise ProviderError(f"Missing API key for provider {self.config.name}")
        supported_names = {t["name"] for t in tools} if tools else set()
        url = (self.config.base_url or "https://api.openai.com/v1") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "tools": [self._to_tool_spec(tool) for tool in tools],
            "tool_choice": "auto",
        }
        body = self._post_json(url, payload)

        try:
            choice = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Invalid provider response envelope from {self.config.name}") from exc
        tool_calls = []
        for tool_call in choice.get("tool_calls", []):
            try:
                raw_arguments = tool_call["function"].get("arguments", "{}")
                parsed_arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                if not isinstance(parsed_arguments, dict):
                    raise ValueError("Tool arguments must decode to an object")
                tool_name = tool_call["function"]["name"]
                if supported_names and tool_name not in supported_names:
                    raise ProviderError(f"Provider returned unsupported tool: {tool_name}")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ProviderError(f"Malformed tool call from {self.config.name}") from exc
            tool_calls.append(
                ToolCall(
                    name=tool_name,
                    arguments=parsed_arguments,
                    call_id=tool_call.get("id", "tool-call"),
                )
            )
        finish_reason = "tool_call" if tool_calls else "stop"
        decision_type = "tool" if tool_calls else "final"
        return ModelResponse(
            text=choice.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=body.get("usage", {}),
            stop_reason=body["choices"][0].get("finish_reason", "completed"),
            decision_type=decision_type,
        )

    def run_probe(self, probe_kind: str) -> dict[str, object]:
        if not self.config.api_key:
            raise ProviderCompatibilityError(f"Missing API key for provider {self.config.name}")
        url = (self.config.base_url or "https://api.openai.com/v1") + "/chat/completions"
        payload = self._build_probe_payload(probe_kind)
        try:
            body = self._post_json(url, payload)
            return {
                "provider": self.config.name,
                "model": self.config.model,
                "probe_kind": probe_kind,
                "ok": True,
                "has_choices": bool(body.get("choices")),
            }
        except ProviderError as exc:
            return {
                "provider": self.config.name,
                "model": self.config.model,
                "probe_kind": probe_kind,
                "ok": False,
                "error": str(exc),
            }

    def _to_tool_spec(self, tool: dict) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
            },
        }

    def _build_probe_payload(self, probe_kind: str) -> dict:
        base_messages = [{"role": "user", "content": "Reply with OK."}]
        payload = {
            "model": self.config.model,
            "messages": base_messages,
        }
        if probe_kind == "basic":
            return payload
        if probe_kind == "structured":
            payload["response_format"] = {"type": "json_object"}
            payload["messages"] = [{"role": "user", "content": 'Return JSON: {"status":"ok"}'}]
            return payload
        if probe_kind == "tool":
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "ping",
                        "description": "Return a ping acknowledgement",
                        "parameters": {
                            "type": "object",
                            "properties": {"value": {"type": "string"}},
                            "required": ["value"],
                            "additionalProperties": False,
                        },
                    },
                }
            ]
            payload["tool_choice"] = "auto"
            payload["messages"] = [{"role": "user", "content": "Call ping with value ok."}]
            return payload
        raise ProviderCompatibilityError(f"Unsupported probe kind: {probe_kind}")

    def _post_json(self, url: str, payload: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:800]
            raise ProviderError(f"provider={self.config.name} model={self.config.model} status={exc.code} body={body}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"provider={self.config.name} model={self.config.model} error={exc}") from exc


def build_provider_adapter(config: ProviderConfig) -> ProviderAdapter:
    normalized = config.name.lower()
    if normalized == "mock":
        return MockProviderAdapter()
    if normalized == "openai":
        return OpenAICompatibleAdapter(config=config)
    if normalized == "groq":
        return OpenAICompatibleAdapter(
            config=ProviderConfig(
                name="groq",
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url or "https://api.groq.com/openai/v1",
                timeout_seconds=config.timeout_seconds,
            )
        )
    if normalized == "openrouter":
        return OpenAICompatibleAdapter(
            config=ProviderConfig(
                name="openrouter",
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url or "https://openrouter.ai/api/v1",
                timeout_seconds=config.timeout_seconds,
            )
        )
    raise ProviderError(f"Unsupported provider: {config.name}")
