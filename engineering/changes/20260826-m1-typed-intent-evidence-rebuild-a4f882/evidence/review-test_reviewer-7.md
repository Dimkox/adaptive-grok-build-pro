# Test re-review 7 — M1 atomic workspace-allocation remediation

## Verdict

**PASS**

Reviewed exact repository HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a` against prior blocked HEAD `9a6e27c193ec944a149e452ff7591fbc7493238c`, original review base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`, remediation-6, and the active M1 package. The worktree was clean at review start. Concurrent route reviewers later wrote only untracked review reports; no product file changed during this review.

No P0, P1, or P2 test finding remains. The partial-construction resource leak from TEST-R6-001 is repaired and protected by failure-injection regressions. This exact HEAD is suitable for a passing local `test_review` receipt, subject to the repository's independent external merge gates.

## TEST-R6-001 closure

`GitWorkspace.__init__()` now treats checkout and trusted-config allocation as one guarded transaction. Both local path references start as `None`; every successfully allocated directory is removed on any later exception; and public object attributes are assigned only after allocation, permission setup, and XDG-directory creation complete.

The committed regressions cover every post-allocation failure boundary:

- checkout `chmod()` failure after checkout allocation;
- second/config-home `mkdtemp()` failure after checkout setup;
- config-home `chmod()` failure after both allocations;
- XDG `mkdir()` failure after both allocations and permission changes.

Each regression preserves the injected exception identity and asserts that the enclosing workspace base is empty afterward. A first-checkout `mkdtemp()` exception cannot leave a returned allocation for this constructor to clean; the four tests cover every phase after a path has actually been returned. A separate successful-path regression constructs the normal two directories, invokes `cleanup()` twice, and asserts that the base remains empty, preserving normal behavior and idempotency.

An independent fault-injection probe reproduced all four committed boundaries outside their test oracle. The observed leftovers were `[]` for checkout-chmod, config-mkdtemp, config-chmod, and XDG-mkdir failures. The normal probe observed the expected checkout and config-home allocations before cleanup and `[]` after two cleanup calls.

## Compatibility and retained regression coverage

The full focused workspace suite still exercises the prior process-group and Git-configuration remediations alongside the new lifecycle cases:

- overflow and timeout paths remove resistant same-group descendants and their original process groups;
- a committed hostile `.gitconfig` does not execute repository-controlled fsmonitor, hook, or external-diff commands;
- bounded streaming, hostile paths, surrogate-containing output, and normal cleanup continue to pass.

The new allocation transaction does not change the successful workspace interface or cleanup contract. The focused suite passed all 15 tests.

## Independent exact-HEAD evidence

- Initial identity: `git rev-parse HEAD` -> `98649e4e1e6a971fb802bc934eb5680de529e18a`; initial `git status --short` was empty.
- `PYTHONPATH=../src:. /tmp/adaptive-grok-m1-venv-20260826/bin/python -m unittest -v test_workspace`: PASS, 15/15.
- Independent four-boundary constructor fault-injection probe: PASS; every failure left `[]` entries in its isolated base and re-raised the injected exception.
- Independent normal lifecycle probe: PASS; the expected two allocations were present before cleanup and the base was empty after two cleanup calls.
- Default Trust CI discovery, first run: PASS, 200 total, 190 executed successfully, 10 conditional PostgreSQL skips.
- Default Trust CI discovery, immediate second run: PASS, 200 total, 190 executed successfully, 10 conditional PostgreSQL skips.
- Holdout identity before and after both default runs: digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64`; complete regular-file set exactly `change_spec_validate.py`, `validate.py`.
- Full root discovery: PASS, 223/223.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`: PASS.
- `git diff --check 0a4dd0a..HEAD`: PASS.
- `python3 scripts/grok_verify.py --mode pr --no-record --json`: PASS at Git HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a`; active spec valid with 6/6 criteria mapped; fingerprint `a7a0bd4b2d1c14ac56c11c6119dfb1589411da4e0c3917002ef863b889de484e`. Concurrent untracked code/security review reports were present by this preflight, so this fingerprint is not represented as a clean-HEAD-only tree fingerprint.

The 10 PostgreSQL integration tests were skipped because `TRUST_CI_TEST_DATABASE_URL` is not configured; this report does not claim executed database evidence. All local evidence remains advisory and does not replace the App-owned policy-epoch check, branch protection, or required external approvals on the exact pull-request head.

## Conclusion

The previously leaking constructor paths are now atomic from the caller's perspective, are covered at every relevant failure boundary, and leave no temporary directories. Successful construction and repeated cleanup remain idempotent. Focused and full exact-HEAD suites pass, and two default full-suite runs leave the holdout file set and digest unchanged. Test review therefore passes for exact HEAD `98649e4e1e6a971fb802bc934eb5680de529e18a`.
