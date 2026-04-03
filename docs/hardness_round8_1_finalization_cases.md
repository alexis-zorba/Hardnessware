# HARDNESS Round 8.1 — Finalization Case Extraction (from Round 8)

Fonte dati:

- [`docs/hardness_round8_metrics.json`](docs/hardness_round8_metrics.json)

## Casi con successo utile ma chiusura imperfetta

Selezione: run con `status=ok` e `final_after_success_rate < 1.0`.

1. `R801` — `ambiguous_router_contract`
   - stop: `stop`
   - turns: `3`
   - tool_calls: `3`
   - final_after_success_rate: `0.3333`

2. `R802` — `noisy_search_metrics`
   - stop: `stop`
   - turns: `3`
   - tool_calls: `2`
   - final_after_success_rate: `0.5`

3. `R803` — `write_verify_status_note`
   - stop: `write_completed`
   - turns: `1`
   - tool_calls: `1`
   - final_after_success_rate: `0.0`

4. `R804` — `write_policy_guardrail_note`
   - stop: `write_completed`
   - turns: `1`
   - tool_calls: `1`
   - final_after_success_rate: `0.0`

## Tassonomia failure mode Round 8.1

Categorie operative (mutualmente non esclusive):

1. `over-action after success`
2. `weak final answer`
3. `missing explicit completion`
4. `late stop`
5. `success not recognized`
6. `write success not sealed`

Uso previsto: classificazione automatica nel runner Round 8.1 e confronto pre/post patch su [`AgentLoop.run()`](src/hardness/agent.py:32).

