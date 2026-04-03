from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


PRICING = {
    "input_per_million": 0.30,
    "output_per_million": 1.20,
}

PRICING_BY_MODEL = {
    "minimax/minimax-m2.7": {"input_per_million": 0.30, "output_per_million": 1.20},
    "anthropic/claude-sonnet-4.6": {"input_per_million": 3.0, "output_per_million": 15.0},
}


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    task_file = root / "HARDNESS" / "05_synthesis" / "task_suite.json"
    api_file = root / "secrets" / "API.txt"
    storage_root = root / args.storage
    out_file = root / args.output

    tasks_payload = json.loads(task_file.read_text(encoding="utf-8"))
    tasks = tasks_payload["tasks"]
    keys = _parse_api_file(api_file)
    pricing = PRICING_BY_MODEL.get(args.model, PRICING)

    config = HardnessConfig(
        workspace_root=root,
        storage_root=storage_root,
        provider=ProviderConfig(
            name=args.provider,
            model=args.model,
            api_key=keys.get("openrouter"),
        ),
    )
    agent = AgentLoop(config)

    task_results: list[dict] = []
    for task in tasks:
        result = agent.run(task["task"])
        usage = extract_usage(storage_root / "runs" / f"{result['run_id']}.json")
        task_cost = estimate_cost(usage, pricing)
        task_results.append(
            {
                "id": task["id"],
                "name": task["name"],
                "task": task["task"],
                "status": result.get("status"),
                "stop_reason": result.get("stop_reason"),
                "metrics": result.get("metrics", {}),
                "error": result.get("error"),
                "usage": usage,
                "estimated_cost_usd": task_cost,
            }
        )

    aggregate = build_aggregate(task_results)
    payload = {
        "provider": args.provider,
        "model": args.model,
        "pricing": pricing,
        "tasks_total": len(task_results),
        "tasks": task_results,
        "aggregate": aggregate,
    }
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["aggregate"], indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HARDNESS validation suite and aggregate metrics")
    parser.add_argument("--provider", default="openrouter")
    parser.add_argument("--model", default="minimax/minimax-m2.7")
    parser.add_argument("--storage", default=".hardness-round2")
    parser.add_argument("--output", default="docs/hardness_round2_metrics.json")
    return parser.parse_args()


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


def estimate_cost(usage: dict, pricing: dict[str, float]) -> float | None:
    if not usage:
        return None
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    cost = (prompt_tokens / 1_000_000) * pricing["input_per_million"]
    cost += (completion_tokens / 1_000_000) * pricing["output_per_million"]
    return round(cost, 8)


def build_aggregate(results: list[dict]) -> dict:
    total = len(results)
    completed = [item for item in results if item.get("status") == "ok"]
    completion_rate = (len(completed) / total) if total else 0.0

    turns = [item.get("metrics", {}).get("turns", 0) for item in results]
    duplicate_rates = [item.get("metrics", {}).get("duplicate_action_rate", 0.0) for item in results]
    redundant_rates = [item.get("metrics", {}).get("redundant_read_rate", 0.0) for item in results]
    final_rates = [item.get("metrics", {}).get("final_after_success_rate", 0.0) for item in results]

    stop_reasons = Counter(item.get("stop_reason") or "none" for item in results)
    failure_modes = Counter()
    for item in results:
        if item.get("status") != "ok":
            failure_modes["provider_error"] += 1
        reason = item.get("stop_reason")
        if reason in {"repeated_action_limit", "redundant_read_suppressed", "no_progress_limit", "tool_failure_limit"}:
            failure_modes[reason] += 1

    known_costs = [item["estimated_cost_usd"] for item in results if item.get("estimated_cost_usd") is not None]

    return {
        "completion_rate": round(completion_rate, 4),
        "mean_turns_per_task": round(avg(turns), 4),
        "duplicate_action_rate_avg": round(avg(duplicate_rates), 4),
        "redundant_read_rate_avg": round(avg(redundant_rates), 4),
        "final_after_success_rate_avg": round(avg(final_rates), 4),
        "stop_reason_distribution": dict(stop_reasons),
        "failure_modes_top": dict(failure_modes.most_common(5)),
        "mean_cost_per_task_usd": round(avg(known_costs), 8) if known_costs else None,
        "total_estimated_cost_usd": round(sum(known_costs), 8) if known_costs else None,
        "cost_coverage_tasks": len(known_costs),
    }


def avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


if __name__ == "__main__":
    main()
