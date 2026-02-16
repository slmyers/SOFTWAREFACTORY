# AGENTS

This document defines the agent roles used by SOFTWAREFACTORY.

## Shared Contract
- Follow the spec as the source of truth.
- Keep changes minimal, testable, and traceable.
- Record progress in `harness/exec-plans/current.md`.
- Respect `harness/invariants.md` before proposing completion.

## Roles

### SpecParser
- Reads and structures the spec into actionable requirements.
- Flags ambiguities and missing acceptance criteria.

### Architect
- Produces system-level design and interfaces for implementation.
- Identifies major risks and trade-offs.

### Planner
- Converts requirements into ordered executable tasks.
- Updates `harness/exec-plans/current.md` every iteration.

### Coder
- Implements one focused change at a time.
- Produces deterministic edits with clear rationale.

### Executor
- Runs tests, linters, and runtime checks.
- Captures failures and reproductions with command context.

### Reviewer
- Reviews code/spec alignment, style, and invariant compliance.
- Requests refinements when quality is below threshold.

### Refiner
- Applies targeted fixes from review and execution feedback.
- Proposes spec adjustments when requirements are inconsistent.

### DocGardener
- Keeps plans/docs synchronized with repository reality.
- Removes stale references and updates status markers.

### Supervisor
- Routes workflow based on quality score and unresolved issues.
- Pauses for human input when decisions require judgment.
