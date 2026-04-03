# HARDNESS Round 8.2 — Finalization Quality Calibration Report

## Scope

Round 8.2 eseguito su MiniMax-only, senza nuovi modelli/router, con obiettivo esclusivo: migliorare la qualità di chiusura.

Interventi implementati:

1. soft success gate in [`AgentLoop.run()`](src/hardness/agent.py:32)
2. prompt di finalizzazione più vincolante in [`build_followup_user_message()`](src/hardness/prompting.py:30)
3. single final repair pass in [`AgentLoop.run()`](src/hardness/agent.py:181)
4. separazione metriche correctness/quality in [`RunMetrics`](src/hardness/types.py:59)

## Raw metrics usati

- baseline Round 8.1 micro: [`docs/hardness_round8_1_metrics.json`](docs/hardness_round8_1_metrics.json)
- Round 8.2 micro: [`docs/hardness_round8_2_metrics.json`](docs/hardness_round8_2_metrics.json)
- Round 8 post-8.1: [`docs/hardness_round8_metrics_post81.json`](docs/hardness_round8_metrics_post81.json)
- Round 8 post-8.2: [`docs/hardness_round8_metrics_post82.json`](docs/hardness_round8_metrics_post82.json)

## Target Round 8.2

- `explicit_completion_rate >= 0.8`
- `weak_final_rate <= 0.2`
- `post_success_extra_action_rate ~ 0`

## Risultati micro-benchmark (6 run)

### Round 8.1 baseline

- explicit_completion_rate_mean: **0.3333**
- weak_final_rate_mean: **0.5**
- post_success_extra_action_rate_mean: **0.2222**

### Round 8.2

- explicit_completion_rate_mean: **0.8333** ✅
- weak_final_rate_mean: **0.0** ✅
- post_success_extra_action_rate_mean: **0.0** ✅
- success_recognized_rate_mean: **1.0**

Target principali raggiunti.

## Rerun subset Round 8 (4 run)

### Post-8.1

- turns_mean: **1.5**
- final_after_success_mean: **0.125**
- stop reason include `post_success_extra_action_limit`

### Post-8.2

- turns_mean: **2.25**
- final_after_success_mean: **0.5833**
- stop reason: `stop=3`, `write_completed=1` (sparisce `post_success_extra_action_limit`)

Lettura: Round 8.2 migliora qualità di finalizzazione e rimuove stop forzati; aumenta il costo in turni medi (trade-off accettabile in questa fase di calibrazione qualità).

## Rerun completo Round 8 (8 run)

Output full:

- [`docs/hardness_round8_metrics_full_post82.json`](docs/hardness_round8_metrics_full_post82.json)

Risultati principali:

- completion_rate_mean: **1.0**
- turns_mean: **1.875**
- over_action_rate: **0.0**
- inconsistent_decision_rate: **0.0**
- premature_stop_rate: **0.0**
- final_after_success_mean: **0.7083**
- stop reasons: `stop=6`, `write_completed=2`

Confronto vs subset post-8.2:

- turns_mean migliora (`2.25 -> 1.875`)
- final_after_success_mean migliora (`0.5833 -> 0.7083`)
- stabilità invariata positiva (nessun over-action/inconsistenza/premature stop)

## Decisione operativa

1. promuovere Round 8.2 come nuova baseline di finalizzazione
2. congelare la logica loop corrente in [`docs/hardness_baseline_v1_approved.md`](docs/hardness_baseline_v1_approved.md)
3. mantenere invariato il perimetro MiniMax-only
4. prossima fase: `challenge realism` senza introdurre nuovi modelli/router
