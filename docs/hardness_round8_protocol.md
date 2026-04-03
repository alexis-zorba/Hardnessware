# HARDNESS Round 8 — Challenge Set Quality & Failure Mode Protocol

## Obiettivo

Migliorare il sistema **a parità di modello** (`minimax/minimax-m2.7`) tramite:

1. challenge set più realistico
2. analisi failure mode run-by-run
3. decisioni di hardening su loop/prompt/policy senza introdurre nuovi modelli o routing

## Vincoli

- modello unico: `minimax/minimax-m2.7`
- nessuna escalation premium
- nessun routing opportunistico
- focus esclusivo su qualità operativa del sistema

## Evidenze di partenza (Round 6/7)

Da metriche aggregate recenti:

- Round 6 full: over-action rate ~`0.0833`, inconsistent task rate elevato
- Round 7 full: over-action rate ~`0.125`, inconsistenza task presente
- no-progress quasi assente, quindi il rischio principale è **decision instability + azioni eccessive** più che stallo puro

## Challenge set Round 8

File target:

- [`HARDNESS/05_synthesis/challenge_set_round8.json`](HARDNESS/05_synthesis/challenge_set_round8.json)

Design criteria:

1. ambiguità reale (`ambiguous`, `uncertain`, `conflicting signal`)
2. rumore search (`nonexistent token`, segnali multipli)
3. write + verify (`write` policy-sensitive)
4. casi stop-vs-act difficili
5. multi-file read/summarize con chiusura deterministica

## Runner Round 8

- [`scripts/round8_failure_mode_benchmark.py`](scripts/round8_failure_mode_benchmark.py)

Output raw:

- `docs/hardness_round8_metrics.json`

## Metriche obbligatorie

1. `completion_rate_mean`, `completion_rate_variance`
2. `turns_mean`, `turns_variance`
3. `over_action_rate`
4. `no_progress_rate`
5. `inconsistent_decision_rate`
6. `premature_stop_rate`
7. `final_after_success_mean`
8. `stop_reason_distribution`
9. `failure_modes_top`

## Regola decisionale Round 8

Hardening Round 8 considerato efficace se:

1. `completion_rate_mean >= baseline recente`
2. `over_action_rate` in calo misurabile
3. `inconsistent_decision_rate` in calo misurabile
4. nessun aumento materiale di `premature_stop_rate`

Se non soddisfatto:

- mantenere baseline corrente
- usare output failure-mode per priorità patch successive su convergenza/stop policy

