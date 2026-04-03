# HARDNESS Round 8.2 — Protocol (Finalization Quality)

## Obiettivo unico

Migliorare la qualità della chiusura post-successo **senza** cambiare modello/routing.

## Vincoli

- `minimax/minimax-m2.7` unico modello operativo
- nessuna escalation premium
- nessun routing opportunistico

## Interventi autorizzati

1. soft success gate (1 reflection turn senza tool)
2. finalization prompt contract esplicito
3. single final repair pass su output deboli
4. metriche separate correctness/quality

## Metriche target

- `explicit_completion_rate_mean >= 0.8`
- `weak_final_rate_mean <= 0.2`
- `post_success_extra_action_rate_mean ~= 0`

## Runner e dataset

- micro runner: [`scripts/round8_1_finalization_benchmark.py`](scripts/round8_1_finalization_benchmark.py)
- micro set: [`HARDNESS/05_synthesis/challenge_set_round8_1.json`](HARDNESS/05_synthesis/challenge_set_round8_1.json)
- subset rerun: [`scripts/round8_failure_mode_benchmark.py`](scripts/round8_failure_mode_benchmark.py)

