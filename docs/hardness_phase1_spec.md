# HARDNESS Phase 1 Specification

## Objective

Build a model-agnostic agent harness that optimizes for:

- maximum signal
- minimum noise
- real transferability across providers

Phase 1 excludes any original leaked source code and focuses only on reusable, abstractable, and verifiable material.

## Curation Principles

Keep only material that is:

1. reusable
2. abstractable
3. verifiable

Reject material that is primarily hype, legally risky, or too coupled to private infrastructure.

## Phase 1 Knowledge Taxonomy

### A. Core Architectural Patterns — keep

Highest-priority study area.

Includes:

- memory architecture
- agent loop
- tool orchestration
- context management
- error recovery

Target outputs:

- pattern summaries
- reusable abstractions
- implementation constraints

### B. Clean-room Reference Implementations — keep, but selective

Include only 1–2 repositories max.

Selection criteria:

- readable structure
- limited over-engineering
- useful for implementation mapping

Role:

- concrete reference
- implementation sanity check

### C. System Prompt and Behavior Design — keep, secondary

Includes:

- public system prompts
- instruction hierarchy patterns
- behavior stability techniques

Role:

- improve consistency
- shape agent behavior

Constraint:

- must not dominate the study

### D. Technical Analyses — keep, curated

Include only 3–5 quality sources.

Selection criteria:

- mechanism-focused
- low hype
- concrete architectural insight

Role:

- accelerate understanding
- support synthesis

### E. Original leaked code — exclude

Reasons:

- legal and DMCA risk
- poor signal-to-noise ratio
- risk of copying instead of understanding
- dependence on private infrastructure

### F. Social hype and short-form commentary — exclude

Reasons:

- distortion
- cherry-picking
- poor structural value

### G. Advanced features such as daemon modes and dream systems — defer

Examples:

- background agents
- auto-dream flows
- multi-agent orchestration

Decision:

- document conceptually
- exclude from initial implementation scope

## Proposed Archive Structure

```text
HARDNESS/
│
├── 01_patterns/
│   ├── memory.md
│   ├── agent_loop.md
│   ├── tool_system.md
│   ├── context_management.md
│   └── error_recovery.md
│
├── 02_reference_impl/
│   ├── python_agent_notes.md
│   └── rust_agent_notes.md
│
├── 03_prompts/
│   └── system_patterns.md
│
├── 04_analysis/
│   └── curated_articles.md
│
└── 05_synthesis/
    ├── design_principles.md
    └── minimal_architecture.md
```

## Proposed HARDNESS Baseline

Recommended profile: balanced baseline with strict scope control.

### Include in v1

- one orchestrating agent loop
- provider adapter abstraction
- support for OpenAI, Groq, and OpenRouter through a unified interface
- three-layer memory model:
  - session state
  - indexed durable notes
  - retrievable evidence or transcripts
- tool registry with 3 initial tools:
  - read
  - write
  - search
- policy layer for tool permissions and validation
- persistent state store for runs, notes, and artifacts
- explicit think → act → verify → update loop

### Exclude from v1

- autonomous daemon mode
- always-on agents
- multi-agent fan-out execution
- speculative dream or background consolidation workers
- provider-specific optimizations that break portability

## Design Principles for a Model-Agnostic Harness

1. provider-neutral core contracts
2. prompt templates separated from provider transport
3. tools represented as typed capabilities, not hardcoded prompt text
4. memory retrieval independent from model vendor
5. deterministic state transitions around non-deterministic model calls
6. verification before memory promotion
7. graceful degradation when a provider lacks a feature

## Immediate Decision for Next Step

Use a standard-but-curated Phase 1 workflow:

- 1 Python clean-room reference
- optional 1 Rust architectural reference
- public system prompts
- 3–5 curated technical analyses
- no original leaked source code

## Implementation Candidate for Phase 1

Phase 1 prototype should be a minimal but production-shaped harness:

- `ProviderAdapter`
- `AgentLoop`
- `MemoryManager`
- `ToolRegistry`
- `PolicyEngine`
- `StateStore`

This is the smallest scope that preserves transferability and real implementation value.
