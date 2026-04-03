# HARDNESS V1 Scope Decision

## Approved Knowledge Base Structure

```text
HARDNESS/
├── 01_patterns/
│   ├── memory.md
│   ├── agent_loop.md
│   ├── tool_system.md
│   └── context_management.md
├── 02_reference_impl/
│   ├── claw-code/
│   └── claurst/
├── 03_prompts/
│   └── system_patterns.md
├── 04_analysis/
│   └── curated_sources.md
└── 05_synthesis/
    ├── design_principles.md
    └── minimal_architecture.md
```

## Included Sources

### Reference implementations

1. `instructkr/claw-code` (Python)
2. `Kuberwastaken/claurst` (Rust)

### Prompts

1. public Claude Code system prompt reference

### Curated analyses

1. `claurst` README
2. Kuber Studio technical blog post
3. Alex Kim analysis
4. Sebastian Raschka analysis
5. `ccunpacked.dev` as visual reference

## HARDNESS V1 Implementation Scope

### Include

- `ProviderAdapter` abstraction
- provider support targets:
  - OpenAI
  - Groq
  - OpenRouter
- single orchestrating `AgentLoop`
- `MemoryManager` with 3 logical layers:
  - active session context
  - indexed durable notes
  - retrievable evidence/transcript layer
- `ToolRegistry` with initial tools:
  - read
  - write
  - search
- `PolicyEngine` for permission checks and command safety
- local `StateStore`
- structured tracing/event log
- explicit plan/act/verify/update cycle

### Exclude from V1

- multi-agent execution
- daemon or always-on background mode
- dream or auto-consolidation workers
- browser automation
- provider-specific advanced optimizations
- speculative hidden features copied from external systems

## Why This Scope

This scope is the smallest one that is:

- portable across providers
- implementable without infrastructure lock-in
- close enough to production shape to avoid toy architecture
- narrow enough to study and build quickly

## Immediate Next Execution Order

1. create `HARDNESS/` knowledge base folders
2. archive curated sources and notes
3. synthesize patterns into reusable design principles
4. implement minimal provider-agnostic harness
5. validate against OpenAI, Groq, and OpenRouter adapters
