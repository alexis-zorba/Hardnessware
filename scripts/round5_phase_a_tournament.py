from __future__ import annotations

import json
from pathlib import Path

from hardness.agent import AgentLoop
from hardness.cli import _parse_api_file
from hardness.config import HardnessConfig, ProviderConfig, RuntimeConfig
from hardness.providers import build_provider_adapter


MODELS = [
    "minimax/minimax-m2.7",
    "deepseek/deepseek-v3.2",
    "qwen/qwen3.6-plus-preview:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

PRICING_BY_MODEL = {
    "minimax/minimax-m2.7": {"input_per_million": 0.30, "output_per_million": 1.20},
    "deepseek/deepseek-v3.2": {"input_per_million": 0.26, "output_per_million": 0.38},
    "qwen/qwen3.6-plus-preview:free": {"input_per_million": 0.0, "output_per_million": 0.0},
    "nvidia/nemotron-3-super-120b-a12b:free": {"input_per_million": 0.0, "output_per_million": 0.0},
}


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    api_key = _parse_api_file(root / "secrets" / "API.txt").get("openrouter")
    tasks = json.loads((root / args.task_file).read_text(encoding="utf-8"))["tasks"]
    if args.max_tasks > 0:
        tasks = tasks[: args.max_tasks]

    model_results = []
    for model in MODELS:
        probes = run_probes(model=model, api_key=api_key)
        metrics = run_tasks(root=root, tasks=tasks, model=model, api_key=api_key)
        model_results.append({
            "model": model,
            "probes": probes,
            "metrics": metrics,
        })

    payload = {
        "phase": "round5_phaseA",
        "provider": "openrouter",
        "tasks_total": len(tasks),
        "models": model_results,
        "ranking": build_ranking(model_results),
    }
    out = root / args.output
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["ranking"], indent=2, ensure_ascii=False))


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Run Round5 Phase A tournament")
    parser.add_argument("--task-file", default="HARDNESS/05_synthesis/challenge_set_round4.json")
    parser.add_argument("--output", default="docs/hardness_round5_phaseA_metrics.json")
    parser.add_argument("--max-tasks", type=int, default=0)
    return parser.parse_args()


def run_probes(model: str, api_key: str | None) -> dict:
    adapter = build_provider_adapter(ProviderConfig(name="openrouter", model=model, api_key=api_key))
    results = {}
    for probe in ("basic", "structured", "tool"):
        results[probe] = adapter.run_probe(probe)
    return results


def run_tasks(root: Path, tasks: list[dict], model: str, api_key: str | None) -> dict:
    storage = root / ".hardness-round5" / sanitize(model)
    agent = AgentLoop(
        HardnessConfig(
            workspace_root=root,
            storage_root=storage,
            provider=ProviderConfig(name="openrouter", model=model, api_key=api_key),
            runtime=RuntimeConfig(max_turns=2),
        )
    )
    rows = []
    for task in tasks:
        result = agent.run(task["task"])
        usage = extract_usage_cost(storage / "runs" / f"{result['run_id']}.json")
        rows.append(
            {
                "id": task["id"],
                "name": task["name"],
                "status": result.get("status"),
                "stop_reason": result.get("stop_reason"),
                "metrics": result.get("metrics", {}),
                "usage": usage,
                "estimated_cost_usd": estimate_cost(model, usage),
            }
        )
    return {
        "tasks": rows,
        "aggregate": aggregate(rows),
    }


def extract_usage_cost(run_file: Path) -> dict:
    if not run_file.exists():
        return {}
    payload = json.loads(run_file.read_text(encoding="utf-8"))
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "provider_cost_usd": 0.0}
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
        usage_total["provider_cost_usd"] += float(usage.get("cost", 0.0) or 0.0)
    return usage_total if found else {}


def estimate_cost(model: str, usage: dict) -> float | None:
    if not usage:
        return None
    provider_cost = usage.get("provider_cost_usd")
    if provider_cost and provider_cost > 0:
        return round(float(provider_cost), 8)
    pricing = PRICING_BY_MODEL.get(model)
    if not pricing:
        return None
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    cost = (prompt_tokens / 1_000_000) * pricing["input_per_million"]
    cost += (completion_tokens / 1_000_000) * pricing["output_per_million"]
    return round(cost, 8)


def aggregate(rows: list[dict]) -> dict:
    total = len(rows)
    completion = [x for x in rows if x.get("status") == "ok"]
    completion_rate = len(completion) / total if total else 0.0
    turns = [x.get("metrics", {}).get("turns", 0) for x in rows]
    final_rates = [x.get("metrics", {}).get("final_after_success_rate", 0.0) for x in rows]
    costs = [x.get("estimated_cost_usd") for x in rows if x.get("estimated_cost_usd") is not None]
    stop_reason_distribution = {}
    for row in rows:
        reason = row.get("stop_reason") or "none"
        stop_reason_distribution[reason] = stop_reason_distribution.get(reason, 0) + 1

    return {
        "completion_rate": round(completion_rate, 4),
        "mean_turns_per_task": round(avg(turns), 4),
        "final_after_success_rate_avg": round(avg(final_rates), 4),
        "mean_cost_per_task_usd": round(avg(costs), 8) if costs else None,
        "total_estimated_cost_usd": round(sum(costs), 8) if costs else None,
        "cost_coverage_tasks": len(costs),
        "stop_reason_distribution": stop_reason_distribution,
    }


def build_ranking(model_results: list[dict]) -> dict:
    def probe_ok(item: dict) -> bool:
        probe_data = item["probes"]
        return all(bool(probe_data[k].get("ok")) for k in ("basic", "structured", "tool"))

    compatible = [x for x in model_results if probe_ok(x)]
    by_quality = sorted(
        compatible,
        key=lambda x: (
            x["metrics"]["aggregate"]["completion_rate"],
            x["metrics"]["aggregate"]["final_after_success_rate_avg"],
            -x["metrics"]["aggregate"]["mean_turns_per_task"],
        ),
        reverse=True,
    )
    by_cost = sorted(
        compatible,
        key=lambda x: x["metrics"]["aggregate"]["mean_cost_per_task_usd"] if x["metrics"]["aggregate"]["mean_cost_per_task_usd"] is not None else 9999,
    )
    return {
        "compatible_models": [x["model"] for x in compatible],
        "quality_rank": [x["model"] for x in by_quality],
        "cost_rank": [x["model"] for x in by_cost],
    }


def sanitize(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def avg(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


if __name__ == "__main__":
    main()
