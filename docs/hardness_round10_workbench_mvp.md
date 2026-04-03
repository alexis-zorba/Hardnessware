# HARDNESS Round 10 — Workbench MVP (FastAPI + React)

## Obiettivo

Trasformare HARDNESS da harness CLI a cockpit operativo minimo con:

- backend API HTTP in FastAPI
- frontend React a 4 pannelli
- streaming eventi live
- file browser workspace
- diff viewer base
- persistenza sessione e run locale

## Scope MVP implementato

### Backend

- API FastAPI in [`app/main.py`](app/main.py)
- servizio applicativo in [`WorkbenchService`](app/workbench.py:30)
- creazione sessione, esecuzione task, messaggi, interrupt
- stream eventi in SSE (`text/event-stream`)
- file listing workspace e diff testuale unificato
- estrazione metriche ultimo run o run specifico

### Frontend

- shell React + Vite in [`frontend/src/App.jsx`](frontend/src/App.jsx)
- layout 4 pannelli in [`frontend/src/styles.css`](frontend/src/styles.css)
- wiring API base verso backend (`/session`, `/run`, `/events`, `/files`, `/diffs`)
- stream live eventi via `EventSource`

## Contratto API MVP

Endpoint principali esposti in [`app/main.py`](app/main.py):

- `POST /session`
- `POST /session/{session_id}/run`
- `POST /session/{session_id}/message`
- `POST /session/{session_id}/reply`
- `POST /session/{session_id}/resume`
- `POST /session/{session_id}/interrupt`
- `GET /session/{session_id}`
- `GET /session/{session_id}/events`
- `GET /session/{session_id}/files`
- `GET /session/{session_id}/diffs`
- `GET /session/{session_id}/metrics`
- `GET /health`

## Flusso interattivo (MITL)

Il Workbench supporta ora una modalità man-in-the-loop cooperativa:

1. l'agent esegue la run e può fermarsi con `stop_reason="needs_clarification"`
2. la sessione passa a stato `waiting_for_input`
3. il frontend mostra la domanda di chiarimento
4. l'utente invia `POST /session/{id}/reply`
5. l'utente riprende con `POST /session/{id}/resume`

Stati sessione principali:

- `idle`
- `running`
- `waiting_for_input`
- `interrupted`
- `completed`

L'interrupt è cooperativo: `POST /session/{id}/interrupt` viene verificato dal loop agent a ogni turn/tool e produce `stop_reason="user_interrupted"`.

## Continuità e checkpoint

- bridge memoria: i messaggi recenti di sessione vengono iniettati nel contesto run successivo
- checkpoint minimale persistito in `storage/checkpoints/*.json` a ogni run, utile per resume e audit

## Architettura

### Backend runtime

[`WorkbenchService`](app/workbench.py:30) usa:

- [`AgentLoop`](src/hardness/agent.py:18) per il run agentico
- [`HardnessConfig`](src/hardness/config.py:59) per configurazione per-sessione
- storage locale per sessione in `.hardness-workbench/<session_id>`

Event sourcing MVP:

- gli eventi sono letti dai run JSON del `StateStore`
- lo stream SSE pubblica payload incrementali con polling leggero

### Frontend runtime

[`App()`](frontend/src/App.jsx:17) mantiene stato locale:

- session id corrente
- task input
- activity log live
- file list
- diff corrente
- metrics + final text

## UX 4 pannelli

1. Chat/Final output
2. Activity (eventi live)
3. Workspace (file list)
4. Result/Diff/Metrics

Riferimento implementativo: [`frontend/src/App.jsx`](frontend/src/App.jsx).

## Persistenza base

- session state in memoria processo backend
- run/events/artifacts persistiti su filesystem locale tramite stack HARDNESS esistente
- baseline diff per file mantenuta per sessione in memoria (`baseline_files`)

## Vincoli noti MVP

- nessuna auth
- CORS permissivo (`*`) per bootstrap locale
- interrupt è flag di sessione (non kill hard del loop in corso)
- frontend senza routing e senza stato persistente browser

## Dipendenze

Aggiunte in [`pyproject.toml`](pyproject.toml):

- `fastapi`
- `uvicorn`

Frontend in [`frontend/package.json`](frontend/package.json):

- `react`, `react-dom`, `vite`

## Avvio locale (manuale)

Backend:

- `python -m uvicorn app.main:app --reload --port 8000`

Frontend:

- `cd frontend`
- `npm install`
- `npm run dev`

## Script Windows `.bat` (setup rapido)

Per semplificare installazione e avvio su Windows sono stati aggiunti:

- installazione dipendenze backend+frontend: [`install_workbench.bat`](install_workbench.bat)
- avvio backend FastAPI: [`start_backend.bat`](start_backend.bat)
- avvio frontend Vite/React: [`start_frontend.bat`](start_frontend.bat)

## Deliverable Round 10 (MVP)

- backend API Workbench: completato
- frontend cockpit 4 pannelli: completato
- streaming eventi SSE: completato
- file browser + diff base + metrics view: completato
- handoff tecnico Round 10: completato
