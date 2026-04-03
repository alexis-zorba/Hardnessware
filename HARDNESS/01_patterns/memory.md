# Memory Pattern

## Goal

Keep long-horizon agent work stable without flooding the active context window.

## Three-layer model

### Layer 1 — active memory index

- very small always-available index
- stores pointers, labels, and retrieval hints
- should be cheap enough to inject every turn

Recommended HARDNESS form:

- `MEMORY.md` or equivalent compact index
- short entries only
- no verbose narrative

### Layer 2 — topic notes

- durable notes grouped by topic
- loaded only when relevant
- should contain distilled facts, conventions, and stable findings

Recommended HARDNESS form:

- markdown notes under a memory directory
- frontmatter or metadata headers for quick scanning
- categories like project, user, convention, investigation, reference

### Layer 3 — evidence and transcripts

- raw or semi-raw historical material
- not injected by default
- searched only on demand

Recommended HARDNESS form:

- run logs, execution traces, transcripts, verification artifacts
- indexed separately from stable notes

## Core behaviors

### Selective retrieval

- scan metadata first
- read full content only for high-relevance items
- keep retrieval budget explicit

### Verification before promotion

- memory must not become a source of hallucinated truth
- any note promoted from a transient observation should be checked against current code or current system state

### Freshness warnings

- older memory should carry a staleness caveat
- agent should treat memory as point-in-time evidence, not live fact

### Deduplication and consolidation

- merge overlapping notes
- delete obsolete fragments
- promote recurring stable observations into durable notes

## HARDNESS decision

Phase 1 implementation should include:

- session context
- indexed durable notes
- retrievable run artifacts

Phase 1 should exclude:

- autonomous dream workers
- background consolidation daemons

## Portability principle

This memory model must work identically whether the provider is OpenAI, Groq, or OpenRouter. Retrieval logic belongs to HARDNESS, not to the model vendor.
