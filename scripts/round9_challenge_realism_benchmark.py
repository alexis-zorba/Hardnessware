from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round9 benchmark: challenge realism on frozen baseline")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round9.json")
    parser.add_argument("--runs-per-task", type=int, default=1)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--output", default="docs/hardness_round9_metrics.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]
    api_key = _parse_api_file(root / "secrets" / "API.txt").get("openrouter")

    rows = run_tasks(root=root, tasks=tasks, runs_per_task=args.runs_per_task, api_key=api_key)
    aggregate = aggregate_rows(rows)
    payload = {
        "phase": "round9_challenge_realism",
        "task_file": args.task_file,
        "runs_per_task": args.runs_per_task,
        "tasks_total": len(tasks),
        "runs": rows,
        "aggregate": aggregate,
    }
    out = root / args.output
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(aggregate, indent=2, ensure_ascii=False))


def run_tasks(root: Path, tasks: list[dict], runs_per_task: int, api_key: str | None) -> list[dict]:
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=root / ".hardness-round9",
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
                    "task_class": task.get("class", "unknown"),
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": result.get("status"),
                    "stop_reason": result.get("stop_reason"),
                    "metrics": result.get("metrics", {}),
                    "failure_mode": classify_failure_mode(result.get("stop_reason"), result.get("metrics", {})),
                }
            )
    return rows


def classify_failure_mode(stop_reason: str | None, metrics: dict) -> str:
    if stop_reason in {"max_turns_reached", "none", None}:
        return "premature_stop"
    if float(metrics.get("post_success_extra_action_rate", 0.0) or 0.0) > 0.0:
        return "over_action_after_success"
    if float(metrics.get("weak_final_rate", 0.0) or 0.0) > 0.0:
        return "weak_finalization"
    if float(metrics.get("success_recognized_rate", 0.0) or 0.0) < 1.0 and int(metrics.get("tool_calls", 0) or 0) > 0:
        return "success_not_recognized"
    return "none"


def aggregate_rows(rows: list[dict]) -> dict:
    total = len(rows)
    statuses = [1 if row.get("status") == "ok" else 0 for row in rows]
    turns = [float(row.get("metrics", {}).get("turns", 0) or 0) for row in rows]
    final_after_success = [float(row.get("metrics", {}).get("final_after_success_rate", 0.0) or 0.0) for row in rows]

    over_action = sum(1 for row in rows if int(row.get("metrics", {}).get("tool_calls", 0) or 0) > 3)
    no_progress = sum(1 for row in rows if int(row.get("metrics", {}).get("no_progress_stop_count", 0) or 0) > 0)
    premature = sum(1 for row in rows if row.get("stop_reason") in {"max_turns_reached", "none", None})

    grouped: dict[str, set[tuple[object, object, int]]] = {}
    for row in rows:
        grouped.setdefault(row["task_id"], set()).add(
            (row.get("status"), row.get("stop_reason"), int(row.get("metrics", {}).get("turns", 0) or 0))
        )
    inconsistent = sum(1 for sigs in grouped.values() if len(sigs) > 1)

    stop_dist = Counter((row.get("stop_reason") or "none") for row in rows)
    failure_modes = Counter(row.get("failure_mode", "none") for row in rows)

    class_groups: dict[str, list[dict]] = {}
    for row in rows:
        class_groups.setdefault(row.get("task_class", "unknown"), []).append(row)

    per_class = {
        key: {
            "completion_rate": round(sum(1 for r in values if r.get("status") == "ok") / len(values), 4) if values else 0.0,
            "turns_mean": round(mean([float(r.get("metrics", {}).get("turns", 0) or 0) for r in values]), 4),
        }
        for key, values in class_groups.items()
    }

    return {
        "completion_rate_mean": round(mean(statuses), 4),
        "turns_mean": round(mean(turns), 4),
        "over_action_rate": round(over_action / total, 4) if total else 0.0,
        "inconsistent_decision_rate": round(inconsistent / len(grouped), 4) if grouped else 0.0,
        "premature_stop_rate": round(premature / total, 4) if total else 0.0,
        "no_progress_rate": round(no_progress / total, 4) if total else 0.0,
        "final_after_success_mean": round(mean(final_after_success), 4),
        "stop_reason_distribution": dict(stop_dist),
        "failure_modes_top": failure_modes.most_common(6),
        "class_breakdown": per_class,
        "runs_total": total,
    }


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()

