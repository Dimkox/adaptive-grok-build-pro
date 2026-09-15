# Test plan — fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Same-inode rewrite with restored atime/mtime is rejected by `cas_write` | `SerializedCasTests.test_same_inode_content_change_with_restored_mtime_is_rejected` |
| P0 | Rejection survives a filesystem where no identity field changes, and is pinned to failure code `cas` | `SerializedCasTests.test_same_inode_content_change_is_rejected_when_identity_cannot_resolve_it` |
| P1 | Mandatory external command `root-unittest` no longer depends on ctime resolution | App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on this head, `commands[name=root-unittest].status` |
| P1 | Product CAS code untouched | `git show --stat` scope check; `INV-002` |

## Automated checks

- Unit: `python3 -m unittest tests.test_workflow_artifacts_adversarial tests.test_workflow_artifacts tests.test_workflow_artifacts_cli` (56 tests) plus the full discovery run.
- Integration: `python3 scripts/grok_verify.py --mode pr` in this worktree.
- Contract: `tests/test_change_spec.py` covers this package's typed spec; no OpenAPI/JSON-Schema/event file changes.
- E2E: not applicable — no runtime entry point is touched.
- Static analysis: `ruff` (clean on the edited file) and `bandit` as invoked by the verifier.

## Manual checks

- Read the retained external traceback (`evidence/ci-failure-traceback.md`) and confirm the failing frame is the test precondition, not product code.
- Confirm the competitor mutation actually changes the file: the byte flip is asserted through the content-digest inequality, not assumed.
- Confirm no assertion in the edited scenario can pass vacuously (equal identity fields are asserted before the rejection, and the rejection code is pinned).
