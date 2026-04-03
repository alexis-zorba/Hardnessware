# HARDNESS Design Principles

## Objective

HARDNESS must be a provider-agnostic agent harness that preserves execution quality across [`OpenAI`](HARDNESS/05_synthesis/design_principles.md), [`Groq`](HARDNESS/05_synthesis/design_principles.md), and [`OpenRouter`](HARDNESS/05_synthesis/design_principles.md) without depending on vendor-specific runtime behavior.

## Core principles

### 1. The harness owns execution discipline

The model supplies reasoning and tool intent.
HARDNESS owns:

- state transitions
- tool safety
- memory retrieval
- verification rules
- persistence

This prevents quality collapse when switching vendors.

### 2. The provider boundary must be thin

Provider-specific code should be limited to:

- request formatting
- response normalization
- tool call translation
- streaming normalization
- model capability metadata

Everything else belongs in the core harness.

### 3. Memory must be layered, not bloated

Persistent memory should be split into:

- active session context
- indexed durable notes
- retrievable evidence

This keeps the live prompt small while preserving long-horizon continuity.

### 4. Verification precedes memory promotion

No observation should become durable memory unless checked against current evidence.
Memory is a working aid, not a truth oracle.

### 5. Tool use must be capability-driven

The model should see a stable tool interface.
Each tool must expose:

- name
- description
- schema
- policy requirements
- normalized result shape

### 6. Prompt assembly must separate stable from volatile context

HARDNESS should assemble prompts from distinct layers:

- stable policy and system rules
- semi-stable project guidance
- dynamic task state
- retrieved memory
- latest tool outputs

This improves cacheability, traceability, and portability.

### 7. Deterministic outer loop, non-deterministic inner model

Model calls are probabilistic.
The surrounding harness should not be.

Run lifecycle, retries, persistence, permission checks, and stop conditions should be deterministic.

### 8. Observability is part of architecture

Every turn should emit structured trace data for:

- prompt assembly
- tool selection
- tool execution
- verification outcome
- memory updates
- provider usage and failure mode

### 9. Graceful degradation beats hidden coupling

If one provider lacks a feature, HARDNESS should degrade predictably instead of forking the architecture.

### 10. Phase 1 optimizes for correctness and transferability

HARDNESS v1 should not chase:

- multi-agent novelty
- daemon autonomy
- speculative background cognition

It should prove the core loop first.

## What to keep out of the core

- provider-specific prompt tricks
- leaked-system mimicry that cannot be justified architecturally
- background systems not required for correctness
- unbounded tool growth before policy maturity

## Architectural consequence

The first correct HARDNESS should look like a small operating system for agent execution, not like a large collection of prompts.
