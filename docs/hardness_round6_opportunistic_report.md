# HARDNESS Round 6 — Opportunistic Qwen Report

## Scope

Valutazione Round 6 del routing ibrido opportunistico:

- default: `minimax/minimax-m2.7`
- opportunistic low-risk: `qwen/qwen3.6-plus-preview:free`

Runner:

- [`scripts/round6_opportunistic_benchmark.py`](scripts/round6_opportunistic_benchmark.py)

Raw metrics principali:

- full run: [`docs/hardness_round6_opportunistic_metrics.json`](docs/hardness_round6_opportunistic_metrics.json)
- subset run: [`docs/hardness_round6_opportunistic_metrics_subset.json`](docs/hardness_round6_opportunistic_metrics_subset.json)
- quick smoke: [`docs/hardness_round6_opportunistic_metrics_quick.json`](docs/hardness_round6_opportunistic_metrics_quick.json)

Configurazione run decisionale (full):

- `runs_per_task=3`
- `max_tasks=4`

## Metriche aggregate (full)

### MiniMax-only

- completion_rate_mean: **1.0**
- turns_mean: **1.5**
- cost_mean: **0.0042592**
- premature_stop_rate: **0.0833**
- over_action_rate: **0.0833**
- inconsistent_decision_rate: **0.75**
- qwen_route_rate: **0.0**

### Hybrid opportunistic (MiniMax + Qwen)

- completion_rate_mean: **0.9167**
- turns_mean: **1.6667**
- cost_mean: **0.00127499**
- premature_stop_rate: **0.0833**
- over_action_rate: **0.0833**
- inconsistent_decision_rate: **1.0**
- qwen_route_rate: **1.0**

## Decisione automatica full

Da [`docs/hardness_round6_opportunistic_metrics.json`](docs/hardness_round6_opportunistic_metrics.json):

- `adopt_opportunistic_qwen = false`
- `keeps_stability = false`
- `cheaper_than_baseline = true`
- `recommended_default = minimax/minimax-m2.7`
- `recommended_opportunistic = disabled`

## Lettura tecnica

Nel run decisionale, il routing opportunistico ha mostrato:

1. riduzione di costo media significativa
2. peggioramento su completion (`1.0 -> 0.9167`)
3. peggioramento su consistenza decisionale (`0.75 -> 1.0`)

Il campione quick iniziale (1 task) era favorevole ma non rappresentativo. Il full (12 run) invalida la promozione: i guardrail introdotti in [`ModelRouter.route()`](src/hardness/router.py:14) e [`ModelRouter._is_low_risk_task()`](src/hardness/router.py:54) instradano correttamente verso Qwen, ma l'esito aggregato indica regressione di stabilità nel loop [`AgentLoop.run()`](src/hardness/agent.py:32).

## Decisione operativa Round 6 (stato corrente)

1. mantenere MiniMax come default
2. disabilitare opportunistic Qwen in produzione per ora
3. mantenere Qwen come challenger economico in benchmark periodici
