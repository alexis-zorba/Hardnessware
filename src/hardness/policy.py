from __future__ import annotations

from pathlib import Path

from hardness.config import PolicyConfig


class PolicyError(Exception):
    pass


class PolicyEngine:
    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    def authorize_path(self, raw_path: str, write: bool = False) -> Path:
        path = (self.config.workspace_root / raw_path).resolve()
        workspace_root = self.config.workspace_root.resolve()
        if workspace_root not in path.parents and path != workspace_root:
            raise PolicyError(f"Path escapes workspace: {raw_path}")
        if write and not self.config.allow_writes:
            raise PolicyError("Writes are disabled by policy")
        if path.suffix and path.suffix not in self.config.allowed_extensions:
            raise PolicyError(f"Extension not allowed: {path.suffix}")
        if write and not self._is_writable(path):
            raise PolicyError(f"Write path not allowed: {raw_path}")
        return path

    def validate_read_size(self, size_bytes: int) -> None:
        if size_bytes > self.config.max_read_bytes:
            raise PolicyError(f"Read exceeds limit of {self.config.max_read_bytes} bytes")

    def validate_write_size(self, size_bytes: int) -> None:
        if size_bytes > self.config.max_write_bytes:
            raise PolicyError(f"Write exceeds limit of {self.config.max_write_bytes} bytes")

    def validate_search_budget(self, results: int) -> None:
        if results > self.config.max_search_results:
            raise PolicyError(f"Search results exceed limit of {self.config.max_search_results}")

    def _is_writable(self, path: Path) -> bool:
        workspace_root = self.config.workspace_root.resolve()
        for allowed in self.config.writable_roots:
            allowed_path = (workspace_root / allowed).resolve()
            if allowed_path == path or allowed_path in path.parents:
                return True
        return False
