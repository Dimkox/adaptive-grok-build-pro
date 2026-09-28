# Independent code review — startup resource policy

Verdict: **FAIL**
Reviewer role: route-selected `code_reviewer` (read-only)
Route: `bd1cb67aa011`
Base: `33a4d3ecb73d81dbdd48195c2681813105159b5a`
Candidate HEAD before/after: `554a29d6396555ebd4961508eca86917126ce4f1`
Candidate Git tree before/after: `58c9c727ef3d38d1e022b1442e7d82a6586f9005`
reviewed-tree-modified: no
Scratch: `/tmp/adaptive-resource-code-review.2yKYwA/repo` (parent mode 0700), exact HEAD/tree reproduced.

## Finding

1. **Material — new startup prose and typed AC misstate the closed selector inventory.** `AGENTS.md:21`, `START_HERE.md:19`, `README.md:9`, and `change-spec.yaml:4` state that only documentation/state inventory is admitted and executable changes retain full scope. The actual merged selector also admits tracked `packages/**` release bytes and the five executable binding test modules (`tests/test_structure.py`, `test_project_state.py`, `test_manifest_package.py`, `test_workflow_sources.py`, `test_repo_router.py`). Probe results: `tests/test_structure.py` and `packages/v2.0.19/example.zip` => `docs-state-focused`, `eligible`, with the three focused skips; `factory/runtime.py`, `engineering/contracts/openapi/example.yaml`, and `.grok-stack/adaptive_grok/verification_scope.py` => `full-pr-suite`; deleted `README.md` => full/unsafe status. This contradicts AC-002 and may send selector-admitted package/test successors into unnecessary full/PostgreSQL work. Correct all four statements to enumerate named docs/state + tracked package bytes + five admitted binding modules, and say *all other* executable/non-admitted paths retain full scope.

## Checks

- `git diff --check 33a4d3ec...HEAD`: PASS.
- Scratch `taskset -c 0-27 env GROK_TEST_WORKERS=8 PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_verify.py --mode pr`: PASS, `docs-state-focused`, 16/16 paths; skips exactly `python-unittest`, `coverage`, `factory-postgres-exit`; factory-unit retained.
- Mutation/inventory probe above: fail-closed mutants killed for factory, contract, selector, and deletion; admitted test/package cases survived as designed and expose the prose defect.
- Capacity recheck: 28 online logical / 14 physical cores, default `nproc=22`, affinity `0,1,8-27`, effective cpuset `0-27`, no finite observed cgroup quota, child probe returned 28. Dated/nonportable wording is correct.
- VERSION `2.0.19` matches README; required architecture model/rules/generated links exist. One writer per isolated contour, UNVERIFIED pre-verification transport, PR-only delivery and exact-head App Trust CI/approval boundaries are consistent. No manual PostgreSQL exemption found.
- Mistake entry states the relevant boundary/root cause (generalizing Git-bound reuse outside the selector) and the correction; event history itself is not independently reproducible from repository state.

## Limitations/unexecuted

- Historical 629 s vs ~14 s timings were not rebenchmarked; wording correctly labels them historical and non-promissory.
- External Trust CI, approvals, push/PR/merge were not executed.
- Initial scratch run without `active-change.json` was inconclusive at typed-spec; rerun with the candidate's non-secret active route/change pointers produced the PASS above.
- A verifier accidentally started in the candidate cwd was interrupted during Bandit before receipt recording; final HEAD/tree/status and pre-existing receipt mtime remained unchanged.
