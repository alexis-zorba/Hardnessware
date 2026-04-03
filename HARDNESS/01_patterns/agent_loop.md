# Agent Loop Pattern

## Goal

Transform a raw chat completion into a controlled execution loop.

## Canonical loop

1. think
2. act
3. verify
4. update

This is preferable to a single request-response pattern because it introduces explicit checkpoints around state and tool usage.

## Recommended HARDNESS loop

### Think

- interpret user intent
- inspect available context and memory
- produce a bounded plan

### Act

- invoke one or more tools through the registry
- capture structured outputs
- preserve execution metadata

### Verify

- check whether tool results support the intended claim or change
- detect mismatch, partial success, or contradiction
- retry only with a reasoned change in approach

### Update

- persist run state
- store useful durable notes only after verification
- emit trace events for observability

## Error recovery

### Retry discipline

- bounded retries only
- backoff on transient failures
- no blind repetition of the same failing action

### Self-correction

- when a tool result contradicts the plan, revise the plan explicitly
- prefer smaller next actions after failure

### Stop conditions

- objective achieved
- permission denied and non-bypassable
- repeated failure threshold reached
- missing required information

## HARDNESS decision

Phase 1 should implement a single orchestrating loop, not multi-agent delegation.

The loop must be provider-agnostic and should depend only on:

- provider adapter
- tool registry
- policy engine
- memory manager
- state store
