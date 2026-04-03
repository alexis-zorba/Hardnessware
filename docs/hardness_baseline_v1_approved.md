# HARDNESS Baseline v1 — Approved

## Stato approvazione

Baseline operativa approvata dopo Round 8.2.

## 1) Modello e routing

- `default_executor = minimax/minimax-m2.7`
- premium escalation (`sonnet`) non nel path operativo standard
- opportunistic challenger (`qwen`) non nel path operativo standard

Riferimento policy:

- [`docs/hardness_routing_runtime_policy.md`](docs/hardness_routing_runtime_policy.md)

## 2) Stato loop (finalizzazione)

Componenti congelate:

1. soft success gate
2. reflection-only turn senza tool su post-success ridondante
3. single final repair pass
4. finalization prompt contract esplicito

Implementazione:

- [`AgentLoop.run()`](src/hardness/agent.py:32)
- [`build_followup_user_message()`](src/hardness/prompting.py:30)

## 3) Metriche baseline monitorate

Core stability:

- completion rate
- over-action rate
- inconsistent decision rate
- premature stop rate

Finalization quality:

- `success_recognized_rate`
- `explicit_completion_rate`
- `weak_final_rate`
- `post_success_extra_action_rate`
- `finalization_correctness_rate`
- `finalization_quality_rate`

Definizione metrica in [`RunMetrics`](src/hardness/types.py:59).

## 4) Benchmark chiusi e decisioni

- Round 6: opportunistic Qwen non promosso
  - [`docs/hardness_round6_opportunistic_report.md`](docs/hardness_round6_opportunistic_report.md)
- Round 7: premium ROI Sonnet non giustificato
  - [`docs/hardness_round7_roi_report.md`](docs/hardness_round7_roi_report.md)
- Round 8: focus challenge quality/failure modes
  - [`docs/hardness_round8_report.md`](docs/hardness_round8_report.md)
- Round 8.2: finalization quality calibration riuscita
  - [`docs/hardness_round8_2_report.md`](docs/hardness_round8_2_report.md)

## 5) Feature volutamente escluse (freeze)

- nuovi modelli nel path operativo
- nuovi router/escalation automatiche
- multi-agent operativo
- memoria avanzata non necessaria al loop core

## 6) Prossima fase autorizzata

`challenge realism` a parità di baseline:

1. casi più sporchi e realistici
2. maggiore rumore e ambiguità operativa
3. validazione robustezza senza alterare l’architettura core

