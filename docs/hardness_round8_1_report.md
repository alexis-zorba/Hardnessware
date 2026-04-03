# HARDNESS Round 8.1 — Post-Success Finalization Hardening Report

## Scope

Round 8.1 focalizzato su finalizzazione post-successo, senza introdurre nuovi modelli o routing.

Patch principali:

- metriche nuove in [`RunMetrics`](src/hardness/types.py:59)
- success gate e contract di chiusura in [`AgentLoop.run()`](src/hardness/agent.py:32)

Asset di benchmark:

- estrazione casi: [`docs/hardness_round8_1_finalization_cases.md`](docs/hardness_round8_1_finalization_cases.md)
- micro challenge set: [`HARDNESS/05_synthesis/challenge_set_round8_1.json`](HARDNESS/05_synthesis/challenge_set_round8_1.json)
- runner dedicato: [`scripts/round8_1_finalization_benchmark.py`](scripts/round8_1_finalization_benchmark.py)

Raw metrics:

- micro-benchmark: [`docs/hardness_round8_1_metrics.json`](docs/hardness_round8_1_metrics.json)
- rerun Round 8 post-patch: [`docs/hardness_round8_metrics_post81.json`](docs/hardness_round8_metrics_post81.json)
- baseline pre-patch: [`docs/hardness_round8_metrics.json`](docs/hardness_round8_metrics.json)

## Risultati micro-benchmark Round 8.1

- completion_rate_mean: **1.0**
- success_recognized_rate_mean: **0.3333**
- finalization_delay_rate_mean: **0.3333**
- post_success_extra_action_rate_mean: **0.2222**
- explicit_completion_rate_mean: **0.3333**
- weak_final_rate_mean: **0.5**

Classificazione top:

- `over-action after success`: 3
- `late stop`: 1
- `clean_finalization`: 1
- `missing explicit completion`: 1

## Confronto Round 8 pre/post patch

### Pre-patch ([`docs/hardness_round8_metrics.json`](docs/hardness_round8_metrics.json))

- turns_mean: **2.0**
- over_action_rate: **0.0**
- inconsistent_decision_rate: **0.0**
- premature_stop_rate: **0.0**

### Post-patch ([`docs/hardness_round8_metrics_post81.json`](docs/hardness_round8_metrics_post81.json))

- turns_mean: **1.5**
- over_action_rate: **0.0**
- inconsistent_decision_rate: **0.0**
- premature_stop_rate: **0.0**
- nuovo stop reason osservato: `post_success_extra_action_limit`

## Lettura tecnica

Effetto positivo:

1. riduzione turni medi su suite Round 8 (`2.0 -> 1.5`)
2. mantenimento completion e stabilità aggregate

Rischio introdotto:

1. il success gate è aggressivo e genera stop `post_success_extra_action_limit`
2. nel micro-set la qualità esplicita di finalizzazione è ancora insufficiente

## Decisione operativa Round 8.1

1. mantenere patch come baseline sperimentale (non promuovere ancora come hardening definitivo)
2. calibrare il success gate per ridurre i casi `post_success_extra_action_limit`
3. rafforzare contract finale testuale in prompt/follow-up prima del prossimo rerun

