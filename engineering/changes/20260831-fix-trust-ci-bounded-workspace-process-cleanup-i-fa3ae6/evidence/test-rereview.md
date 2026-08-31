# Test rereview — bounded workspace process cleanup

**Route:** `fa3ae6080deb`  
**Reviewed verification fingerprint:** `a9a4cc297ab7e84b301340aaf8bea48b1c6a92d8bb578e862d081370826a3da9`  
**Verdict:** **PASS**

This is the independent rereview after the prior fingerprint's blocking TR-001 finding. The old `test-review.md` remains an accurate FAIL record for that older tree; this report evaluates the remediated current tree.

## Findings

No blocking, important, or minor test findings remain.

## TR-001 closure

`PostKillProcessGroupClassifierTests` now invokes `_classify_post_kill_process_group()` directly with deterministic mocked procfs and monotonic-time inputs. The tests assert the security-relevant result rather than merely increasing aggregate coverage:

- all observed target-PGID `Z` members produce `zombie_only`;
- target-PGID `R`, `S`, and `X` members produce `live`;
- malformed, truncated, and oversized stat data produce `unknown`;
- stat-open and stat-read errors produce `unknown`, while a vanished PID is tolerated only if the final group probe proves absence;
- numeric-entry exhaustion and deadline exhaustion before/during inspection produce `unknown`;
- non-numeric proc entries are ignored;
- zero matching members produce `absent` only after `_process_group_exists()` proves absence; an extant or uninspectable final group remains `unknown`.

The existing dispatch tests remain complementary: a classified `zombie_only` result preserves each original stdout-limit, stderr-limit, and timeout `WorkspaceError`, while `live` and `unknown` replace the original error with the fail-closed cleanup error. The real SIGTERM-ignoring descendant regression still covers stdout, stderr, and timeout modes and asserts that no live same-group descendant remains.

## Independent commands and results

Focused suite plus source-targeted classifier coverage:

```text
COVERAGE_FILE=/tmp/fa3ae6-test-rereview.coverage \
PYTHONPATH=trust-ci/src coverage run --branch \
  --source=adaptive_trust_ci.workspace \
  -m unittest trust-ci.tests.test_workspace -q

Ran 28 tests in 3.195s
OK

workspace.py: 81%; classifier lines 105-157 executed except line 108,
the own-worker-PGID return guard.
```

The own-worker group invariant remains exercised at the signaling/inspection boundary by `test_process_group_cleanup_refuses_own_group_and_tolerates_esrch`; the unexecuted classifier guard is duplicate defense and not a coverage blocker.

Exact immutable runner execution used `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`, UID/GID `10001:10001`, read-only root/source, `network=none`, and tmpfs `/tmp`:

```text
Ran 28 tests in 6.187s
OK
```

The current route verification receipt is PASS on fingerprint `a9a4cc2…`: architecture drift/fitness/diagrams, spec, secrets, contracts, SQL safety, Ruff, Bandit, root unit tests, and root coverage all passed; the root suite ran 404 tests successfully.

## Receipt-test stabilization

The one-line removal of the branch-global `result.status == 'pass'` assertion remains acceptable for AC-003. The test still directly binds the frozen adoption base, route base, base kind, bootstrap state, exact comparison base, architecture fingerprint, and evidence fields. The current route's independent architecture gate passes against stacked base `9493741…`, so the binding regression is no longer coupled to unrelated cumulative fitness of a later dirty worktree.

## Residual test risk

The positive classification is intentionally Linux/procfs-specific. Real PID churn or restricted procfs may conservatively return `unknown`; the deterministic tests prove that this availability failure cannot become cleanup success. Local verification and this review remain preflight evidence and do not replace the App-owned exact-SHA Trust CI check or required external approvals.
