# HARDNESS Round 9 — Challenge Realism Report

## Scope

Valutazione baseline v1 congelata su challenge realistico, senza modifiche a loop/routing/modelli.

Protocollo:

- [`docs/hardness_round9_protocol.md`](docs/hardness_round9_protocol.md)

Challenge set:

- [`HARDNESS/05_synthesis/challenge_set_round9.json`](HARDNESS/05_synthesis/challenge_set_round9.json)

Runner:

- [`scripts/round9_challenge_realism_benchmark.py`](scripts/round9_challenge_realism_benchmark.py)

Raw metrics:

- [`docs/hardness_round9_metrics.json`](docs/hardness_round9_metrics.json)

Configurazione run:

- `runs_per_task=1`
- `tasks_total=9`

## Metriche aggregate

- completion_rate_mean: **1.0**
- turns_mean: **1.8889**
- over_action_rate: **0.0**
- inconsistent_decision_rate: **0.0**
- premature_stop_rate: **0.0**
- no_progress_rate: **0.0**
- final_after_success_mean: **0.537**
- stop_reason_distribution: `stop=7`, `write_completed=2`
- failure_modes_top: `none=9`

## Breakdown per classe realistica

- documentale: completion `1.0`, turns_mean `2.3333`
- operativo: completion `1.0`, turns_mean `1.3333`
- epistemico: completion `1.0`, turns_mean `2.0`

## Lettura tecnica

La baseline v1 regge anche su scenari più sporchi rispetto ai round precedenti:

1. nessuna regressione su completion/stabilità
2. nessun segnale di over-action o stop prematuro
3. comportamento coerente tra classi diverse di task realistici

Punto ancora monitorabile:

- `final_after_success_mean` non è ancora vicino a 1.0, ma resta coerente con i trade-off già noti e senza impatto su completion.

## Decisione operativa

1. baseline v1 confermata anche in challenge realism
2. nessuna riapertura di routing/modelli
3. fase successiva: espansione graduale del challenge realism (più casi confliggenti e incompleti) mantenendo la stessa baseline

