# TR-001 remediation — direct post-KILL classifier coverage

`test-review.md` remains an unchanged record of the prior failing review and is superseded for the prior fingerprint. This remediation adds deterministic direct execution of `_classify_post_kill_process_group()` using mocked bounded `scandir`, `open`, `read`, and monotonic-time inputs; it does not alter production cleanup behavior.

## Characterization RED

The independent review established the coverage gap on the prior tree:

```text
PYTHONPATH=trust-ci/src coverage run --branch --source=adaptive_trust_ci.workspace \
  -m unittest trust-ci.tests.test_workspace -q

Ran 19 tests in 3.091s
OK
workspace.py: 69%; classifier lines 113-149 unexecuted
```

This was a test-observability failure rather than a changed runtime result: integration tests patched the classifier return value and could not detect parser or bounded-procfs defects.

## GREEN

`PostKillProcessGroupClassifierTests` directly proves all matching Z records return `zombie_only`; `R`, `S`, and explicitly `X` return `live`; malformed, truncated, oversized, unavailable, open/read-error, entry-cap, deadline, and final-probe uncertainty return fail-closed outcomes. A vanished PID is tolerated only when the final group-existence probe proves absence.

```text
PYTHONPATH=trust-ci/src python3 -m unittest \
  trust-ci.tests.test_workspace.PostKillProcessGroupClassifierTests -v

Ran 9 tests in 0.025s
OK
```

```text
COVERAGE_FILE=/tmp/fa3ae6-full-workspace.coverage \
PYTHONPATH=trust-ci/src coverage run --branch --source=adaptive_trust_ci.workspace \
  -m unittest trust-ci.tests.test_workspace -q

Ran 28 tests in 3.202s
OK
trust-ci/src/adaptive_trust_ci/workspace.py: 81%; classifier body lines 105-157 fully executed except the own-worker-PGID guard, which remains covered by the existing signal guard test.
```

```text
digest-pinned immutable runner, read-only root/source, UID/GID 10001, network none, tmpfs /tmp:

PYTHONPATH=/workspace/.grok-stack:/workspace/trust-ci/src \
  python3 -m unittest trust-ci.tests.test_workspace -q

Ran 28 tests in 3.406s
OK
RUFF_CACHE_DIR=/tmp/ruff-cache ruff check trust-ci/src/adaptive_trust_ci/workspace.py trust-ci/tests/test_workspace.py
All checks passed!
```

A fresh independent test review remains required on this new fingerprint; this document is remediation evidence, not a review receipt.
