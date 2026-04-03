# HARDNESS Validation Round 1

## Scope

First real-provider validation after hardening the v1 loop.

Targets selected:

- OpenRouter + `minimax/minimax-m2.7`
- Groq + `llama-3.3-70b-versatile`

Rationale is aligned with [`docs/cost_optimized_routing.md`](docs/cost_optimized_routing.md):

- low-cost workhorse baseline first
- premium references deferred

## Pre-validation hardening completed

Before running real providers, HARDNESS was updated with:

- structured trace and metrics in [`AgentLoop.run()`](src/hardness/agent.py:31)
- routing layer in [`ModelRouter`](src/hardness/router.py:9)
- stronger response/tool schemas in [`ToolDefinition`](src/hardness/types.py:44) and [`OpenAICompatibleAdapter.generate()`](src/hardness/providers.py:38)
- stronger tool guardrails in [`PolicyEngine`](src/hardness/policy.py:12) and [`ReadTool`](src/hardness/tools.py:22) / [`WriteTool`](src/hardness/tools.py:45) / [`SearchTool`](src/hardness/tools.py:72)
- stop conditions and repeated-action detection in [`AgentLoop.run()`](src/hardness/agent.py:31)
- task suite in [`HARDNESS/05_synthesis/task_suite.json`](HARDNESS/05_synthesis/task_suite.json)

## Automated verification status

Local verification passed:

- `python -m unittest discover -s tests -v`
- result: 11 tests passed

Coverage includes:

- mock harness behavior
- provider builder support
- API file parsing
- repeated-action stop condition
- tool guardrails
- task suite integrity

## Real-provider results

### 1. OpenRouter + `minimax/minimax-m2.7`

Command succeeded at transport level.

Observed result:

- status: success
- task: `read README.md`
- turns: 3
- tool calls: 2
- repeated actions: 1
- final behavior: model repeated the same `read` action instead of converging cleanly after the first successful read

Interpretation:

- provider integration works
- tool calling works
- current loop still allows redundant tool reuse before termination
- this is not a transport failure; it is a convergence-quality issue

What this reveals:

- HARDNESS needs a stronger post-tool continuation policy
- after a successful low-risk read, the next turn should bias toward synthesis rather than blindly re-offering the same action space
- repeated-action handling exists, but current thresholds allowed one redundant cycle before stop

### 2. Groq + `llama-3.3-70b-versatile`

Command failed at provider/API level.

Observed result:

- status: error
- error: `error code: 1010`
- turns: 1
- parse failures: 1

Interpretation:

- transport request reached the provider stack
- current adapter is not yet robust enough to normalize or diagnose this Groq failure path cleanly
- the issue may be model capability mismatch, request-shape incompatibility, or provider-side rejection behavior

What this reveals:

- HARDNESS needs provider-specific diagnostics without breaking provider-agnostic core design
- response and error normalization in [`OpenAICompatibleAdapter`](src/hardness/providers.py:35) should be extended
- Groq validation should include a dedicated compatibility probe before full task execution

## Failure modes discovered

### A. Redundant tool reuse after success

Observed on OpenRouter.

Cause class:

- loop policy weakness, not provider transport failure

Required fix direction:

- add stronger no-progress detection
- detect success-with-sufficient-evidence and force summarize/finalize mode
- optionally reduce available tools on subsequent turns when the objective is already satisfied

### B. Weak provider-specific diagnostics

Observed on Groq.

Cause class:

- adapter normalization gap

Required fix direction:

- preserve raw provider error body in trace
- classify error type: auth, unsupported model, malformed tools, rate limit, provider internal
- add provider capability probes per backend

## Strategic conclusion

Round 1 validates the architecture, not yet the full execution quality.

What is validated:

- provider-agnostic core loop structure is real
- routing layer is in place
- low-cost provider testing is possible
- tracing and metrics are sufficient to expose actual failure modes

What is not yet validated:

- reliable convergence after successful tool use
- cross-provider parity of tool-call behavior
- stable Groq compatibility

## Recommended next step

Priority order:

1. strengthen post-tool convergence logic in [`AgentLoop.run()`](src/hardness/agent.py:31)
2. improve provider diagnostics in [`OpenAICompatibleAdapter.generate()`](src/hardness/providers.py:38)
3. add provider capability probe command before task execution
4. rerun the same baseline on OpenRouter and Groq
5. only after that, introduce premium reference validation with Claude Sonnet 4.6

## Round 1 verdict

HARDNESS is no longer a toy skeleton.
It is now a measurable harness with real failure visibility.
The next engineering step is not adding features, but improving convergence and provider robustness.
