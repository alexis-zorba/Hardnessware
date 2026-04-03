# HARDNESS Round 2 — Operational Decision

## Executive Decision

Baseline ufficiale per la prossima validazione agentica:

- Provider: **OpenRouter**
- Model: **MiniMax M2.7**

Groq viene sospeso come target operativo finché non supera la compatibility suite sul basic path.

---

## 1) Stato architetturale

Il sistema ha separato con successo due piani distinti:

1. qualità/convergenza dell'agente
2. compatibilità provider

Contributi principali già presenti:

- convergenza e stop conditions in [`AgentLoop.run()`](src/hardness/agent.py:31)
- output contract esplicito in [`DecisionType`](src/hardness/types.py:8)
- metriche di convergenza in [`RunMetrics`](src/hardness/types.py:52)
- probe provider (`basic`, `structured`, `tool`) in [`OpenAICompatibleAdapter.run_probe()`](src/hardness/providers.py:90)
- suite compatibilità separata in [`tests/test_compatibility.py`](tests/test_compatibility.py)

---

## 2) Esito compatibilità backend

### OpenRouter + MiniMax M2.7

- basic: PASS
- structured: PASS
- tool: PASS

Stato: compatibile per task suite agentica.

### Groq + Llama 3.3 70B Versatile

- basic: FAIL
- structured: FAIL
- tool: FAIL
- errore osservato: `403 / error code 1010`

Stato: incompatibile sul percorso minimo; non idoneo come baseline corrente.

---

## 3) Decisione operativa

1. Promuovere OpenRouter/M2.7 a baseline ufficiale.
2. Congelare Groq come target operativo (non eliminare integrazione).
3. Eseguire la prossima task suite reale solo su baseline compatibile.
4. Aprire un binario separato per recovery Groq.

---

## 4) Binario separato: Groq Recovery

Checklist recovery:

1. verifica credenziali/perimetro account
2. verifica endpoint e naming modello realmente abilitato
3. probe esterna minimale fuori da HARDNESS
4. riesecuzione compatibility suite interna

Solo dopo PASS su `basic` e `structured`, Groq rientra nel confronto agentico.

---

## 5) Prossima fase (ordine disciplinato)

1. report comparativo formale su baseline OpenRouter/M2.7
2. task suite reale con metriche:
   - completion rate
   - cost per task
   - redundant action rate
   - final_after_success_rate
   - failure modes residui
3. confronto premium reference in seconda passata (non default)

---

## 6) Criterio di avanzamento

La fase successiva è accettata quando:

- baseline OpenRouter resta stabile sulla task suite
- convergenza migliora in modo misurabile
- Groq recovery chiarisce in modo definitivo causa e rimedio (o esclusione)

