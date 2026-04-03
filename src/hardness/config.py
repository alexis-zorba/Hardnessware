from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProviderConfig:
    name: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: int = 60


@dataclass(slots=True)
class ModelProfile:
    name: str
    provider: str
    model: str
    role: str
    escalation_triggers: tuple[str, ...] = ()


@dataclass(slots=True)
class MemoryConfig:
    max_notes_in_context: int = 12
    max_events_in_session: int = 20


@dataclass(slots=True)
class RuntimeConfig:
    max_turns: int = 4
    max_consecutive_tool_failures: int = 2
    max_repeated_identical_actions: int = 2
    max_no_progress_turns: int = 2


@dataclass(slots=True)
class PolicyConfig:
    workspace_root: Path
    allow_writes: bool = True
    allowed_extensions: tuple[str, ...] = (
        ".md",
        ".txt",
        ".json",
        ".py",
        ".toml",
        ".yaml",
        ".yml",
    )
    writable_roots: tuple[str, ...] = (".",)
    max_read_bytes: int = 64_000
    max_write_bytes: int = 64_000
    max_search_results: int = 25


@dataclass(slots=True)
class HardnessConfig:
    workspace_root: Path
    storage_root: Path
    provider: ProviderConfig
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    policy: PolicyConfig | None = None
    model_profiles: tuple[ModelProfile, ...] = ()
    enable_opportunistic_qwen: bool = False

    def __post_init__(self) -> None:
        self.workspace_root = self.workspace_root.resolve()
        self.storage_root = self.storage_root.resolve()
        if self.policy is None:
            self.policy = PolicyConfig(workspace_root=self.workspace_root)
