# HARDNESS Round 4 — Escalation Policy (Misurabile)

Policy operativa per routing ibrido:

- default executor: `minimax/minimax-m2.7`
- premium escalation: `anthropic/claude-sonnet-4.6`

Implementazione di riferimento: [`should_escalate()`](scripts/round4_hybrid_benchmark.py:127).

## Trigger espliciti

Escalation a premium se almeno una condizione è vera:

1. `status != ok`
2. `stop_reason` non in `{stop, write_completed, completed}`
3. `turns >= 4`
4. `final_after_success_rate < 1.0` **e** `turns >= 3`
5. `duplicate_action_rate > 0.0`
6. `no_progress_stop_count > 0`

## Obiettivo

Comprare qualità premium solo quando il baseline mostra segnali misurabili di fatica/instabilità.

## Vincolo

Nessuna escalation “a intuito”: ogni passaggio premium deve essere tracciabile a uno dei trigger sopra.

