from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round8 benchmark: MiniMax-only failure mode analysis")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round8.json")
    parser.add_argument("--runs-per-task", type=int, default=2)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--output", default="docs/hardness_round8_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    api_key = _parse_api_file(root / "secrets" / "API.txt").get("openrouter")
    storage = ".hardness-round8"

    rows = run_tasks(root=root, tasks=tasks, runs_per_task=args.runs_per_task, storage=storage, api_key=api_key)
    aggregate = aggregate_rows(rows)

    payload = {
        "phase": "round8_failure_modes",
        "task_file": args.task_file,
        "runs_per_task": args.runs_per_task,
        "tasks_total": len(tasks),
        "runs": rows,
        "aggregate": aggregate,
    }
    out = root / args.output
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(aggregate, indent=2, ensure_ascii=False))


def run_tasks(root: Path, tasks: list[dict], runs_per_task: int, storage: str, api_key: str | None) -> list[dict]:
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / storage,
            provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key=api_key),
        )
    )
    rows: list[dict] = []
    for task in tasks:
        for run_index in range(1, runs_per_task + 1):
            result = agent.run(task["task"])
            rows.append(
                {
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": result.get("status"),
                    "stop_reason": result.get("stop_reason"),
                    "metrics": result.get("metrics", {}),
                }
            )
    return rows


def aggregate_rows(rows: list[dict]) -> dict:
    statuses = [1 if row.get("status") == "ok" else 0 for row in rows]
    turns = [float(row.get("metrics", {}).get("turns", 0) or 0) for row in rows]
    final_after_success = [float(row.get("metrics", {}).get("final_after_success_rate", 0.0) or 0.0) for row in rows]

    stop_reasons = Counter((row.get("stop_reason") or "none") for row in rows)

    over_action = 0
    no_progress = 0
    premature = 0
    grouped: dict[str, list[tuple[object, object, int]]] = {}

    for row in rows:
        metrics = row.get("metrics", {})
        if int(metrics.get("tool_calls", 0) or 0) > 3:
            over_action += 1
        if int(metrics.get("no_progress_stop_count", 0) or 0) > 0:
            no_progress += 1
        if row.get("stop_reason") in {"max_turns_reached", "none", None}:
            premature += 1
        grouped.setdefault(row.get("task_id", "?"), []).append(
            (row.get("status"), row.get("stop_reason"), int(metrics.get("turns", 0) or 0))
        )

    inconsistent = sum(1 for sigs in grouped.values() if len(set(sigs)) > 1)

    failure_modes = Counter()
    for row in rows:
        metrics = row.get("metrics", {})
        if row.get("stop_reason") in {"max_turns_reached", "none", None}:
            failure_modes["premature_stop"] += 1
        if int(metrics.get("tool_calls", 0) or 0) > 3:
            failure_modes["over_action"] += 1
        if int(metrics.get("no_progress_stop_count", 0) or 0) > 0:
            failure_modes["no_progress"] += 1
        if float(metrics.get("final_after_success_rate", 0.0) or 0.0) < 1.0:
            failure_modes["weak_finalization"] += 1

    total = len(rows)
    return {
        "completion_rate_mean": round(mean(statuses), 4),
        "completion_rate_variance": round(variance(statuses), 6),
        "turns_mean": round(mean(turns), 4),
        "turns_variance": round(variance(turns), 6),
        "over_action_rate": round(over_action / total, 4) if total else 0.0,
        "no_progress_rate": round(no_progress / total, 4) if total else 0.0,
        "inconsistent_decision_rate": round(inconsistent / len(grouped), 4) if grouped else 0.0,
        "premature_stop_rate": round(premature / total, 4) if total else 0.0,
        "final_after_success_mean": round(mean(final_after_success), 4),
        "stop_reason_distribution": dict(stop_reasons),
        "failure_modes_top": failure_modes.most_common(5),
        "runs_total": total,
    }


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def variance(values: list[float]) -> float:
    if not values:
        return 0.0
    m = mean(values)
    return float(sum((v - m) ** 2 for v in values) / len(values))


if __name__ == "__main__":
    main()

