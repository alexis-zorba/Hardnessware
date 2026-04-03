from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Round8.1 benchmark: post-success finalization quality")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round8_1.json")
    parser.add_argument("--runs-per-task", type=int, default=2)
    parser.add_argument("--max-tasks", type=int, default=0)
    parser.add_argument("--output", default="docs/hardness_round8_1_metrics.json")
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
        "phase": "round8_1_finalization",
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
            storage_root=root / ".hardness-round8_1",
            provider=ProviderConfig(name="openrouter", model="minimax/minimax-m2.7", api_key=api_key),
        )
    )
    rows: list[dict] = []
    for task in tasks:
        for run_index in range(1, runs_per_task + 1):
            result = agent.run(task["task"])
            metrics = result.get("metrics", {})
            rows.append(
                {
                    "task_id": task["id"],
                    "task_name": task["name"],
                    "run_index": run_index,
                    "status": result.get("status"),
                    "stop_reason": result.get("stop_reason"),
                    "metrics": metrics,
                    "finalization_label": classify_finalization(result.get("stop_reason"), metrics),
                }
            )
    return rows


def classify_finalization(stop_reason: str | None, metrics: dict) -> str:
    if float(metrics.get("post_success_extra_action_rate", 0.0) or 0.0) > 0.0:
        return "over-action after success"
    if float(metrics.get("weak_final_rate", 0.0) or 0.0) > 0.0:
        return "weak final answer"
    if float(metrics.get("explicit_completion_rate", 0.0) or 0.0) < 1.0:
        return "missing explicit completion"
    if float(metrics.get("finalization_delay_rate", 0.0) or 0.0) > 0.34:
        return "late stop"
    if float(metrics.get("success_recognized_rate", 0.0) or 0.0) < 1.0:
        return "success not recognized"
    if stop_reason == "write_completed" and int(metrics.get("verified_writes", 0) or 0) < 1:
        return "write success not sealed"
    return "clean_finalization"


def aggregate_rows(rows: list[dict]) -> dict:
    total = len(rows)
    labels = Counter(row.get("finalization_label", "unknown") for row in rows)
    stop_reasons = Counter((row.get("stop_reason") or "none") for row in rows)

    success_recognized = [float(row.get("metrics", {}).get("success_recognized_rate", 0.0) or 0.0) for row in rows]
    finalization_delay = [float(row.get("metrics", {}).get("finalization_delay_rate", 0.0) or 0.0) for row in rows]
    post_success_extra = [float(row.get("metrics", {}).get("post_success_extra_action_rate", 0.0) or 0.0) for row in rows]
    explicit_completion = [float(row.get("metrics", {}).get("explicit_completion_rate", 0.0) or 0.0) for row in rows]
    weak_final = [float(row.get("metrics", {}).get("weak_final_rate", 0.0) or 0.0) for row in rows]

    return {
        "completion_rate_mean": round(sum(1 for row in rows if row.get("status") == "ok") / total, 4) if total else 0.0,
        "success_recognized_rate_mean": round(mean(success_recognized), 4),
        "finalization_delay_rate_mean": round(mean(finalization_delay), 4),
        "post_success_extra_action_rate_mean": round(mean(post_success_extra), 4),
        "explicit_completion_rate_mean": round(mean(explicit_completion), 4),
        "weak_final_rate_mean": round(mean(weak_final), 4),
        "stop_reason_distribution": dict(stop_reasons),
        "finalization_labels_top": labels.most_common(8),
        "runs_total": total,
    }


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()

