# HARDNESS Round 2.1 — Root Cause Analysis (`T05`)

## Caso analizzato

- Task: `write tmp/note.txt with a short status note`
- Run osservata: [`run-20260401T101616581784Z.json`](.hardness-round2/runs/run-20260401T101616581784Z.json)
- Stop reason precedente: `max_turns_reached`

## Evidenze chiave dal trace

1. Turno 1: `write` riuscita e verificata (`write_verified=true`)
2. Turno 2: il modello emette `tool_call` con nome `final` (non tool valido)
3. Il core interpreta `final` come tool non registrato → `tool_failures += 1`
4. Turni successivi: ulteriori `write` sullo stesso file
5. Chiusura forzata solo per limite turni (`max_turns_reached`)

## Causa radice

Mismatch di contratto operativo:

- il modello ha usato una decisione di controllo (`final`) nel canale tool-call
- il core non gestiva esplicitamente `final/stop/needs_clarification` come decisioni di controllo

Effetto:

- mancata chiusura elegante
- incremento turni/costo

## Patch minima applicata

In [`AgentLoop.run()`](src/hardness/agent.py:31):

1. **Control-tool handling**
   - se `tool_call.name` è in `{final, stop, needs_clarification}`, il loop chiude con `stop_decision` esplicita

2. **Write completion gate**
   - se task inizia con `write ` e la write è verificata, chiusura immediata con `stop_reason=write_completed`

## Risultato post-patch

Nella nuova baseline:

- scompare `max_turns_reached`
- distribuzione stop reason: `stop=11`, `write_completed=1`
- turni medi scendono a `1.9167` (da `2.1667`)

## Conclusione

Il problema era locale e correggibile con patch minima, senza rifattorizzazioni estese.

