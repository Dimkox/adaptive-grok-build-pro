# Rollback plan — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

## Trigger conditions

Use rollback if review rejects the boundary, a future change needs to undo the
wording, or the successor PR is abandoned.

## Application rollback

Revert the bounded changes to `tests/test_structure.py`, `trust-ci/README.md`,
`trust-ci/config/policy.example.json`, and
`engineering/runbooks/l5-runtime-observation-2026-09-15.md`, plus their package
evidence. Alternatively revert the whole candidate commit range, which restores
the pre-change authority and runtime-evidence wording together.

## Data recovery / forward-fix

No runtime, database, provider, key, holdout, or deployment recovery is
needed: this slice performs none of those operations. A forward fix is a new
source change with fresh verification and review receipts.

## Verification after rollback

Run the focused structure/policy tests and the exact PR verifier again; old
receipts are stale after the revert.
