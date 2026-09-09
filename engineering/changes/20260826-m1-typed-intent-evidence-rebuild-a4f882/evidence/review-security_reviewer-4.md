# M1 security re-review 4

## Verdict

**BLOCKED** for exact HEAD `ee9ed6ada12f78f808a12df311a41d7888ca9d30` against remediation base `1e3c5ce3cde0f60a65343e7df1764ced4e56c290` and original review base `0a4dd0a867c876f99a8fe3580c9f0d47c90e3105`.

The candidate closes the previously reported Git display-quoting failure for Unicode/LF/tab/backslash paths and closes unpaired-surrogate crashes with signed raw provenance. However, exact-path preservation is now asymmetric with approval-rule parsing: dot-prefixed protected globs and literal-backslash globs are still rewritten, so real protected paths can receive no required scope. The purported aggregate Git-output bounds also run only after unbounded capture/all-record allocation and therefore do not bound trusted-worker memory. No passing `security_review` receipt should be recorded for this HEAD.

## Exact-HEAD verification

- `git rev-parse HEAD` — `ee9ed6ada12f78f808a12df311a41d7888ca9d30`.
- Focused root suites, `python3 -m unittest tests.test_change_spec tests.test_change_receipts -v` — **42 passed**.
- Focused Trust CI suites for holdout, policy, runner, signing, and PostgreSQL — **82 passed, 10 skipped**. Every skip was an honest conditional PostgreSQL skip because `TRUST_CI_TEST_DATABASE_URL` is not configured.
- Full root discovery — **223 passed**.
- Full Trust CI discovery — **182 passed, 10 skipped**.
- Holdout bundle after testing contains exactly `change_spec_validate.py` and `validate.py`; digest `e2de03333ac37e6478433ad37486f6ee904ae8ba8054c86481c04eb7d56fcd64` matches `trust-ci/config/policy.example.json`.
- `git diff --check 1e3c5ce3cde0f60a65343e7df1764ced4e56c290..HEAD` — passed.

## Prior finding closure

| Reviewed boundary | Result | Evidence |
| --- | --- | --- |
| Unicode/LF/tab/backslash Git identity | **Closed in changed-path and mutation parsing** | `git diff --name-only -z` and `git status --porcelain=v1 -z` are consumed as strict UTF-8 bytes. A real temporary Git repository returned every unusual path exactly. Mutation reporting also returned the exact four paths. |
| Approval-scope binding for unusual paths | **Partially closed; blocking regression remains** | Broad `trust-ci/**` matched Unicode, LF, tab, and backslash children. Dot-prefixed and literal-backslash policy globs do not match exact paths; see SEC-R4-001. |
| Signed unusual-path provenance | **Closed for exercised paths** | Exact `Checkout.changed_files` now flows without slash/leading-prefix rewriting into spec selection and `AttestationPayload`; the real-repository signing regression passes. |
| Unpaired surrogates in values and keys | **Closed** | Local, independent holdout, and trusted metadata walkers reject surrogate code points before UTF-8 canonicalization. Direct adversarial execution returned controlled `SpecError`, `SystemExit`, and `SpecMetadataError`, respectively. |
| Signed raw provenance on surrogate failure | **Closed** | Runner raw bytes are hashed before parsing. Direct extraction returned `spec_digest=855ec2637fe5954d806a1a1f5f883dfdcccee53525d4e64e357bdf296c14b526`, exactly matching an independently computed composite digest; the full runner regression proves zero coverage, no commands, and a verifiable signed failure. |
| Exact base/head identity and path validation | **Closed for reviewed vectors** | Checkout still binds the fetched PR ref and detached HEAD to the job SHA; `_changed_files()` verifies both commit objects and uses them as explicit diff operands followed by `--`. Missing commit, invalid UTF-8, absolute path, traversal, missing terminal NUL, empty records, and a path over 4096 bytes fail closed. |
| Aggregate byte/path resource bounds | **Not closed** | Logical rejection checks exist, but allocation happens before them; see SEC-R4-002. |

## Findings

### SEC-R4-001 — P0 / blocking: exact paths no longer match dot-prefixed and literal-backslash approval globs

`Policy.required_scopes()` was correctly changed to preserve exact Git paths (`trust-ci/src/adaptive_trust_ci/policy.py:277-283`). `ApprovalRule.from_dict()` was not changed with it: line 68 still runs every policy glob through `.replace('\\', '/').lstrip('./')`.

`str.lstrip('./')` does not remove one optional `./` prefix; it removes every leading `.` or `/` character. Consequently deployed-shape rules such as `.grok/**`, `.grok-stack/**`, `.github/**`, and `.coveragerc` are stored without their leading dot. Because changed paths are now exact, these rules never match. Rewriting `\\` to `/` similarly prevents a policy from targeting a literal-backslash Git filename.

Independent policy reproduction:

```text
authored='.grok-stack/**' stored='grok-stack/**' path='.grok-stack/hook.py' scopes=[]
authored='.github/**' stored='github/**' path='.github/workflows/check.yml' scopes=[]
authored='.coveragerc' stored='coveragerc' path='.coveragerc' scopes=[]
authored='trust-ci/back\\slash.txt' stored='trust-ci/back/slash.txt' path='trust-ci/back\\slash.txt' scopes=[]
```

A real Git repository confirmed that `_changed_files()` returns `.grok-stack/hook.py` exactly while the current parsed policy returns no governance scope. In the same run, Unicode/LF/tab/backslash children of broad `trust-ci/**` correctly returned governance, demonstrating that the residual failure is policy-pattern rewriting rather than Git parsing.

This is a human-approval bypass for current protected control-plane and production paths, and directly contradicts the approved architecture's requirement that `.grok-stack/**` changes independently trigger deployed governance policy.

Required repair:

- preserve approval glob identity consistently with exact Git paths; do not use character-set `lstrip()` or unconditional backslash rewriting;
- if a convenience `./` prefix is supported, remove exactly one `./` with `removeprefix('./')` while preserving `.github` and other dot names;
- add policy and full `JobRunner` regressions for `.grok/**`, `.grok-stack/**`, `.github/**`, `.coveragerc`, and an explicitly targeted literal-backslash filename, proving action-required/no-command behavior without the corresponding signed scope.

### SEC-R4-002 — P1 / blocking: Git output limits are checked only after unbounded memory allocation

`GitWorkspace._git_bytes()` uses `subprocess.run(..., capture_output=True)` and returns the complete stdout (`trust-ci/src/adaptive_trust_ci/workspace.py:172-184`). Only after the child exits does `_nul_records()` check the 100 MB aggregate limit. It then evaluates `tuple(raw[:-1].split(b'\0'))` before checking the 100,000-record limit (`workspace.py:104-115`).

Thus attacker-controlled diff/status output is fully accumulated before the byte limit is consulted. Even output within 100 MB can contain tens of millions of tiny records; `split()` plus tuple construction allocates all record objects before the count check and can consume far more than the raw byte cap. Output above 100 MB has no allocation bound at all. The 120-second timeout is a time bound, not a memory bound.

Per-record validation itself behaved correctly in adversarial checks:

```text
missing terminal NUL -> controlled RuntimeError
empty record -> controlled RuntimeError
4096-byte record -> accepted
4097-byte record -> controlled RuntimeError
invalid UTF-8 / absolute / traversal -> controlled RuntimeError
```

The blocking issue is aggregate resource enforcement, not record semantics. A sufficiently large PR tree can exhaust the trusted worker before it reaches the intended fail-closed result.

Required repair: stream stdout from `git diff`/`git status` with a hard `max+1` byte read, terminate the child on overflow, and parse NUL records incrementally while enforcing total bytes, record count, and per-record bytes before allocating the complete collection. Add boundary tests for exactly-at/over byte, count, and record limits, plus a fake child producing over-limit output to prove bounded termination rather than post-capture rejection.

## Security boundary conclusion

The prior surrogate and Git display-quoting exploits are materially repaired, and the test/holdout tree is repeatable on this HEAD. Nevertheless, SEC-R4-001 permits mandatory governance/production approval scopes to be omitted for protected dot paths, while SEC-R4-002 leaves the trusted path-discovery boundary susceptible to attacker-controlled memory exhaustion. Both require a new exact-HEAD security review. Local evidence remains advisory and cannot replace the App-owned policy-epoch exact-SHA check or external signed approvals.
