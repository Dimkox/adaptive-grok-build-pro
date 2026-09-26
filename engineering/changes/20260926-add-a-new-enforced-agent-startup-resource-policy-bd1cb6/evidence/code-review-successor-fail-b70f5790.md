# Independent successor code review — startup resource policy

Verdict: **FAIL**
Reviewer role: route-selected `code_reviewer` (read-only)
Route: `bd1cb67aa011`
Base: `33a4d3ecb73d81dbdd48195c2681813105159b5a`
Candidate HEAD before/after: `b70f5790c42b3733638536ad0bfcdfee4618a177`
Candidate Git tree before/after: `8b28183df787ddac70ae3d37c2906c93f57ef6fe`
Candidate repository fingerprint before/after: `08cd2cd1414a71d7154169582b392aaf703dfde04a77ae298cab2820a8d23aa2`
reviewed-tree-modified: no
Scratch: `/tmp/adaptive-resource-successor-review.fkrnBV/repo` (parent mode 0700), exact HEAD/tree/fingerprint reproduced.

## Prior material finding

**Repaired.** `AGENTS.md:21`, `START_HERE.md:19`, `README.md:9`, and `change-spec.yaml:4` now enumerate named docs/state paths, tracked `packages/**` release bytes, and exactly the five selector constants: `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py`, `tests/test_workflow_sources.py`, and `tests/test_repo_router.py`. Each reserves full scope for every other executable/non-admitted/ambiguous inventory. No manual PostgreSQL exemption was introduced.

## Findings

1. **Material factual error — the durable jq mistake quotes the wrong failure.** `mistakes.md:1475` says the shown `select([...] | index(.number))` form failed with `expected an object but got: array`. On the repository host's jq 1.7, the exact bad expression exits 5 with `jq: error (at <unknown>): Cannot index array with string "number"`. The documented dot-context root cause and `.number as $n` repair are correct, and the corrected fixture exits 0 with `[157,228]`, but the quoted symptom is not factual. Replace the quote with the observed error, or describe it without claiming an exact error string.

2. **Minor package staleness — the current handoff still describes steps already completed.** `tasks.md` says the current action is to commit the repair and run its exact-tree verifier, while HEAD is already repair commit `b70f5790…` and the runtime receipt records PASS at `2026-09-26T01:45:17+00:00` with fingerprint `08cd2cd…`. `state.json` likewise describes the repaired receipt as still needing refresh before this re-review. This is conservative and grants no false merge authority, but it is not an exact current handoff. Update it when persisting this review: identify the current receipt as pre-review evidence that will become stale when the report is added, then require the final post-report verifier.

## Bounded checks

- Four exact selector unit tests: PASS, 4 tests in 0.014 s.
- Four wording blocks: PASS; `packages/**` and all five binding modules present.
- Direct selector probes: all five binding modules and `packages/v2.0.19/example.zip` selected `docs-state-focused` with skips `python-unittest,coverage,factory-postgres-exit`; factory runtime, OpenAPI contract, selector source, non-binding test and deleted README all selected full scope.
- `git diff --check 33a4d3ec...HEAD`: PASS.
- Preserved historical FAIL report SHA-256: PASS, `a77338963c5b4789f57442a4b3e714bfde343f990d39115cb98094458ed83a6a`.
- Existing exact-successor runtime receipt (read-only inspection): PASS at fingerprint `08cd2cd…`, 18-path `docs-state-focused`; this review did not reuse it as approval or rerun the full verifier.
- jq bad fixture: killed with exit 5 and the actual message above. Corrected bound-variable fixture: PASS, exit 0, `[157,228]`.

## Limitations / unexecuted

- Full verification was not rerun; the task requested bounded selector probes and no candidate writes.
- Historical timing measurements were not rebenchmarked.
- External Trust CI, approvals, push, PR, merge, and any external action were not executed.
