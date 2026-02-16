"""Harness scaffolding bootstrap for first-run initialization.

Creates required templates for Issue #4 if missing.
This function is intentionally idempotent and never overwrites existing files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _templates() -> Dict[str, str]:
    return {
        "docs/AGENTS.md": """# AGENTS

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
""",
        "harness/quality-score.md": """# Quality Score

Tracks quality for the current run and decision routing.

## Current Snapshot
- Overall score: 0/100
- Iteration: 0
- Decision: continue
- Last updated: TBD

## Rubric
- Spec alignment: 0-30
- Correctness/tests: 0-30
- Invariant compliance: 0-20
- Code quality/readability: 0-10
- Documentation hygiene: 0-10

## Evidence
- Commands run:
- Test summary:
- Lint summary:
- Reviewer notes:

## Iteration History
| Iteration | Score | Summary | Owner |
|---|---:|---|---|
| 0 | 0 | Template initialized | bootstrap |
""",
        "harness/invariants.md": """# Invariants

Non-negotiable rules for the harness and generated changes.

## Required Invariants
1. All changes map to an explicit spec requirement or issue task.
2. New/modified code must pass relevant tests before merge.
3. Do not edit files outside the repository root.
4. Keep edits minimal and avoid unrelated refactors.
5. Preserve deterministic behavior for tooling and scripts.
6. Update harness docs when behavior or workflow changes.

## Validation Commands
- `pytest -q`
- `python -m compileall .`

## Severity
- Critical: violates safety, data integrity, or repository boundaries.
- Major: breaks tests/invariants or diverges from spec.
- Minor: style/docs mismatch that does not break behavior.

## Waiver Process
- Waivers require explicit human approval.
- Record waiver reason, scope, and expiration in this file.

## Active Waivers
- None
""",
        "harness/exec-plans/current.md": """# Execution Plan (Current)

## Objective
Bootstrap harness scaffolding templates for Issue #4.

## Tasks
- [x] Create `docs/AGENTS.md`
- [x] Create `harness/quality-score.md`
- [x] Create `harness/invariants.md`
- [x] Create `harness/exec-plans/current.md`
- [ ] Add first-run scaffolding generator hook

## Validation
- [ ] Run tests
- [ ] Confirm idempotent generation

## Notes
This file is updated by Planner/DocGardener during runs.
""",
    }


def ensure_harness_scaffolding(root: Path | None = None) -> List[Path]:
    """Create harness scaffolding files if missing.

    Args:
        root: Optional project root path. Defaults to repository root.

    Returns:
        List of created file paths.
    """
    base = root or _project_root()
    created: List[Path] = []

    (base / "harness" / "exec-plans").mkdir(parents=True, exist_ok=True)

    for rel_path, content in _templates().items():
        file_path = base / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.write_text(content)
            created.append(file_path)

    return created


def main() -> None:
    created = ensure_harness_scaffolding()
    if created:
        print(f"Created {len(created)} scaffold file(s):")
        for path in created:
            print(f"- {path.relative_to(_project_root())}")
    else:
        print("Harness scaffolding already present; nothing to do.")


if __name__ == "__main__":
    main()
