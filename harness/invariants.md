# Invariants

Non-negotiable rules for the harness and generated changes.

## Required Invariants
1. All changes map to an explicit spec requirement or issue task.
2. New/modified code must pass relevant tests before merge.
3. Do not edit files outside the repository root.
4. Keep edits minimal and avoid unrelated refactors.
5. Preserve deterministic behavior for tooling and scripts.
6. Update harness docs when behavior or workflow changes.
7. All functions > 100 LOC must be split or justified in comment.

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
