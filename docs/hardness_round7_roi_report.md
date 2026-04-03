# HARDNESS Round 7 — Premium Escalation ROI Report

## Scope eseguito

Confronto ROI tra:

- MiniMax-only (`minimax/minimax-m2.7`)
- MiniMax + Sonnet escalation (`anthropic/claude-sonnet-4.6`)

Protocollo:

- [`docs/hardness_round7_roi_protocol.md`](docs/hardness_round7_roi_protocol.md)

Runner:

- [`scripts/round7_premium_roi_benchmark.py`](scripts/round7_premium_roi_benchmark.py)

Raw output disponibili:

- subset controllato: [`docs/hardness_round7_roi_metrics_subset.json`](docs/hardness_round7_roi_metrics_subset.json)
- quick smoke: [`docs/hardness_round7_roi_metrics_quick.json`](docs/hardness_round7_roi_metrics_quick.json)

Configurazione decisionale corrente:

- `runs_per_task=1`
- `max_tasks=2`

## Metriche aggregate (subset)

### Baseline MiniMax-only

- completion_rate: **1.0**
- difficult_completion_rate: **1.0**
- mean_turns_per_task: **3.0**
- mean_cost_per_task_usd: **0.00875355**
- escalation_rate: **0.0**

### Hybrid MiniMax + Sonnet

- completion_rate: **1.0**
- difficult_completion_rate: **1.0**
- mean_turns_per_task: **3.0**
- mean_cost_per_task_usd: **0.1026135**
- escalation_rate: **1.0**

## ROI decision (subset)

Da [`docs/hardness_round7_roi_metrics_subset.json`](docs/hardness_round7_roi_metrics_subset.json):

- `difficult_completion_gain = 0.0`
- `extra_cost_per_task_usd = 0.09385995`
- `quality_gain_per_extra_usd = 0.0`
- `cost_ratio_vs_baseline = 11.7225`
- `adopt_premium_escalation = false`

## Decisione operativa corrente

1. mantenere `minimax/minimax-m2.7` come default
2. non adottare escalation premium in questa configurazione trigger (ROI non giustificato)
3. restringere ulteriormente i trigger Sonnet per ridurre escalation rate prima di nuova validazione

## Aggiornamento full run (2x4)

Run completato con:

- `runs_per_task=2`
- `max_tasks=4`
- output: [`docs/hardness_round7_roi_metrics.json`](docs/hardness_round7_roi_metrics.json)

Decisione full:

- `difficult_completion_gain = 0.0`
- `extra_cost_per_task_usd = 0.04013249`
- `quality_gain_per_extra_usd = 0.0`
- `cost_ratio_vs_baseline = 9.0195`
- `adopt_premium_escalation = false`

Interpretazione:

- il full run conferma la decisione subset
- nessun guadagno qualitativo sui task difficili
- premium ancora non giustificato nel path operativo
