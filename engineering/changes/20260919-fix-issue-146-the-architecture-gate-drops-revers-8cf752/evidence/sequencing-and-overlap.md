# Sequencing and concurrent-wave note (measured 2026-09-19)

## File overlap with other open pull requests

`gh pr list --state open` plus per-PR `--name-only` diff listings, checked against this change's write set
(`.grok-stack/adaptive_grok/architecture.py`, `.grok-stack/adaptive_grok/architecture_fitness.py`,
`tests/test_architecture_fitness.py`):

| PR | issue | overlapping files | gate on its head |
|---|---|---|---|
| #137 | #120 semantic schema metadata | `architecture.py`, `tests/test_architecture_fitness.py` | SUCCESS (pre-#133 base) |
| #138 | #121 durable activation probe | `tests/test_architecture_fitness.py`, adds `factory/contracts/openapi/landing-probe.v1.json` | SUCCESS (pre-#133 base) |
| this | #146 | `architecture.py`, `architecture_fitness.py`, `tests/test_architecture_fitness.py` | — |

Three waves therefore converge on `tests/test_architecture_fitness.py`. Discipline for this change:

- append a new `TestCase` class with #146-specific names; do not edit or reorder existing methods, so a rebase over
  #137/#138 stays textual and conflict-free;
- keep the `architecture.py` edit to *exposing* the shared reference grammar (no verdict logic), so it cannot collide
  semantically with #137's metadata comparison inside `_compare_schema_direction`;
- if #138 lands first, its new contract joins the declared inventory and the #146 blast-radius table must be
  re-derived before the gate run is trusted (that file is the checklist, not this note).

## Cost already paid by merging #133

Branch protection is `strict: true` with the single required context
`adaptive-trust-ci/verified@06ecf1c875bc` (app 4694114). Twelve open PRs held SUCCESS on heads based on
`2f66ba6`; after `#133` merged as `d871ea6` they must update to the new base and be re-checked on the new head SHA.
That is inherent to a shared `main` and to any merge, including a decision to wait — the queue does not shrink by
holding a green pull request. Recorded so no one reads it as an avoidable mistake of the merge itself.

## What this changes for review

Reviewers of the #146 pull request should expect, and must not treat as a defect, that:

1. a re-check on the rebased head is required (fresh exact-SHA check by contract), and
2. the local `factory-postgres-exit` tier may fail for the host-contention reason already tracked by #128/#143
   rather than for anything in this diff — re-measure in an isolated private clone before attributing any red.
