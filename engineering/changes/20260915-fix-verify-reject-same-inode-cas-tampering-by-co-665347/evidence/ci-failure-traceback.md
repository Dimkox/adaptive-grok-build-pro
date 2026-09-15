# Retained external failure evidence

Source: Trust CI job store (`adaptive-trust-ci-postgres-1`, table `trust_ci_jobs`, job for PR #64 head `23dd5c58c7dd251c3468a7cdaa31ace0b3d6db75`, `status=failed`, `failure_code=verification-failed`, GitHub App check run `104549121465`, started `2026-09-15T20:19:07Z`, finished `2026-09-15T20:27:12Z`).

Per-command outcome recorded with the job:

```text
holdout-bundle-integrity|pass|0
external-holdout|pass|0
root-unittest|fail|1
```

`root-unittest` command is `python3 -m unittest discover -s tests` (required, `timeout_seconds=900`), which is byte-identical to the command run locally in a clean worktree.

Retained `stdout_tail` of the failing command, verbatim:

```text
.................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................s...........................................................................Automatic merge went well; stopped before committing as requested
.............................................................................F................
======================================================================
FAIL: test_same_inode_content_change_with_restored_mtime_is_rejected (test_workflow_artifacts_adversarial.SerializedCasTests.test_same_inode_content_change_with_restored_mtime_is_rejected)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/tests/test_workflow_artifacts_adversarial.py", line 706, in test_same_inode_content_change_with_restored_mtime_is_rejected
    ARTIFACTS.cas_write(
  File "/workspace/.grok-stack/adaptive_grok/workflow_artifacts.py", line 1688, in cas_write
    _rename_exchange(parent_fd, temporary, target_parts[-1], temporary_identity, current_identity)
  File "/usr/local/lib/python3.12/unittest/mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
  File "/usr/local/lib/python3.12/unittest/mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
  File "/usr/local/lib/python3.12/unittest/mock.py", line 1204, in _execute_mock_call
    result = effect(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "/workspace/tests/test_workflow_artifacts_adversarial.py", line 701, in exchange
    self.assertNotEqual(target.stat().st_ctime_ns, original.st_ctime_ns)
AssertionError: 1789504031135392670 == 1789504031135392670

----------------------------------------------------------------------
Ran 715 tests in 467.966s

FAILED (failures=1, skipped=1)
```

## Reading of the evidence

- Exactly one test failed, and it failed inside the test's own tampering precondition (`exchange`), not inside product code: the traceback's last frame is the assertion at line 701.
- The two compared `st_ctime_ns` values are identical to the nanosecond, which is what a filesystem reports when its timestamp granularity cannot resolve the write, `fsync` and `utime` sequence within one tick. Nothing about the CAS behaved differently.
- The local run of the same command on the same tree passed (`Ran 715 tests ... OK`), so the defect is a host-capability assumption in the test, not a regression introduced by the pull request that surfaced it.
- The rejection is layered, and which layer fires depends on the filesystem. Measured on this host, the scenario is caught at the exchange itself: `_rename_exchange` compares the full six-field identity tuple strictly (`workflow_artifacts.py:1433-1436`) and raises `code="race"` while the target keeps the competitor bytes. On a filesystem whose ctime cannot resolve the tamper that guard does not abort — the expected identity was snapshotted at the same instant, so the strict compare passes and the exchange completes — and the post-exchange displaced-digest re-read rejects instead (`:1694-1742`), again with the competitor bytes retained. The pre-write expected-digest comparison (`:1646-1651`, `code="cas"`) never fires in this scenario, because the digest is sampled at the same instant the expected value is recorded; it is the layer the *new* test pins, in a scenario where every non-content identity field is equal. The assertion at line 701 demanded that one specific layer fire, when the guarantee is that some layer always does.
