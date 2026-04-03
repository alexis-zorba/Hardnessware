from __future__ import annotations

import argparse
import json
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


PRICING = {
    "minimax/minimax-m2.7": {"input_per_million": 0.30, "output_per_million": 1.20},
    "anthropic/claude-sonnet-4.6": {"input_per_million": 3.0, "output_per_million": 15.0},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round7 ROI benchmark: MiniMax-only vs MiniMax+Sonnet escalation")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round4.json")
    parser.add_argument("--runs-per-task", type=int, default=2)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--output", default="docs/hardness_round7_roi_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    api_key = _parse_api_file(root / "secrets" / "API.txt").get("openrouter")

    baseline = run_mode(
        tasks=tasks,
        root=root,
        runs_per_task=args.runs_per_task,
        storage_name=".hardness-round7-baseline",
        model_name="minimax/minimax-m2.7",
        api_key=api_key,
    )
    hybrid = run_hybrid_mode(tasks=tasks, root=root, runs_per_task=args.runs_per_task, api_key=api_key)

    decision = build_decision(baseline["aggregate"], hybrid["aggregate"])
    payload = {
        "phase": "round7_premium_roi",
        "task_file": args.task_file,
        "runs_per_task": args.runs_per_task,
        "tasks_total": len(tasks),
        "baseline_minimax_only": baseline,
        "hybrid_minimax_plus_sonnet": hybrid,
        "decision": decision,
    }
    (root / args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(decision, indent=2, ensure_ascii=False))


def run_mode(
    tasks: list[dict],
    root: Path,
    runs_per_task: int,
    storage_name: str,
    model_name: str,
    api_key: str | None,
) -> dict:
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / storage_name,
            provider=ProviderConfig(name="openrouter", model=model_name, api_key=api_key),
        )
    )
    rows: list[dict] = []
    for task in tasks:
        for run_index in range(1, runs_per_task + 1):
            result = agent.run(task["task"])
            usage = extract_usage(root / storage_name / "runs" / f"{result['run_id']}.json")
            rows.append(
                {
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": result.get("status"),
                    "stop_reason": result.get("stop_reason"),
                    "metrics": result.get("metrics", {}),
                    "usage": usage,
                    "estimated_cost_usd": estimate_cost(usage, model_name),
                    "difficult": is_difficult_task(task),
                    "model_used": model_name,
                }
            )
    return {
        "runs": rows,
        "aggregate": aggregate_results(rows),
    }


def run_hybrid_mode(tasks: list[dict], root: Path, runs_per_task: int, api_key: str | None) -> dict:
    minimax_storage = ".hardness-round7-hybrid-minimax"
    sonnet_storage = ".hardness-round7-hybrid-sonnet"
    minimax_agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / minimax_storage,
            provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key=api_key),
        )
    )
    sonnet_agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / sonnet_storage,
            provider=ProviderConfig(name="openrouter", model="anthropic/claude-sonnet-4.6", api_key=api_key),
        )
    )

    rows: list[dict] = []
    consecutive_failures: dict[str, int] = {}

    for task in tasks:
        for run_index in range(1, runs_per_task + 1):
            first = minimax_agent.run(task["task"])
            first_usage = extract_usage(root / minimax_storage / "runs" / f"{first['run_id']}.json")
            final = first
            merged_usage = first_usage
            escalated = False
            escalation_reasons: list[str] = []

            pre_trigger = should_escalate_pre(task)
            if pre_trigger:
                escalated = True
                escalation_reasons.append("pre_risk_trigger")
            else:
                post_trigger, post_reasons = should_escalate_post(first, consecutive_failures.get(task["id"], 0))
                if post_trigger:
                    escalated = True
                    escalation_reasons.extend(post_reasons)

            if escalated:
                second = sonnet_agent.run(task["task"])
                second_usage = extract_usage(root / sonnet_storage / "runs" / f"{second['run_id']}.json")
                final = second
                merged_usage = merge_usage(first_usage, second_usage)

            if final.get("status") == "ok" and (final.get("stop_reason") in {"stop", "write_completed", "completed"}):
                consecutive_failures[task["id"]] = 0
            else:
                consecutive_failures[task["id"]] = consecutive_failures.get(task["id"], 0) + 1

            rows.append(
                {
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": final.get("status"),
                    "stop_reason": final.get("stop_reason"),
                    "metrics": final.get("metrics", {}),
                    "usage": merged_usage,
                    "estimated_cost_usd": estimate_hybrid_cost(first_usage, merged_usage),
                    "difficult": is_difficult_task(task),
                    "escalated": escalated,
                    "escalation_reasons": escalation_reasons,
                    "model_used": "hybrid:escalated_to_sonnet" if escalated else "minimax/minimax-m2.7",
                }
            )

    return {
        "runs": rows,
        "aggregate": aggregate_results(rows),
    }


def should_escalate_pre(task: dict) -> bool:
    text = f"{task.get('name', '')} {task.get('task', '')}".lower()
    tokens = (
        "ambiguous",
        "uncertainty",
        "conflict",
        "decide",
        "write",
        "policy",
        "multi_file",
        "routing_contract",
        "nonexistent",
        "noisy",
        "signal_extraction",
        "across docs",
    )
    return any(token in text for token in tokens)


def should_escalate_post(result: dict, current_consecutive_failures: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if result.get("status") != "ok":
        reasons.append("status_not_ok")

    stop_reason = result.get("stop_reason")
    if stop_reason not in {"stop", "write_completed", "completed"}:
        reasons.append("unstable_stop_reason")
    if stop_reason in {"needs_clarification", "none", "max_turns_reached", None}:
        reasons.append("needs_clarification_or_max_turns")

    metrics = result.get("metrics", {})
    if float(metrics.get("duplicate_action_rate", 0.0) or 0.0) > 0.0:
        reasons.append("duplicate_action")
    if int(metrics.get("no_progress_stop_count", 0) or 0) > 0:
        reasons.append("no_progress")
    if current_consecutive_failures >= 1:
        reasons.append("second_consecutive_failure")
    return bool(reasons), reasons


def is_difficult_task(task: dict) -> bool:
    name = str(task.get("name", "")).lower()
    tokens = (
        "ambiguous",
        "multi_file",
        "policy",
        "write",
        "stop",
        "signal",
    )
    return any(token in name for token in tokens)


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
    cost = (usage.get("prompt_tokens", 0) / 1_000_000) * pricing["input_per_million"]
    cost += (usage.get("completion_tokens", 0) / 1_000_000) * pricing["output_per_million"]
    return round(cost, 8)


def estimate_hybrid_cost(first_usage: dict, merged_usage: dict) -> float | None:
    if not merged_usage:
        return None
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


def aggregate_results(rows: list[dict]) -> dict:
    total = len(rows)
    completed = [r for r in rows if r.get("status") == "ok"]
    difficult = [r for r in rows if r.get("difficult")]
    difficult_completed = [r for r in difficult if r.get("status") == "ok"]
    costs = [r.get("estimated_cost_usd") for r in rows if r.get("estimated_cost_usd") is not None]
    escalated = [r for r in rows if r.get("escalated")]
    escalation_costs = [r.get("estimated_cost_usd") for r in escalated if r.get("estimated_cost_usd") is not None]

    return {
        "completion_rate": round(len(completed) / total, 4) if total else 0.0,
        "difficult_completion_rate": round(len(difficult_completed) / len(difficult), 4) if difficult else 0.0,
        "mean_turns_per_task": round(avg([r.get("metrics", {}).get("turns", 0) for r in rows]), 4),
        "mean_cost_per_task_usd": round(avg(costs), 8) if costs else None,
        "total_estimated_cost_usd": round(sum(costs), 8) if costs else None,
        "escalation_rate": round(len(escalated) / total, 4) if total else 0.0,
        "escalation_cost_mean_usd": round(avg(escalation_costs), 8) if escalation_costs else None,
        "runs_total": total,
    }


def build_decision(baseline: dict, hybrid: dict) -> dict:
    base_diff = float(baseline.get("difficult_completion_rate", 0.0) or 0.0)
    hyb_diff = float(hybrid.get("difficult_completion_rate", 0.0) or 0.0)
    difficult_gain = hyb_diff - base_diff

    base_cost = float(baseline.get("mean_cost_per_task_usd", 0.0) or 0.0)
    hyb_cost = float(hybrid.get("mean_cost_per_task_usd", 0.0) or 0.0)
    extra_cost = hyb_cost - base_cost
    quality_gain_per_extra_usd = round(difficult_gain / extra_cost, 6) if extra_cost > 0 else None

    cost_ratio = (hyb_cost / base_cost) if base_cost > 0 else 0.0
    pass_rule = (
        hyb_diff > base_diff
        and float(hybrid.get("escalation_rate", 0.0) or 0.0) <= 0.35
        and cost_ratio <= 2.0
        and (quality_gain_per_extra_usd is not None and quality_gain_per_extra_usd > 0)
    )

    return {
        "difficult_completion_gain": round(difficult_gain, 4),
        "extra_cost_per_task_usd": round(extra_cost, 8),
        "quality_gain_per_extra_usd": quality_gain_per_extra_usd,
        "cost_ratio_vs_baseline": round(cost_ratio, 4),
        "adopt_premium_escalation": pass_rule,
        "recommended_default": "minimax/minimax-m2.7",
        "recommended_escalation": "anthropic/claude-sonnet-4.6" if pass_rule else "restricted_or_disabled",
    }


def avg(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()
