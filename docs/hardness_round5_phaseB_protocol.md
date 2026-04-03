# HARDNESS Round 5 — Phase B Protocol

## Scope vincolato

Confronto esclusivo tra:

- `minimax/minimax-m2.7`
- `qwen/qwen3.6-plus-preview:free`

Nessun altro provider/modello/tool/policy durante Phase B.

## Obiettivo

Decidere se Qwen può sostituire MiniMax come default **senza perdita di stabilità**.

## Test design

1. challenge set dedicato (8–12 task ad alta ambiguità)
2. esecuzione multipla per task e modello (`runs_per_task` tra 3 e 5)
3. valutazione per varianza, non solo per media

## Metriche obbligatorie

- completion_rate_mean
- completion_rate_variance
- turns_mean
- turns_variance
- cost_mean
- cost_variance
- premature_stop_rate
- over_action_rate
- inconsistent_decision_rate

## Regola di promozione (fissata a priori)

Qwen diventa default solo se:

1. completion rate >= MiniMax
2. varianza <= MiniMax su completion e turns
3. nessun peggioramento netto su premature stop e over-action
4. costo medio inferiore
5. comportamento consistente tra run

Altrimenti:

- MiniMax resta default
- Qwen resta fallback economico / challenger ricorrente

