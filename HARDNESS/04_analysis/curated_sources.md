# Curated Sources

## Reference implementations

### Python

- Repository: `https://github.com/instructkr/claw-code`
- Local archive: `HARDNESS/02_reference_impl/claw-code`
- Why kept:
  - Python-first workspace is easier to inspect quickly
  - repository layout is compact and readable
  - useful as a transfer-oriented clean-room implementation reference

### Rust

- Repository: `https://github.com/Kuberwastaken/claurst`
- Local archive: `HARDNESS/02_reference_impl/claurst`
- Why kept:
  - more rigorous architecture decomposition
  - useful for studying coordinator, memory, and tool boundary design
  - helpful as a production-shape reference, even if not adopted literally

## Prompt source

- Public prompt reference:
  - `https://github.com/asgeirtj/system_prompts_leaks/blob/main/Anthropic/claude-code.md`
- Use:
  - study instruction hierarchy
  - identify behavior constraints worth abstracting
  - avoid copying provider-coupled wording into HARDNESS core

## Curated analysis sources

1. `claurst` README
2. Kuber Studio blog post
3. Alex Kim analysis
4. Sebastian Raschka analysis
5. `ccunpacked.dev` visual reference

## Early observations from archived references

### From `README.md` in `claw-code`

- the Python port is currently a focused workspace rather than a full runtime clone
- the active Python files emphasize manifesting, models, commands, tools, and query summarization
- this makes it useful for extracting abstractions, but not sufficient as a drop-in runtime model

### From `claurst` indexed materials

- coordinator mode is explicitly modeled as orchestrator logic with internal-only coordination tools
- memory is treated as a file-based multi-layer system with selective loading and freshness caveats
- tool registration is filtered by gates, permissions, and context
- the architecture separates core, tools, query, commands, api, tui, and mcp concerns cleanly

## Selection rule

If a source does not improve one of these four dimensions, it should not enter the archive:

1. memory design
2. agent loop design
3. tool-runtime discipline
4. context management
