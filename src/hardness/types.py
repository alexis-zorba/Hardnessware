from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Role = Literal["system", "user", "assistant", "tool"]
FinishReason = Literal["stop", "tool_call", "error"]
DecisionType = Literal["tool", "final", "needs_clarification", "stop"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str
    name: str | None = None


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str = "tool-call"


@dataclass(slots=True)
class ModelResponse:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: FinishReason = "stop"
    usage: dict[str, Any] = field(default_factory=dict)
    stop_reason: str = "completed"
    decision_type: DecisionType = "final"


@dataclass(slots=True)
class ToolResult:
    name: str
    success: bool
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentTraceEvent:
    kind: str
    payload: dict[str, Any]


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: str
    parameters: dict[str, Any]


@dataclass(slots=True)
class RunMetrics:
    turns: int = 0
    tool_calls: int = 0
    tool_failures: int = 0
    repeated_actions: int = 0
    parse_failures: int = 0
    verified_writes: int = 0
    provider_calls: int = 0
    duplicate_action_rate: float = 0.0
    redundant_read_rate: float = 0.0
    final_after_success_rate: float = 0.0
    mean_turns_to_completion: float = 0.0
    no_progress_stop_count: int = 0
    success_recognized_rate: float = 0.0
    finalization_delay_rate: float = 0.0
    post_success_extra_action_rate: float = 0.0
    explicit_completion_rate: float = 0.0
    weak_final_rate: float = 0.0
    finalization_correctness_rate: float = 0.0
    finalization_quality_rate: float = 0.0


@dataclass(slots=True)
class RoutingDecision:
    profile_name: str
    provider: str
    model: str
    reason: str
