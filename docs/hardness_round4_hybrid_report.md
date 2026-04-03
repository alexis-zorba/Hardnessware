# HARDNESS Round 4 — Hybrid Benchmark Report

## Perimetro

Challenge set eseguito: [`HARDNESS/05_synthesis/challenge_set_round4.json`](HARDNESS/05_synthesis/challenge_set_round4.json)

- task totali: 10
- confronto:
  - MiniMax-only
  - MiniMax + escalation Sonnet (trigger-based)

Runner:

- [`scripts/round4_hybrid_benchmark.py`](scripts/round4_hybrid_benchmark.py)

Policy escalation:

- [`docs/hardness_round4_escalation_policy.md`](docs/hardness_round4_escalation_policy.md)

Raw metrics:

- [`docs/hardness_round4_hybrid_metrics.json`](docs/hardness_round4_hybrid_metrics.json)

## Risultati aggregati

### MiniMax-only

- completion rate: **1.0**
- mean turns/task: **2.7**
- final_after_success_rate avg: **0.4367**
- mean cost/task: **$0.00747657**
- total cost: **$0.0747657**

### Hybrid (MiniMax + Sonnet escalation)

- completion rate: **1.0**
- mean turns/task: **2.2**
- final_after_success_rate avg: **0.5283**
- mean cost/task: **$0.0737973**
- total cost: **$0.737973**
- escalation_count: **6/10** (rate **0.6**)

## Lettura decisionale

Il sistema ibrido migliora la convergenza media sul challenge set:

- turni medi: 2.7 → 2.2
- final_after_success: 0.4367 → 0.5283

Ma il costo aumenta in modo molto forte:

- mean cost/task: ~**9.87x**
- total cost: ~**9.87x**

## Decisione operativa

1. mantenere MiniMax M2.7 come default executor
2. restringere i trigger premium (escalation 60% è troppo alta per obiettivo cost-sensitive)
3. usare Sonnet come bisturi su subset più selettivo (alta ambiguità reale / failure persistenti)

## Patch/strumenti introdotti in questa fase

- challenge set Round 4: [`HARDNESS/05_synthesis/challenge_set_round4.json`](HARDNESS/05_synthesis/challenge_set_round4.json)
- benchmark ibrido: [`scripts/round4_hybrid_benchmark.py`](scripts/round4_hybrid_benchmark.py)
- policy escalation formalizzata: [`docs/hardness_round4_escalation_policy.md`](docs/hardness_round4_escalation_policy.md)

## Prossimo passo consigliato

Round 4.1: calibrazione trigger per ridurre escalation rate verso ~20–30% mantenendo il miglioramento su turni/convergenza.

