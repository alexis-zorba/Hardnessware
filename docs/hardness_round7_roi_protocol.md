# HARDNESS Round 7 — Premium Escalation ROI Protocol

## Obiettivo

Misurare il ROI reale di escalation premium:

- baseline: `minimax/minimax-m2.7`
- hybrid: MiniMax default + Sonnet escalation a trigger espliciti

La domanda decisionale è unica: **il premium compra abbastanza qualità sui task difficili per giustificare il costo extra?**

## Scope vincolato

- stesso provider: OpenRouter
- stessi tool/policy/loop HARDNESS
- nessun nuovo challenger/provider nel path core

Challenge set di riferimento:

- [`HARDNESS/05_synthesis/challenge_set_round4.json`](HARDNESS/05_synthesis/challenge_set_round4.json)

Runner Round 7:

- [`scripts/round7_premium_roi_benchmark.py`](scripts/round7_premium_roi_benchmark.py)

## Trigger escalation (espliciti)

Escalation Sonnet se almeno una condizione è vera.

### A) Trigger pre-run (task risk)

1. task ambiguo o ad alta incertezza (`ambiguous`, `uncertainty`, `conflict`, `decide`)
2. write delicato o multi-file (`write`, `policy`, `multi_file`, `routing_contract`)
3. search rumoroso / confliggente (`nonexistent`, `noisy`, `signal_extraction`, `across docs`)

### B) Trigger post-run (evidenza runtime)

1. `status != ok`
2. `stop_reason` non in `{stop, write_completed, completed}`
3. `needs_clarification`/`none`/`max_turns_reached`
4. `duplicate_action_rate > 0`
5. `no_progress_stop_count > 0`
6. secondo fallimento consecutivo sullo stesso task

## Metriche obbligatorie

Confronto tra baseline e hybrid su:

1. `completion_rate`
2. `difficult_completion_rate` (subset task difficili)
3. `mean_turns_per_task`
4. `mean_cost_per_task_usd`
5. `escalation_rate`
6. `escalation_cost_mean_usd`
7. `quality_gain_per_extra_usd` (improvement per dollar)

## Regola decisionale Round 7

Escalation premium confermata solo se tutte vere:

1. `difficult_completion_rate_hybrid > difficult_completion_rate_baseline`
2. `escalation_rate <= 0.35`
3. `mean_cost_per_task_usd` non cresce oltre soglia accettata (`<= +2.0x` baseline)
4. `quality_gain_per_extra_usd > 0`

Altrimenti:

- MiniMax-only resta configurazione primaria
- escalation Sonnet va ulteriormente ristretta

