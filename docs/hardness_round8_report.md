# HARDNESS Round 8 — Challenge Set Quality & Failure Mode Report

## Scope

Round 8 eseguito con vincolo **single-model**:

- modello: `minimax/minimax-m2.7`
- nessun routing aggiuntivo
- nessuna escalation premium

Protocollo:

- [`docs/hardness_round8_protocol.md`](docs/hardness_round8_protocol.md)

Challenge set:

- [`HARDNESS/05_synthesis/challenge_set_round8.json`](HARDNESS/05_synthesis/challenge_set_round8.json)

Runner:

- [`scripts/round8_failure_mode_benchmark.py`](scripts/round8_failure_mode_benchmark.py)

Raw metrics:

- [`docs/hardness_round8_metrics.json`](docs/hardness_round8_metrics.json)

Configurazione run:

- `runs_per_task=1`
- `max_tasks=4`

## Metriche aggregate

- completion_rate_mean: **1.0**
- completion_rate_variance: **0.0**
- turns_mean: **2.0**
- turns_variance: **1.0**
- over_action_rate: **0.0**
- no_progress_rate: **0.0**
- inconsistent_decision_rate: **0.0**
- premature_stop_rate: **0.0**
- final_after_success_mean: **0.2083**
- stop_reason_distribution: `stop=2`, `write_completed=2`
- failure_modes_top: `weak_finalization=4`

## Lettura tecnica

Round 8 centra il target principale di robustezza operativa sul challenge set aggiornato:

1. nessun premature stop
2. nessun over-action
3. nessuna inconsistenza inter-task

Il failure mode dominante residuo è la **weak finalization** (final_after_success non ancora pienamente allineato), coerente con quanto osservato storicamente nel loop [`AgentLoop.run()`](src/hardness/agent.py:32).

## Decisione operativa

1. mantenere MiniMax-only come path operativo
2. nessuna reintroduzione di routing/modelli
3. prossimo hardening mirato: migliorare finalizzazione post-successo (prompt/stop policy) senza aumentare complessità architetturale

