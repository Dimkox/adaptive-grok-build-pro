# Test review — bounded workspace process cleanup

**Route:** `fa3ae6080deb`
**Reviewed verification fingerprint:** `7b768fbef0db4c1cfe7a9603349a6e71cdc60907c96d2f0f7b2ba3f6584e93b6`
**Verdict:** **FAIL**

## Blocking finding

### TR-001 — The new procfs classifier is not exercised by its tests

The acceptance contract requires positive zombie-only proof and fail-closed handling for live, unknown, malformed, inaccessible, unavailable, over-limit, and deadline-expired observations. The added end-to-end error-preservation tests patch `_classify_post_kill_process_group()` to return `zombie_only`, `live`, or `unknown`; therefore they verify only `_terminate_process()` dispatch for already-classified values and cannot detect a parser, membership, state, bound, or deadline defect in the new implementation.

The sole direct classifier test covers only `os.scandir('/proc')` raising `OSError`. Instrumented execution of the complete focused suite confirms that the substantive classifier body is unexecuted:

```text
COVERAGE_FILE=/tmp/fa3ae6-test-review.coverage \
PYTHONPATH=trust-ci/src coverage run --branch \
  --source=adaptive_trust_ci.workspace \
  -m unittest trust-ci.tests.test_workspace -q

Ran 19 tests in 3.091s
OK

workspace.py: 69%; missing 113-149, 152-157 (among unrelated lines)
```

The same result occurs in the exact immutable runner image: lines `113-149` remain unexecuted. Consequently, the tests do not directly prove:

- a parsed all-`Z` target PGID returns `zombie_only`;
- any non-`Z` target member returns `live`;
- a malformed/truncated/oversized stat record returns `unknown`;
- stat open/read failure returns `unknown`, while a vanished PID is tolerated;
- the numeric-entry ceiling returns `unknown`;
- a deadline reached during enumeration or after a stat read returns `unknown`;
- no matching member is accepted as `absent` only after the final group-existence probe proves absence.

Add deterministic direct unit tests around fake `scandir` entries and mocked `open/read/close`, plus explicit deadline/entry-limit cases. Retain at least one real process-group test in the exact runner. Do not satisfy this finding only by increasing aggregate coverage; assert each security-relevant classification result.

## Evidence that is adequate

- The real SIGTERM-ignoring descendant regression still covers stdout overflow, stderr overflow, and timeout, and asserts that no live descendant remains. Cleanup in `finally` prevents a live probe from leaking after a failed assertion.
- The dispatch-level tests prove that `zombie_only` preserves each original stdout/stderr/timeout `WorkspaceError`, while preclassified `live` and `unknown` values produce `bounded process group survived SIGKILL`.
- Exact runner execution passed under the pinned image `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`, UID/GID `10001:10001`, read-only root/source, `network=none`, and tmpfs `/tmp`:

```text
Ran 19 tests in 6.190s
OK
```

- The route verification receipt is passing on the reviewed fingerprint: 404 root tests passed; architecture, spec, static analysis, contracts, and coverage gates passed. This broad success does not close TR-001 because root coverage does not measure `trust-ci/src`.

## Receipt-test stabilization assessment

Removing the branch-global `result.status == 'pass'` assertion from `test_pre_adoption_route_base_uses_one_architecture_comparison_base` makes the test stable on a later stacked worktree whose unrelated cumulative diff legitimately fails the historical architecture comparison. The remaining assertions still bind adoption base, route base, base kind, bootstrap state, fingerprint, and evidence consistently, matching AC-003; the active-route architecture gate independently passes against `9493741…`.

This stabilization is acceptable for the stated binding-only criterion, although the test no longer proves that the historical checker result itself passes. That behavior should remain covered by isolated architecture-verification tests rather than by a test coupled to the repository's current dirty stacked tree.

## Required re-review

Return the finding to the same `general_implementer`. After direct classifier regressions are added, rerun the focused suite in the exact pinned runner, the route verifier on the new fingerprint, and this independent test review. No `test_review` pass receipt should be recorded for the current tree.
