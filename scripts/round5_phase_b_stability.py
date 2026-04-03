from __future__ import annotations

import argparse
import json
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig, RuntimeConfig


MODELS = [
    "minimax/minimax-m2.7",
    "qwen/qwen3.6-plus-preview:free",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round5 Phase B stability benchmark")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round5_phaseB.json")
    parser.add_argument("--runs-per-task", type=int, default=3)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--output", default="docs/hardness_round5_phaseB_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    api_key = _parse_api_file(root / "secrets" / "API.txt").get("openrouter")

    model_results = []
    for model in MODELS:
        result = run_model(root=root, model=model, tasks=tasks, runs_per_task=args.runs_per_task, api_key=api_key)
        model_results.append(result)

    payload = {
        "phase": "round5_phaseB",
        "task_file": args.task_file,
        "runs_per_task": args.runs_per_task,
        "tasks_total": len(tasks),
        "models": model_results,
        "decision": build_decision(model_results),
    }

    out = root / args.output
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["decision"], indent=2, ensure_ascii=False))


def run_model(root: Path, model: str, tasks: list[dict], runs_per_task: int, api_key: str | None) -> dict:
    storage = root / ".hardness-round5-phaseB" / sanitize(model)
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=storage,
            provider=ProviderConfig(name="openrouter", model=model, api_key=api_key),
            runtime=RuntimeConfig(max_turns=3),
        )
    )

    rows = []
    for task in tasks:
        for run_index in range(1, runs_per_task + 1):
            result = agent.run(task["task"])
            run_file = storage / "runs" / f"{result['run_id']}.json"
            usage = extract_usage(run_file)
            rows.append(
                {
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": result.get("status"),
                    "stop_reason": result.get("stop_reason"),
                    "metrics": result.get("metrics", {}),
                    "usage": usage,
                }
            )

    aggregate = aggregate_rows(rows)
    return {
        "model": model,
        "runs": rows,
        "aggregate": aggregate,
    }


def extract_usage(run_file: Path) -> dict:
    if not run_file.exists():
        return {}
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "provider_cost_usd": 0.0}
    for event in payload.get("events", []):
        if event.get("kind") != "provider_response":
            continue
        event_usage = event.get("payload", {}).get("usage") or {}
        if not isinstance(event_usage, dict):
            continue
        usage["prompt_tokens"] += int(event_usage.get("prompt_tokens", 0) or 0)
        usage["completion_tokens"] += int(event_usage.get("completion_tokens", 0) or 0)
        usage["total_tokens"] += int(event_usage.get("total_tokens", 0) or 0)
        usage["provider_cost_usd"] += float(event_usage.get("cost", 0.0) or 0.0)
    return usage


def aggregate_rows(rows: list[dict]) -> dict:
    statuses = [1 if row.get("status") == "ok" else 0 for row in rows]
    turns = [float(row.get("metrics", {}).get("turns", 0) or 0) for row in rows]
    costs = [float(row.get("usage", {}).get("provider_cost_usd", 0.0) or 0.0) for row in rows]

    premature = 0
    over_action = 0
    inconsistent = 0
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["task_id"], []).append(row)
        stop_reason = row.get("stop_reason")
        if stop_reason in {"max_turns_reached", "none", None}:
            premature += 1
        if int(row.get("metrics", {}).get("tool_calls", 0) or 0) > 3:
            over_action += 1

    for task_id, task_rows in grouped.items():
        signatures = {(r.get("status"), r.get("stop_reason"), int(r.get("metrics", {}).get("turns", 0) or 0)) for r in task_rows}
        if len(signatures) > 1:
            inconsistent += 1

    return {
        "completion_rate_mean": round(mean(statuses), 4),
        "completion_rate_variance": round(variance(statuses), 6),
        "turns_mean": round(mean(turns), 4),
        "turns_variance": round(variance(turns), 6),
        "cost_mean": round(mean(costs), 8),
        "cost_variance": round(variance(costs), 10),
        "premature_stop_rate": round(premature / len(rows), 4) if rows else 0.0,
        "over_action_rate": round(over_action / len(rows), 4) if rows else 0.0,
        "inconsistent_decision_rate": round(inconsistent / len(grouped), 4) if grouped else 0.0,
        "runs_total": len(rows),
    }


def build_decision(model_results: list[dict]) -> dict:
    lookup = {item["model"]: item["aggregate"] for item in model_results}
    mini = lookup["minimax/minimax-m2.7"]
    qwen = lookup["qwen/qwen3.6-plus-preview:free"]

    promote = (
        qwen["completion_rate_mean"] >= mini["completion_rate_mean"]
        and qwen["completion_rate_variance"] <= mini["completion_rate_variance"]
        and qwen["turns_variance"] <= mini["turns_variance"]
        and qwen["premature_stop_rate"] <= mini["premature_stop_rate"]
        and qwen["over_action_rate"] <= mini["over_action_rate"]
        and qwen["cost_mean"] <= mini["cost_mean"]
        and qwen["inconsistent_decision_rate"] <= mini["inconsistent_decision_rate"]
    )

    return {
        "promote_qwen_to_default": promote,
        "recommended_default": "qwen/qwen3.6-plus-preview:free" if promote else "minimax/minimax-m2.7",
        "recommended_fallback": "minimax/minimax-m2.7" if promote else "qwen/qwen3.6-plus-preview:free",
    }


def sanitize(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def variance(values: list[float]) -> float:
    if not values:
        return 0.0
    m = mean(values)
    return float(sum((v - m) ** 2 for v in values) / len(values))


if __name__ == "__main__":
    main()

