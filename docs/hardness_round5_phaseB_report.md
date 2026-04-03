# HARDNESS Round 5 — Phase B Stability Report

## Scope

Confronto limitato a due modelli, come da protocollo:

- `minimax/minimax-m2.7`
- `qwen/qwen3.6-plus-preview:free`

Protocollo: [`docs/hardness_round5_phaseB_protocol.md`](docs/hardness_round5_phaseB_protocol.md)

Challenge set:

- [`HARDNESS/05_synthesis/challenge_set_round5_phaseB.json`](HARDNESS/05_synthesis/challenge_set_round5_phaseB.json)

Runner:

- [`scripts/round5_phase_b_stability.py`](scripts/round5_phase_b_stability.py)

Configurazione run:

- `runs_per_task=3`
- `max_tasks=4` (subset rapido controllato)

Raw output:

- [`docs/hardness_round5_phaseB_metrics.json`](docs/hardness_round5_phaseB_metrics.json)

## Metriche aggregate

### MiniMax M2.7

- completion_rate_mean: **1.0**
- completion_rate_variance: **0.0**
- turns_mean: **1.6667**
- turns_variance: **0.388889**
- cost_mean: **0.00354312**
- premature_stop_rate: **0.0**
- over_action_rate: **0.0833**
- inconsistent_decision_rate: **0.5**

### Qwen 3.6 Plus free

- completion_rate_mean: **1.0**
- completion_rate_variance: **0.0**
- turns_mean: **1.4167**
- turns_variance: **0.576389**
- cost_mean: **0.0**
- premature_stop_rate: **0.0**
- over_action_rate: **0.1667**
- inconsistent_decision_rate: **0.75**

## Decisione automatica del protocollo

Da [`docs/hardness_round5_phaseB_metrics.json`](docs/hardness_round5_phaseB_metrics.json):

- `promote_qwen_to_default = false`
- `recommended_default = minimax/minimax-m2.7`
- `recommended_fallback = qwen/qwen3.6-plus-preview:free`

## Lettura tecnica

Qwen mostra vantaggio su:

- costo medio (free)
- turns_mean (più basso)

Qwen peggiora su stabilità:

- turns_variance più alta
- over_action_rate più alta
- inconsistent_decision_rate più alta

Quindi, sui criteri fissati a priori, la promozione a default non è giustificata.

## Decisione operativa finale (Phase B subset)

1. mantenere MiniMax M2.7 come default
2. mantenere Qwen come fallback economico/challenger
3. ripetere la stessa metodologia su set completo (10 task) prima di qualsiasi promozione definitiva

