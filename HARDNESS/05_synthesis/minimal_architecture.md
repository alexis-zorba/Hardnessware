# HARDNESS Minimal Architecture

## Phase 1 target

Build a minimal harness that is small enough to implement quickly but shaped like a real system.

## Components

### [`ProviderAdapter`](HARDNESS/05_synthesis/minimal_architecture.md)

Normalizes interaction with provider APIs.

Responsibilities:

- build vendor request payloads
- normalize message and tool-call responses
- expose capability flags
- unify errors

Concrete adapters planned:

- `OpenAIAdapter`
- `GroqAdapter`
- `OpenRouterAdapter`

### [`AgentLoop`](HARDNESS/05_synthesis/minimal_architecture.md)

Owns the turn lifecycle.

Cycle:

1. collect live state
2. retrieve relevant memory
3. assemble prompt
4. ask provider
5. execute requested tool or finalize answer
6. verify result
7. persist state and traces

### [`MemoryManager`](HARDNESS/05_synthesis/minimal_architecture.md)

Implements three logical layers:

- active session state
- durable indexed notes
- retrievable artifacts and transcripts

Operations:

- select relevant notes
- add verified notes
- store evidence
- compact stale session material

### [`ToolRegistry`](HARDNESS/05_synthesis/minimal_architecture.md)

Maintains available tools and schemas.

Phase 1 tools:

- `read`
- `write`
- `search`

### [`PolicyEngine`](HARDNESS/05_synthesis/minimal_architecture.md)

Guards tool execution.

Phase 1 checks:

- allowed paths
- write restrictions
- schema validation
- command-risk placeholder interface for future shell tools

### [`StateStore`](HARDNESS/05_synthesis/minimal_architecture.md)

Stores local run state.

Phase 1 format:

- JSON files on disk

Stored entities:

- run metadata
- event trace
- durable memory notes
- artifacts

## Runtime flow

```text
User Task
   ↓
AgentLoop
   ├─→ MemoryManager.retrieve()
   ├─→ PromptAssembler.build()
   ├─→ ProviderAdapter.generate()
   ├─→ ToolRegistry.resolve()
   ├─→ PolicyEngine.authorize()
   ├─→ Tool.execute()
   ├─→ Verifier.check()
   └─→ StateStore.persist()
```

## Provider-agnostic contract

The core loop should depend on one internal response model:

- assistant text chunks
- tool call requests
- finish reason
- usage metadata

Adapters convert vendor payloads into this internal contract.

## What Phase 1 excludes

- coordinator mode
- sub-agents
- background jobs
- browser automation
- provider-specific caching features
- hidden prompt gymnastics tied to one vendor

## Why this architecture is efficient

- minimal component count
- clear seams for testing
- portable across vendors
- directly extensible to later multi-agent or daemon layers

## Proposed implementation order

1. core models and config
2. state store
3. memory manager
4. tool registry and three tools
5. provider adapter abstraction
6. agent loop
7. tracing and verification hooks
