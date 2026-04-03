from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.config import HardnessConfig, ProviderConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HARDNESS prototype CLI")
    parser.add_argument("task", help="Task or prompt to run")
    parser.add_argument("--provider", default="mock", choices=["mock", "openai", "groq", "openrouter"])
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--storage", default=".hardness")
    parser.add_argument("--api-file", default="secrets/API.txt")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    provider = ProviderConfig(
        name=args.provider,
        model=args.model,
        api_key=_resolve_api_key(args.provider, Path(args.api_file)),
    )
    config = HardnessConfig(
        workspace_root=Path(args.workspace),
        storage_root=Path(args.storage),
        provider=provider,
    )
    result = AgentLoop(config).run(args.task)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _resolve_api_key(provider: str, api_file: Path) -> str | None:
    mapping = {
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    env_name = mapping.get(provider)
    if env_name and os.environ.get(env_name):
        return os.environ.get(env_name)
    if api_file.exists():
        parsed = _parse_api_file(api_file)
        return parsed.get(provider.lower())
    return None


def _parse_api_file(path: Path) -> dict[str, str]:
    content = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    parsed: dict[str, str] = {}
    current_key: str | None = None
    for line in lines:
        if line.endswith(":"):
            current_key = line[:-1].strip().lower()
            continue
        if current_key:
            parsed[current_key] = line
            current_key = None
    return parsed


if __name__ == "__main__":
    main()
