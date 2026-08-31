# Bounded workspace process cleanup — RED/GREEN

## Root cause

`killpg(pgid, 0)` reports a zombie-only process group as extant. After the correct TERM/KILL sequence, the old post-KILL wait therefore raised `bounded process group survived SIGKILL` and masked the already-classified stdout-limit, stderr-limit, or timeout failure.

## RED

```text
PYTHONPATH=trust-ci/src python3 -m unittest \
  trust-ci.tests.test_workspace.WorkspaceStreamingTests.test_bounded_process_preserves_every_original_error_for_zombie_only_group \
  trust-ci.tests.test_workspace.WorkspaceStreamingTests.test_bounded_process_fails_closed_for_live_post_kill_group \
  trust-ci.tests.test_workspace.WorkspaceStreamingTests.test_bounded_process_fails_closed_for_uncertain_post_kill_group -v

FAIL (3): expected stdout/stderr/timeout; got bounded process group survived SIGKILL
```

The live and uncertain tests were already green on the old implementation, confirming that the regression is narrowly error masking rather than missing fail-closed behavior.

## GREEN

```text
PYTHONPATH=.grok-stack:trust-ci/src python3 -m unittest trust-ci.tests.test_workspace -q

Ran 19 tests in 3.049s
OK
```

```text
digest-pinned read-only runner, UID/GID 10001, network none, read-only source/root,
tmpfs /tmp:

PYTHONPATH=/workspace/.grok-stack:/workspace/trust-ci/src \
  python3 -m unittest trust-ci.tests.test_workspace -q

Ran 19 tests in 3.342s
OK
```

```text
RUFF_CACHE_DIR=/tmp/ruff-cache ruff check trust-ci/src/adaptive_trust_ci/workspace.py trust-ci/tests/test_workspace.py
All checks passed!

python3 scripts/grok_spec.py validate engineering/changes/20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6/change-spec.yaml --gate
ok: true

git diff --check
clean
```

## Implementation and residual risk

`workspace.py` preserves the existing new-session/PGID, TERM, bounded TERM grace, KILL, bounded KILL grace, and direct-leader reap flow. In the final portion of KILL grace it performs one bounded, read-only `/proc` scan: every matching member must be positively parsed as `Z`; a live state, unreadable/malformed/over-limit observation, unsupported procfs, deadline expiry, or incomplete evidence is fail-closed.

The static root receipt regression for the older frozen pre-adoption base is not a valid hotfix verification target while this Trust-CI-only worktree is dirty: it deliberately compares the entire worktree against that historical base and reports the old M2 implementation diff mixed with `trust-ci/**`. The active route base is the stacked M2 head `9493741…`, where this hotfix is isolated. No architecture authority was changed to suppress that policy.

The receipt regression was therefore stabilized narrowly: its former branch-global `result.status == 'pass'` assertion was RED for every legitimate later Trust-CI-only stacked worktree, while its actual base/binding/evidence assertions remained meaningful. The test now passes in the dirty hotfix worktree and in a fresh local clone of `9493741…` with this exact diff applied; the active route's architecture gate independently remains `pass` against route base `9493741…`.

## Committed-head ROOT regression rationale

At committed head `6a2ccca`, two ROOT tests were RED solely because they compared the entire later stacked Trust-CI-only worktree to the frozen pre-adoption base: `test_all_mandatory_categories_emit_typed_applicability` asserted global `change_separation` and report pass states, and `test_route_base_remains_a_separate_architecture_staleness_binding` asserted `_architecture_check` pass. Their actual contracts are typed category/applicability evidence and exact comparison/route-base receipt binding, respectively. The remediation retains those direct assertions and removes only the branch-global fitness-pass assumptions; it does not alter architecture fitness policy or the active-route gate.

Rollback is a one-file forward-fix/revert of the classifier with its focused tests; never replace uncertain state with cleanup success or omit TERM/KILL/reap.

## TR-001 direct-classifier remediation

The retained prior test review is superseded as evidence for its older fingerprint, not edited. Its RED result was that the full 19-test suite left classifier body lines 113–149 unexecuted because integration tests mocked the classifier result. [`test-review-remediation.md`](test-review-remediation.md) records the deterministic mocked-procfs characterization tests, current 28-test coverage run, and 28-test digest-pinned runner result; a fresh independent review remains required on the new fingerprint.
