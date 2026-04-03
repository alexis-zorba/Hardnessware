# HARDNESS Round 5 — Phase A Tournament Report

## Scope eseguito

Phase A challenger bracket richiesto:

- `minimax/minimax-m2.7`
- `deepseek/deepseek-v3.2`
- `qwen/qwen3.6-plus-preview:free`
- `nvidia/nemotron-3-super-120b-a12b:free`

Provider:

- OpenRouter

Runner:

- [`scripts/round5_phase_a_tournament.py`](scripts/round5_phase_a_tournament.py)

Output raw usati per questo report:

- quick run (`--max-tasks 3`): [`docs/hardness_round5_phaseA_metrics_quick.json`](docs/hardness_round5_phaseA_metrics_quick.json)
- full run (10 task): [`docs/hardness_round5_phaseA_metrics.json`](docs/hardness_round5_phaseA_metrics.json)

Nota esecuzione:

- il quick run è stato usato per decisione provvisoria rapida
- il full run è stato completato dopo e costituisce la base decisionale definitiva di Phase A

## Compatibilità

Tutti i 4 modelli hanno superato i probe:

- basic: PASS
- structured: PASS
- tool: PASS

Dettagli in [`docs/hardness_round5_phaseA_metrics_quick.json`](docs/hardness_round5_phaseA_metrics_quick.json).

## Risultati sintetici (full run, 10 task)

### MiniMax M2.7

- completion rate: 0.9
- mean turns/task: 2.7
- final_after_success_rate: 0.2733
- mean cost/task: $0.01896433
- stop_reason_distribution: `stop=5`, `write_completed=2`, `max_turns_reached=2`, `none=1`

### DeepSeek V3.2

- completion rate: 1.0
- mean turns/task: 3.2
- final_after_success_rate: 0.0333
- mean cost/task: $0.01345469
- stop_reason_distribution: `max_turns_reached=5`, `redundant_read_suppressed=2`, `write_completed=2`, `stop=1`

### Qwen 3.6 Plus Preview (free)

- completion rate: 0.9
- mean turns/task: 2.6
- final_after_success_rate: 0.4283
- mean cost/task: $0.0 (provider_cost_usd=0 nel trace)
- stop_reason_distribution: `stop=7`, `write_completed=2`, `none=1`

### Nemotron 3 Super (free)

- completion rate: 0.6
- mean turns/task: 2.9
- final_after_success_rate: 0.0833
- mean cost/task: $0.0 (provider_cost_usd=0 nel trace)
- stop_reason_distribution: `stop=2`, `none=4`, `write_completed=2`, `max_turns_reached=2`

## Ranking emerso

### Quick run (3 task)

- quality rank:
  1. `qwen/qwen3.6-plus-preview:free`
  2. `minimax/minimax-m2.7`
  3. `deepseek/deepseek-v3.2`
  4. `nvidia/nemotron-3-super-120b-a12b:free`

- cost rank:
  1. `qwen/qwen3.6-plus-preview:free`
  2. `nvidia/nemotron-3-super-120b-a12b:free`
  3. `deepseek/deepseek-v3.2`
  4. `minimax/minimax-m2.7`

### Full run (10 task, ranking automatico runner)

- quality rank:
  1. `deepseek/deepseek-v3.2`
  2. `qwen/qwen3.6-plus-preview:free`
  3. `minimax/minimax-m2.7`
  4. `nvidia/nemotron-3-super-120b-a12b:free`

- cost rank:
  1. `qwen/qwen3.6-plus-preview:free`
  2. `nvidia/nemotron-3-super-120b-a12b:free`
  3. `deepseek/deepseek-v3.2`
  4. `minimax/minimax-m2.7`

## Decisione operativa (Phase A, consolidata)

1. mantenere `minimax/minimax-m2.7` come baseline ufficiale e affidabile
2. confermare `qwen/qwen3.6-plus-preview:free` come challenger prioritario (forte su costo e buono su convergenza)
3. mantenere `deepseek/deepseek-v3.2` come candidato secondario: completion alta ma stabilità/convergenza peggiori (molti `max_turns_reached`)
4. mantenere `nvidia/nemotron-3-super-120b-a12b:free` come fallback free, non challenger principale

## Prossimo passo consigliato

Round 5 Phase B su 2 soli candidati:

- baseline: `minimax/minimax-m2.7`
- challenger: `qwen/qwen3.6-plus-preview:free`

con focus su stabilità (error rate/`none` stop), non solo su costo medio.
