# fix(verify): reject same-inode CAS tampering by content digest, not by filesystem ctime granularity

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260915-fix-verify-reject-same-inode-cas-tampering-by-co-665347`
Created: 2026-09-15T21:35:12+00:00
Risk: medium
Complexity: standard
Domains: test-infra, verification

## Reproduction (external, not local)

The App-owned check for PR #64 head `23dd5c58` published `verification-failed` at `2026-09-15T20:27:12Z`; the retained job record (`trust_ci_jobs.result->commands`, command `root-unittest`, `exit_code=1`, `Ran 715 tests in 467.966s`) names exactly one failure — see [ci-failure-traceback.md](evidence/ci-failure-traceback.md):

```text
FAIL: test_same_inode_content_change_with_restored_mtime_is_rejected
  File "/workspace/tests/test_workflow_artifacts_adversarial.py", line 701, in exchange
    self.assertNotEqual(target.stat().st_ctime_ns, original.st_ctime_ns)
AssertionError: 1789504031135392670 == 1789504031135392670
```

The same command passes on this host's filesystem (`715 tests OK` in a clean worktree), which is what kept the defect invisible until PR #93 merged: the assertion holds only where `ctime` resolves two sub-jiffie writes. On the runner's filesystem the two reads are equal, so the *precondition* of the test fails before the product behavior is exercised at all.

## Problem

`SerializedCasTests.test_same_inode_content_change_with_restored_mtime_is_rejected` asserts that `st_ctime_ns` strictly changed, as a way of proving the simulated same-inode tamper really happened. `ctime` is the one identity field a filesystem may be unable to advance within a single test, so the assertion encodes a filesystem capability the project never claimed to require. Because `root-unittest` is a mandatory Trust CI command, that brittleness blocks every pull request whose run happens to land inside one ctime tick — including unrelated documentation changes such as PR #64.

The product is not at fault and is not changed here, and its rejection is layered rather than carried by one comparison. Before writing anything, `cas_write` compares the on-disk digest with the caller's expected digest (`workflow_artifacts.py:1646-1651`, `"CAS expected digest mismatch"`, `code="cas"`). At the exchange itself, `_rename_exchange` re-reads the target identity and compares the **full** six-field tuple — including `st_ctime_ns` — strictly (`:1433-1436`, `"CAS exchange target identity changed"`, `code="race"`), which is the layer that actually fires in this scenario on a host whose ctime advances (measured: `code="race"`, competitor bytes retained). After the exchange, `_post_exchange_identity_matches` deliberately compares the first five fields with `==` and ctime with `>=` (`:1415-1419`) and the displaced digest is re-read (`:1694-1742`), so a filesystem whose ctime cannot resolve the tamper still ends in a rejection with the competitor bytes intact. The assertion at line 701 therefore demanded that one specific layer fire, when the guarantee is that some layer always does: measured here the exchange guard rejects with `race`, and when ctime cannot carry the signal the exchange proceeds and the post-exchange displaced digest rejects instead, with the competitor bytes retained in both cases.

## Outcome

The adversarial suite states its premise with fields that are always observable — restored inode, size and mtime plus differing content — instead of requiring one layer's signal; the original scenario still asserts that the exchange is refused and the competitor bytes survive. The new test pins the one rejection that never depends on the filesystem, the pre-write `cas` digest comparison, in a scenario where every non-content identity field is equal. The mandatory verification command becomes independent of filesystem timestamp granularity without removing any fail-closed assertion.

## Scope

### In scope

- `tests/test_workflow_artifacts_adversarial.py`: replace the strict ctime precondition with the restored-field equalities plus a content-difference assertion, and add the digest-carried rejection scenario.
- `mistakes.md`: record the root cause as a repository-wide rule about timestamp-granularity assumptions.

### Out of scope

- Any change to `.grok-stack/adaptive_grok/workflow_artifacts.py`, its identity tuple, `_post_exchange_identity_matches`, or the expected-digest comparison.
- Machine-local deployment state under `trust-ci/runtime/` (root-owned key material that the repository verifier correctly refuses to walk); that is an operator-environment fact, recorded in `mistakes.md`, not a product defect.

## Constraints

- Backward compatibility: test-only; no public behavior, schema or contract changes.
- Data/privacy: no credential, key or machine-local runtime state enters the diff.
- Performance: not applicable.
- Operational: the fix must not weaken a rejection; `INV-001` and `FORBID-001` bound it.
