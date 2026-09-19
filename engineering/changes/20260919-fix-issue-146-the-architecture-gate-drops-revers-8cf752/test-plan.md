# Test plan — issue #146 contract-closure reverse edges

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | `$id`-referenced dependent is re-verified when its target changes (AC-001); fragment-referenced dependent likewise (AC-002); plain-relative control still works (AC-003) | `tests/test_architecture_fitness.py` closure arms — names recorded in `change-spec.yaml` after implementation |
| P0 | Comparator semantics frozen: identical status/reason tuples for a verdictable pair before and after (AC-006) | existing `test_architecture_fitness`/`test_architecture_model` suites plus the helper-level arm |
| P0 | Mutation proof: neutralising the shared grammar helper (return only plain-relative paths) must FAIL the new arms; the old suite must NOT catch it, which is the statement of the bug | mutation run in a throwaway clone, results in `evidence/` |
| P1 | Dangling `$id`/path reference creates no edge and raises nothing (AC-004) | new negative arm |
| P1 | Duplicate declared `$id` fails closed (AC-005) | new collision arm |
| P1 | End-to-end: a probe commit editing a real shipped target surfaces its dependent through the CLI path | `evidence/verification-arms.md` (`grok_architecture.py fitness --base … --head …`) |
| P2 | `$id` map build cost does not add a second document walk | read of the final code path in review |

## Automated checks

- Unit: `python3 -m unittest tests.test_architecture_fitness -q` (plus `tests.test_architecture_model`,
  `tests.test_governance_fitness` as neighbours of the touched module).
- Integration: `python3 scripts/grok_verify.py --mode pr` on the clean delivered head.
- Contract: no contract changes; the comparator's own contract rows are asserted unchanged (AC-006).
- E2E: fitness CLI arms A/B/C against a throwaway clone of the delivered head.
- Static analysis: `ruff check .grok-stack/adaptive_grok/ tests/`, `git diff --check`, bandit as run by the gate.

## Manual checks

- Re-read the 9 previously-lost edges from the issue and confirm each now yields an edge in the closure (the issue's
  table is the checklist).
- Confirm no `unsupported` row newly appears on an *unmodified* tree (the gate must stay green at base→base).

## Environment notes

- No `pytest` on this host and none in the gate runner image: tests must run under plain `unittest`.
- `GROK_VERIFY_CAPABILITY=repository-sandbox UV_LOCKED=1` for the local gate; `test_verification_doctor` needs a
  generous per-unit deadline. The disposable-PostgreSQL tier has a known host-contention failure class tracked by
  #128/#143 and must not be reported as a product defect without re-measuring.
