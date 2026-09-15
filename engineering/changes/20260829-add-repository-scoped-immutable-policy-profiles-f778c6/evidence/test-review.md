# Test review — repository-scoped immutable policy profiles

- Base: `1c06299894279a88b881defa3f19b004fa742223`
- Head: `3db32de705a0cd084d3c7d967b4ff927f2b436de`
- Verdict: **PASS**
- Scope: exact base..HEAD; test quality and regression evidence only. No code fixes.

## Verified coverage

- `trust-ci/tests/test_runner.py` reaches the executor for two catalog profiles and checks distinct command lists, local holdout paths, host mount paths, epoch check names, and attestation policy digests.
- `trust-ci/tests/test_worker.py` checks bound-profile dispatch, stale binding without runner construction, paired local/host descendants, filesystem-root rejection, parent traversal, and an outside host root.
- `trust-ci/tests/test_api.py` covers catalog enqueue binding, case-sensitive repository rejection, valid catalog approval/requeue, changed-digest distinct jobs, and catalog closed-event isolation.
- `trust-ci/tests/test_policy.py` covers profile digest scoping/order independence, duplicate/wildcard rejection, canonical path digest behavior, and preservation of the legacy digest/check name.
- The implementation agent reported `167 passed, 8 skipped`, spec validation passed, `git diff --check` passed, and `grok_verify --mode pr` passed. These reports are not substitutes for the missing cases below.

## Execution evidence

Command run:

```text
python3 -m unittest discover -s trust-ci/tests -q
```

Result: **PASS**. The configured verification environment ran the full suite: `PASS python-unittest`, `PASS coverage`, with all other checks passing (`git-diff-check`, `secret-scan`, `contract-structure`, `sql-safety`, `ruff`, `bandit`). Final result: `PASS | profiles=base,contracts | changed=45`.

## Conclusion

The exact file at `3db32de…`, especially lines 335–399, contains the requested replay-preservation assertions: no re-execution, old head SHA, old check name, old external ID, and old attestation digest. Together with the two-profile runner boundary, trusted-root matrix, valid/stale/removed approval cases, changed-digest distinct-job case, catalog closed-event isolation, legacy digest coverage, and repository verification PASS, the route-selected test review is **PASS** for head `3db32de705a0cd084d3c7d967b4ff927f2b436de`.
