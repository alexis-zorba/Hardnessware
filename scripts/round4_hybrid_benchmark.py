from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


PRICING = {
    "minimax/minimax-m2.7": {"input_per_million": 0.30, "output_per_million": 1.20},
    "anthropic/claude-sonnet-4.6": {"input_per_million": 3.0, "output_per_million": 15.0},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round4 benchmark: MiniMax-only vs MiniMax+Sonnet escalation")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round4.json")
    parser.add_argument("--output", default="docs/hardness_round4_hybrid_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    keys = _parse_api_file(root / "secrets" / "API.txt")

    baseline = run_mode(
        tasks=tasks,
        root=root,
        storage_name=".hardness-round4-minimax",
        provider_name="openrouter",
        model_name="minimax/minimax-m2.7",
        api_key=keys.get("openrouter"),
    )

    hybrid = run_hybrid_mode(tasks=tasks, root=root, api_key=keys.get("openrouter"))

    payload = {
        "task_file": args.task_file,
        "tasks_total": len(tasks),
        "baseline_minimax_only": baseline,
        "hybrid_minimax_plus_sonnet": hybrid,
    }
    (root / args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"baseline": baseline["aggregate"], "hybrid": hybrid["aggregate"]}, indent=2, ensure_ascii=False))


def run_hybrid_mode(tasks: list[dict], root: Path, api_key: str | None) -> dict:
    minimax_agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / ".hardness-round4-hybrid-minimax",
            provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key=api_key),
        )
    )
    sonnet_agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / ".hardness-round4-hybrid-sonnet",
            provider=ProviderConfig(name="openrouter", model="anthropic/claude-sonnet-4.6", api_key=api_key),
        )
    )

    task_results: list[dict] = []
    escalated = 0
    for task in tasks:
        first = minimax_agent.run(task["task"])
        usage_first = extract_usage(root / ".hardness-round4-hybrid-minimax" / "runs" / f"{first['run_id']}.json")
        final = first
        usage_final = usage_first
        model_used = "minimax/minimax-m2.7"

        if should_escalate(first):
            escalated += 1
            second = sonnet_agent.run(task["task"])
            usage_second = extract_usage(root / ".hardness-round4-hybrid-sonnet" / "runs" / f"{second['run_id']}.json")
            final = second
            usage_final = merge_usage(usage_first, usage_second)
            model_used = "hybrid:escalated_to_sonnet"

        task_results.append(
            {
                "id": task["id"],
                "name": task["name"],
                "status": final.get("status"),
                "stop_reason": final.get("stop_reason"),
                "metrics": final.get("metrics", {}),
                "usage": usage_final,
                "estimated_cost_usd": estimate_cost_for_hybrid(usage_first, usage_final),
                "model_used": model_used,
            }
        )

    aggregate = aggregate_results(task_results)
    aggregate["escalation_count"] = escalated
    aggregate["escalation_rate"] = round(escalated / len(tasks), 4) if tasks else 0.0
    return {"tasks": task_results, "aggregate": aggregate}


def run_mode(
    tasks: list[dict],
    root: Path,
    storage_name: str,
    provider_name: str,
    model_name: str,
    api_key: str | None,
) -> dict:
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / storage_name,
            provider=ProviderConfig(name=provider_name, model=model_name, api_key=api_key),
        )
    )
    task_results: list[dict] = []
    for task in tasks:
        result = agent.run(task["task"])
        usage = extract_usage(root / storage_name / "runs" / f"{result['run_id']}.json")
        task_results.append(
            {
                "id": task["id"],
                "name": task["name"],
                "status": result.get("status"),
                "stop_reason": result.get("stop_reason"),
                "metrics": result.get("metrics", {}),
                "usage": usage,
                "estimated_cost_usd": estimate_cost(usage, model_name),
                "model_used": model_name,
            }
        )
    return {"tasks": task_results, "aggregate": aggregate_results(task_results)}


def should_escalate(result: dict) -> bool:
    if result.get("status") != "ok":
        return True
    stop_reason = result.get("stop_reason")
    metrics = result.get("metrics", {})
    turns = int(metrics.get("turns", 0) or 0)
    final_after_success_rate = float(metrics.get("final_after_success_rate", 0.0) or 0.0)
    duplicate_action_rate = float(metrics.get("duplicate_action_rate", 0.0) or 0.0)
    no_progress = int(metrics.get("no_progress_stop_count", 0) or 0)
    if stop_reason not in {"stop", "write_completed", "completed"}:
        return True
    if turns >= 4:
        return True
    if final_after_success_rate < 1.0 and turns >= 3:
        return True
    if duplicate_action_rate > 0.0 or no_progress > 0:
        return True
    return False


def extract_usage(run_file: Path) -> dict:
    if not run_file.exists():
        return {}
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    found = False
    for event in payload.get("events", []):
        if event.get("kind") != "provider_response":
            continue
        usage = event.get("payload", {}).get("usage") or {}
        if not isinstance(usage, dict):
            continue
        found = True
        usage_total["prompt_tokens"] += int(usage.get("prompt_tokens", 0) or 0)
        usage_total["completion_tokens"] += int(usage.get("completion_tokens", 0) or 0)
        usage_total["total_tokens"] += int(usage.get("total_tokens", 0) or 0)
    return usage_total if found else {}


def merge_usage(first: dict, second: dict) -> dict:
    return {
        "prompt_tokens": int(first.get("prompt_tokens", 0)) + int(second.get("prompt_tokens", 0)),
        "completion_tokens": int(first.get("completion_tokens", 0)) + int(second.get("completion_tokens", 0)),
        "total_tokens": int(first.get("total_tokens", 0)) + int(second.get("total_tokens", 0)),
    }


def estimate_cost(usage: dict, model_name: str) -> float | None:
    if not usage:
        return None
    pricing = PRICING[model_name]
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    cost = (prompt_tokens / 1_000_000) * pricing["input_per_million"]
    cost += (completion_tokens / 1_000_000) * pricing["output_per_million"]
    return round(cost, 8)


def estimate_cost_for_hybrid(first_usage: dict, merged_usage: dict) -> float | None:
    if not merged_usage:
        return None
    # hybrid cost = first pass (MiniMax) + optional second pass (Sonnet)
    if merged_usage == first_usage:
        return estimate_cost(first_usage, "minimax/minimax-m2.7")
    sonnet_usage = {
        "prompt_tokens": int(merged_usage.get("prompt_tokens", 0)) - int(first_usage.get("prompt_tokens", 0)),
        "completion_tokens": int(merged_usage.get("completion_tokens", 0)) - int(first_usage.get("completion_tokens", 0)),
        "total_tokens": int(merged_usage.get("total_tokens", 0)) - int(first_usage.get("total_tokens", 0)),
    }
    c1 = estimate_cost(first_usage, "minimax/minimax-m2.7") or 0.0
    c2 = estimate_cost(sonnet_usage, "anthropic/claude-sonnet-4.6") or 0.0
    return round(c1 + c2, 8)


def aggregate_results(results: list[dict]) -> dict:
    total = len(results)
    completion = [item for item in results if item.get("status") == "ok"]
    stop_reasons = Counter(item.get("stop_reason") or "none" for item in results)

    completion_rate = (len(completion) / total) if total else 0.0
    mean_turns = avg([item.get("metrics", {}).get("turns", 0) for item in results])
    duplicate = avg([item.get("metrics", {}).get("duplicate_action_rate", 0.0) for item in results])
    redundant = avg([item.get("metrics", {}).get("redundant_read_rate", 0.0) for item in results])
    final_rate = avg([item.get("metrics", {}).get("final_after_success_rate", 0.0) for item in results])
    costs = [item.get("estimated_cost_usd") for item in results if item.get("estimated_cost_usd") is not None]

    return {
        "completion_rate": round(completion_rate, 4),
        "mean_turns_per_task": round(mean_turns, 4),
        "duplicate_action_rate_avg": round(duplicate, 4),
        "redundant_read_rate_avg": round(redundant, 4),
        "final_after_success_rate_avg": round(final_rate, 4),
        "stop_reason_distribution": dict(stop_reasons),
        "mean_cost_per_task_usd": round(avg(costs), 8) if costs else None,
        "total_estimated_cost_usd": round(sum(costs), 8) if costs else None,
        "cost_coverage_tasks": len(costs),
    }


def avg(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()

