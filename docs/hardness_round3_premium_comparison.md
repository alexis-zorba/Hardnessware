# HARDNESS Round 3 — Premium Comparison (MiniMax vs Sonnet)

## Scope

Confronto controllato sulla stessa task suite (12 task):

- Baseline economica: OpenRouter + `minimax/minimax-m2.7`
- Premium reference: OpenRouter + `anthropic/claude-sonnet-4.6`

Raw data:

- baseline: [`docs/hardness_round2_metrics.json`](docs/hardness_round2_metrics.json)
- premium: [`docs/hardness_round3_sonnet_metrics.json`](docs/hardness_round3_sonnet_metrics.json)

## Metriche confronto

| Metrica | MiniMax M2.7 | Sonnet 4.6 |
|---|---:|---:|
| Completion rate | 1.0 | 1.0 |
| Mean turns/task | 1.9167 | 1.9167 |
| Duplicate action rate avg | 0.0 | 0.0 |
| Redundant read rate avg | 0.0 | 0.0 |
| Final-after-success avg | 0.9167 | 0.9167 |
| Stop reasons | `stop=11`, `write_completed=1` | `stop=11`, `write_completed=1` |
| Mean cost/task (USD) | 0.00414052 | 0.06707775 |
| Total cost 12 task (USD) | 0.0496863 | 0.804933 |

## Delta costo

- Sonnet mean cost/task vs MiniMax: **~16.2x**
- Sonnet total cost vs MiniMax sulla suite: **~16.2x**

## Lettura decisionale

Su questa suite:

- qualità operativa osservata: **parità pratica**
- costo: **fortemente peggiore** per Sonnet

Conclusione operativa:

- mantenere MiniMax M2.7 come default executor
- usare Sonnet 4.6 solo su casi selezionati ad alta ambiguità o failure reali

## Implicazione strategica HARDNESS

Il premium non va valutato per “forza generale”, ma per **marginal gain per euro**.
In questa run il marginal gain osservato è nullo sulla metrica core, mentre il costo cresce in modo netto.

