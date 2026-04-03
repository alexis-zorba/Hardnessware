# HARDNESS Cost-Optimized Routing Proposal

## Objective

Optimize [`HARDNESS`](README.md) for maximum quality per unit cost.

The core rule is:

- cheap model for most turns
- premium model only for high-ambiguity decisions
- specialist model only when its advantage is concrete

## Recommended routing stack

### Default executor

- **MiniMax M2.7**

Use for:

- ordinary read/search/write loops
- routine continuation turns
- low-ambiguity task execution
- state update turns

Why:

- much lower cost profile than frontier premium models
- suitable as the main workhorse for repeated agent turns

### Premium escalation

- **Claude Sonnet 4.6**

Use only for:

- initial planning on ambiguous tasks
- reflection after repeated failures
- memory promotion decisions when confidence matters
- delicate refactors or high-ambiguity multi-file reasoning

Why:

- high quality, but too expensive for continuous execution

### Tool-execution specialist

- **GPT-5.3 Codex**

Use only for:

- operational coding tasks
- strict tool/terminal chaining
- debugging and targeted fixes

Why:

- useful when execution discipline matters more than broad reasoning

### Long-context escalation

- **Gemini 3.1 Pro Preview**

Use only for:

- very large repository slices
- cross-file analysis over broad context
- cases where smaller active context repeatedly fragments the task

Why:

- context window is the primary benefit here, not default routing quality

## What not to do

Do not make premium models the default runtime.

Specifically avoid:

- Sonnet as the main executor
- Codex as a constant fallback
- broad multi-model rotation without strict triggers

That pattern raises cost before the core harness is even validated.

## Phase 2 routing policy for HARDNESS

### Router 1 — default

- MiniMax M2.7

Trigger:

- normal execution turns

### Router 2 — quality escalation

- Claude Sonnet 4.6

Trigger:

- repeated failure
- ambiguous intent
- planning complexity
- memory decision with high consequence

### Router 3 — tool specialist

- GPT-5.3 Codex

Trigger:

- coding-heavy execution
- tool chaining
- technical debugging

### Router 4 — big context

- Gemini 3.1 Pro Preview

Trigger:

- genuine need for extreme context breadth

## Architectural implication

The next HARDNESS iteration should not hardcode a single provider choice.
It should add a routing layer above [`ProviderAdapter`](src/hardness/providers.py:17) so model selection becomes policy-driven.

## Immediate implementation consequence

Before running costly real-provider validation, HARDNESS should be updated to support:

- named model profiles
- routing reasons recorded in trace events
- per-task metrics including latency, tool error rate, repeated-action rate, and stop reason
- provider/model selection separated from the core loop in [`AgentLoop.run()`](src/hardness/agent.py:30)
