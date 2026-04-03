# HARDNESS Round 9 — Challenge Realism Protocol

## Obiettivo

Validare la robustezza della baseline v1 in scenari più realistici, senza cambiare loop/routing/modelli.

Baseline congelata:

- [`docs/hardness_baseline_v1_approved.md`](docs/hardness_baseline_v1_approved.md)

## Vincoli

- modello unico: `minimax/minimax-m2.7`
- nessuna escalation premium
- nessun routing opportunistico
- nessuna modifica architetturale durante il benchmark

## Challenge set Round 9 (3 classi)

1. **Realismo documentale**: sintesi e incoerenze su fonti multiple
2. **Realismo operativo**: task minimi read/search/write con verifica concreta
3. **Realismo epistemico**: dati incompleti/confliggenti, stop corretto senza invenzioni

Dataset:

- [`HARDNESS/05_synthesis/challenge_set_round9.json`](HARDNESS/05_synthesis/challenge_set_round9.json)

## Runner

- [`scripts/round9_challenge_realism_benchmark.py`](scripts/round9_challenge_realism_benchmark.py)

Output raw:

- `docs/hardness_round9_metrics.json`

## Metriche obbligatorie

- completion rate
- turns mean
- over_action_rate
- inconsistent_decision_rate
- premature_stop_rate
- final_after_success_mean
- stop_reason_distribution
- failure_modes_top (taxonomy real-world)

