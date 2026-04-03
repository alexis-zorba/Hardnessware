# Context Management Pattern

## Goal

Preserve high-value context while avoiding entropy and token waste.

## Core principles

### Static versus dynamic boundary

- static content changes rarely:
  - system rules
  - tool schemas
  - stable project instructions
- dynamic content changes every turn:
  - user request
  - live repo state
  - retrieved notes
  - current tool results

HARDNESS should keep these layers separate so that caching and selective refresh remain possible.

### Live repository context

- current repository state should be refreshed when relevant
- examples:
  - file changes
  - active task state
  - project instructions

### Entropy control

- repeated paraphrasing and unbounded transcript injection degrade quality
- summarize aggressively, preserve evidence separately, and reload only when needed

### Prompt cache awareness

- stable sections should remain stable in order and content
- dynamic sections should be isolated to reduce churn

## HARDNESS implementation guidance

- separate prompt assembly into static, semi-static, and dynamic builders
- keep durable memory out of the active context unless selected
- persist evidence outside the active prompt path
- add compaction hooks later, but keep interfaces ready now

## Phase 1 decision

Include:

- static/dynamic prompt boundary
- live state injection hooks
- memory retrieval budget
- structured trace of what entered context

Exclude:

- advanced prompt cache optimizers tightly coupled to a single provider
