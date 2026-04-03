# HARDNESS Round 2 Validation Report

## 1) Perimetro del test

Baseline ufficiale eseguita:

- Provider: OpenRouter
- Modello: `minimax/minimax-m2.7`

Perimetro coerente con la decisione operativa in [`docs/hardness_round2_operational_decision.md`](docs/hardness_round2_operational_decision.md).

Task suite usata:

- [`HARDNESS/05_synthesis/task_suite.json`](HARDNESS/05_synthesis/task_suite.json)
- totale task: 12

Runner usato:

- [`scripts/round2_validation_runner.py`](scripts/round2_validation_runner.py)

Output raw dei risultati:

- [`docs/hardness_round2_metrics.json`](docs/hardness_round2_metrics.json)

---

## 2) Configurazione usata

- agent loop con convergenza hardenizzata in [`AgentLoop.run()`](src/hardness/agent.py:31)
- contratto output con decision types in [`DecisionType`](src/hardness/types.py:8)
- metriche di convergenza in [`RunMetrics`](src/hardness/types.py:58)
- prompt contract rafforzato in [`SYSTEM_PROMPT`](src/hardness/prompting.py:6)
- provider adapter e probe compatibilità in [`OpenAICompatibleAdapter.run_probe()`](src/hardness/providers.py:90)

Prezzi usati per la stima costo (OpenRouter M2.7):

- input: $0.30 / 1M token
- output: $1.20 / 1M token

---

## 3) Metriche aggregate

Da [`docs/hardness_round2_metrics.json`](docs/hardness_round2_metrics.json):

- completion rate: **1.0**
- mean turns per task: **2.1667**
- duplicate action rate avg: **0.0**
- redundant read rate avg: **0.0**
- final_after_success_rate avg: **0.9167**
- stop reason distribution:
  - `stop`: 11
  - `max_turns_reached`: 1
- mean cost per task: **$0.00378357**
- total estimated cost: **$0.0454029**
- cost coverage: **12/12 task**

---

## 4) Failure mode principali (3–5)

### FM-1: mancata chiusura su task di write (`T05`)

- evidenza: unico task con `max_turns_reached`
- implicazione: il gate post-tool ha migliorato la convergenza generale, ma il path write richiede un criterio di finalizzazione ancora più netto

### FM-2: assenza di failure mode sistemici nel baseline

- evidenza: nessun provider error nella run baseline OpenRouter
- implicazione: baseline idonea per continuare ottimizzazione qualità/costo senza blocchi infrastrutturali

### FM-3: finalization non perfetta ma alta

- evidenza: `final_after_success_rate` = 0.9167
- implicazione: miglioramento evidente, ma ancora margine sul subset di task con azione write o semantica ambigua

---

## 5) Decisione successiva

Decisione operativa confermata:

1. mantenere OpenRouter + M2.7 come baseline ufficiale
2. avviare iterazione mirata su convergenza post-write
3. mantenere Groq in binario separato recovery (nessun impatto sul core)
4. introdurre premium reference solo dopo nuova run con metriche migliorate

---

## 6) Azioni immediate consigliate (Round 2.1)

1. aggiungere write-finalization gate specifico in [`AgentLoop.run()`](src/hardness/agent.py:31)
2. aggiungere metrica `write_finalization_rate` in [`RunMetrics`](src/hardness/types.py:58)
3. rieseguire la stessa suite con confronto pre/post su:
   - `max_turns_reached`
   - `final_after_success_rate`
   - costo medio per task

