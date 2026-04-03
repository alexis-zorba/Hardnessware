# HARDNESS Routing & Runtime Policy (Frozen Baseline)

Stato policy operativo corrente, consolidato dopo Round 6.

## 1) Routing policy (attiva)

- `default_executor = minimax/minimax-m2.7`
- `premium_escalation = anthropic/claude-sonnet-4.6` (solo su trigger espliciti)
- `opportunistic_qwen = disabled`
- `qwen_status = periodic challenger only`

## 2) Principi decisionali vincolanti

1. il default **non** si sceglie su costo puro
2. la stabilità pesa più della performance media puntuale
3. i path ibridi si attivano solo con evidenza quantitativa stabile
4. decisioni negative motivate sono outcome validi

## 3) Evidenze sintetiche

- Round 5 Phase B: Qwen non promosso a default per instabilità
  - riferimento: [`docs/hardness_round5_phaseB_report.md`](docs/hardness_round5_phaseB_report.md)
- Round 6 opportunistico: Qwen opportunistico non adottato in produzione
  - riferimento: [`docs/hardness_round6_opportunistic_report.md`](docs/hardness_round6_opportunistic_report.md)

## 4) Guardrail di runtime da preservare

Le seguenti protezioni restano obbligatorie:

- routing low-risk per opportunistic in [`ModelRouter.route()`](src/hardness/router.py:14)
- blocco task non low-risk in [`ModelRouter._is_low_risk_task()`](src/hardness/router.py:54)
- stop/convergenza nel loop in [`AgentLoop.run()`](src/hardness/agent.py:32)

## 5) Prossima fase autorizzata

Priorità operativa:

1. consolidamento baseline produzione-lite (policy + metriche + report standard)
2. benchmark ROI premium: MiniMax-only vs MiniMax+Sonnet escalation su trigger espliciti
3. ampliamento challenge set con casi realistici (ambiguità, rumore, write+verify, stop judgement)

## 6) Cose esplicitamente fuori scope ora

- nuovi challenger free in routing opportunistico produttivo
- nuova complessità architetturale non necessaria (multi-agent operativo, memoria avanzata)
- nuovi provider nel path core prima della chiusura benchmark premium

Questo documento rappresenta la baseline decisionale fino a nuova evidenza quantitativa.
