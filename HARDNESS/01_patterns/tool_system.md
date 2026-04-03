# Tool System Pattern

## Goal

Make tool use disciplined, inspectable, and safe.

## Tool registry model

- tools are registered centrally
- each tool exposes a stable schema
- tool selection happens through explicit capability exposure
- execution is routed through policy and validation layers

## Required components

### Tool definition

- unique name
- description
- input schema
- output shape
- risk level

### Tool registry

- capability lookup
- filtered exposure per run or mode
- schema retrieval for prompt construction

### Policy layer

- permission checks before execution
- path and command validation
- allow/deny rules per tool or risk level

### Execution wrapper

- structured result
- error normalization
- timing and trace capture

## Phase 1 tools

1. read
2. write
3. search

These are enough to validate the harness architecture without premature expansion.

## Security principles

- tools are not plain wrappers
- dangerous operations must be mediated by a policy engine
- command execution, if later added, must use explicit safety checks and provider-independent rules

## Portability principle

Tool logic belongs to HARDNESS. The model only requests tool use through a provider-neutral schema.
