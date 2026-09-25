# Release/readiness review — issue #227

## Verdict

**FAIL — local workflow readiness is blocked by a stale required scope gate.**

The source repair and exact-head verification evidence are otherwise suitable for
local handoff. This is not a source-code rejection: the candidate cannot be
declared locally complete until the required scope-and-design decision is bound
to the current scope and the coordinator persists all reviews, reruns final
verification, and records fresh fingerprint-bound receipts.

**EXTERNAL DELIVERY: NOT AUTHORIZED.** No push, pull-request write, merge, tag,
release, deployment, network access, or Daybreak operation was performed or is
authorized by this review. Local evidence does not substitute for the App-owned
exact-PR-head Trust CI check.

## Review identity

- Route: `177f5dc1d5cf`
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Reviewed HEAD: `5f4e8fef003271a9b62198d181ad6be1f1838158`
- Reviewed Git tree: `eb0e0f649e0e17d55f93be8ab46b859e436d56f7`
- Pre-report candidate fingerprint from the exact-head verification receipt:
  `4f1fce294a4c85af9db462daa8a7a33acca5636781cdbfaef9800a1f58eceba3`
- Worktree before report persistence: clean (`git status --porcelain=v1
  --untracked-files=all` produced no output)
- Scratch path: not created; release review used read-only inspection and no
  mutation probe.
- `reviewed-tree-modified: no` (this reviewer subsequently added only this
  requested report; another selected review report appeared concurrently after
  the clean candidate snapshot).

## Findings

### Critical

None.

### Important

1. **The required scope-and-design approval is stale on the reviewed tree.**
   The typed spec requires `scope_and_design_approval`
   (`change-spec.yaml:24-25`), while the recorded decision remains bound to its
   earlier scope digest (`human-gates.json:8-14`). On reviewed HEAD
   `5f4e8fef003271a9b62198d181ad6be1f1838158`, `python3
   scripts/grok_status.py` reports the gate state as `stale` with reason
   `recorded decision no longer matches route, change, or scope`. This is a
   required high-risk workflow gate and prevents a local go decision. Refresh
   it through the repository workflow only from valid explicit user consent;
   if that consent cannot be rebound under policy, obtain a new human decision.

### Minor

None.

## Readiness assessment

### Acceptance evidence

- The implementation applies the paired control required by the design:
  repository probes remove `GIT_DIR`/`GIT_WORK_TREE`
  (`.grok-stack/adaptive_grok/util.py:16-23,38-44,133-150,182-205`), and branch
  or tag push evaluation denies selector presence before human-gate/grant lookup
  (`.grok-stack/adaptive_grok/_policy_legacy.py:589-611`). Empty values are
  denied by key presence, not truthiness.
- Tests cover root-bound identity/HEAD/inventory/fingerprint
  (`tests/test_util_fingerprint.py:141-196`), a matching foreign checkout with a
  foreign push URL and no push execution (`tests/test_policy.py:106-145`), each
  selector plus empty values and clean-environment compatibility
  (`tests/test_policy.py:147-192`), and the real hook denial with secret-safe
  output and unchanged Git state (`tests/test_hooks.py:168-233`).
- RED/GREEN evidence records the original reproduction and final focused result:
  80 focused tests and 49 nearby contract tests passed, followed by a 129-test
  combined rerun (`evidence/implementation-general_implementer.md:13-102`).
- The current verification receipt is `status=pass`, created
  `2026-09-25T09:03:16+00:00`, bound to route `177f5dc1d5cf`, reviewed HEAD
  `5f4e8fef003271a9b62198d181ad6be1f1838158`, and fingerprint
  `4f1fce294a4c85af9db462daa8a7a33acca5636781cdbfaef9800a1f58eceba3`.
  Its 16 checks include passing diff, spec, architecture, governance, secret,
  Ruff, Bandit, Python, coverage, factory, PostgreSQL-exit, and source-stability
  checks; workflow artifacts are explicitly not configured.

### Compatibility and operational behavior

- No public API, grant schema, HTTP/event contract, migration, dependency,
  release identity, or feature flag changes are introduced. Existing
  clean-environment exact-action grant behavior remains covered
  (`tests/test_policy.py:147-164`; `architecture.md:33-35`).
- The intentional compatibility tightening is fail-closed: callers exporting
  either selector, including an empty value, must unset it and retry. The denial
  names only selector keys and the hook continues recording the denial at the
  intended repository root (`tests/test_hooks.py:218-233`).
- The change adds no network client or GitHub/Daybreak integration. Regression
  fixtures clone local paths and inspect local configuration; they never invoke
  `git push`. The typed forbidden outcome records the same boundary
  (`change-spec.yaml:33-42`).

### Rollback, forward-fix, and observability

- Rollback is correctly forward-fix only: do not reopen the vulnerable allow
  path; disable delegated agent Git pushes, correct selector handling, and rerun
  the P0 and full-route checks (`rollback.md:3-21`). There is no migration or
  persistent product data to recover; changed-tree grants become stale.
- The observable signal is an actionable, secret-safe policy denial naming only
  the present selector key(s), with the hook-level denial ledger asserted by the
  integration test (`release.md:13-15`; `tests/test_hooks.py:218-231`).
- Root-local `remote.origin.pushurl` mutation without ambient selectors remains
  explicitly out of scope and is not presented as fixed
  (`evidence/implementation-general_implementer.md:119-125`).

## Local closure conditions

1. Resolve the Important stale-gate finding without fabricating consent.
2. Persist the selected code, test, security, and release reports and address
   any blocker they contain.
3. Because adding review reports changes the repository fingerprint, rerun
   `python3 scripts/grok_verify.py --mode pr` on the final tree and record fresh
   exact-fingerprint review receipts. The unchecked closure items at
   `tasks.md:6-8` must reflect actual completed evidence, not anticipation.
4. Keep external delivery separate. Any future pull-request delivery still
   requires explicit operation authority and the GitHub App-owned
   `adaptive-trust-ci/verified@<policy-sha12>` check on the exact PR head.

## Probes performed

- `git rev-parse HEAD`, `git rev-parse
  cb9af4073ba6c3d515145164d771c75ebdfa3224^{commit}`, `git rev-parse
  HEAD^{tree}`, `git status --porcelain=v1 --untracked-files=all` — exact
  identities above; candidate clean before report.
- `git diff --stat`, `git diff --name-status`, and full source/test diff for
  `cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158`
  — 25 scoped paths; two implementation modules, three regression-test files,
  and durable plan/change evidence; no release artifact, deployment, workflow,
  migration, or dependency path.
- `git diff --check
  cb9af4073ba6c3d515145164d771c75ebdfa3224..5f4e8fef003271a9b62198d181ad6be1f1838158`
  — exit 0, no output.
- Read `.grok-stack/runtime/receipts/177f5dc1d5cf/verification.json` — exact-head
  `status=pass` and fingerprint listed above.
- `python3 scripts/grok_status.py` — clean worktree, four pending review
  receipts, and the required scope gate reported stale.

No release mutation test was executed: this review assessed already verified
local source and workflow readiness, and the assignment prohibited all external
or release actions.

---

## Re-review — repaired exact head

Re-review date: 2026-09-25.

### Final local verdict

**PASS — the issue #227 candidate at exact HEAD
`57c249d2b8543742bdfdcbaba364797a86ab489f` is locally release-ready for
coordinator evidence closure.**

The earlier FAIL remains valid historical evidence for HEAD
`5f4e8fef003271a9b62198d181ad6be1f1838158`. Its stale-gate blocker and the
subsequent test-review blockers are closed on this repaired head. No Critical or
Important readiness finding remains.

**EXTERNAL DELIVERY: NOT AUTHORIZED.** This PASS authorizes no push,
pull-request write, merge, tag, release, deployment, network access, or
Daybreak operation. It is local workflow evidence only and does not replace the
GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on an exact
pull-request head.

### Exact binding

- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Re-reviewed HEAD: `57c249d2b8543742bdfdcbaba364797a86ab489f`
- Git tree: `2ac21d83a525ab70187045e19b682dea953fe208`
- Clean committed-tree fingerprint from the exact-head verifier and independent
  test re-review:
  `e50bf7e4d44594a60f8558646c7f3f988c93b4a0f463250a9a6323a0d2c08ce3`
- `reviewed-tree-modified: no`; this reviewer appends only this re-review to the
  assigned report. Concurrent test/security re-review appendages do not change
  HEAD, the Git tree, or reviewed source/test bytes.

### Closed findings and current evidence

1. **Prior release finding closed — scope gate is current.** `python3
   scripts/grok_gate.py status` reports `scope_and_design_approval` as
   `approved`, bound to current scope digest
   `c66f8353752dd7aa310e7b6ba5623aef7e40dee19572c1f7768e35ff4ba1bcf2`.
   The latest recorded decision at `human-gates.json:16-27` preserves the
   user-approved local-only scope and explicitly authorizes no external
   operation. The gate output reiterates that it is local workflow evidence,
   not merge or operational authority.
2. **Full verifier is current for the repaired committed candidate.** The
   verification receipt is `status=pass`, created
   `2026-09-25T09:37:59+00:00`, bound to route `177f5dc1d5cf`, HEAD
   `57c249d2b8543742bdfdcbaba364797a86ab489f`, and fingerprint
   `e50bf7e4d44594a60f8558646c7f3f988c93b4a0f463250a9a6323a0d2c08ce3`.
   All configured checks pass; workflow artifacts alone are explicitly not
   configured, and source stability passed.
3. **Test-review I-01 closed — exact tag compatibility.** The repaired test
   creates a selector-free `git-push-tag` grant and requires the matching tag
   push to be allowed (`tests/test_policy.py:224-240`). The independent test
   re-review killed an unconditional clean-tag denial mutant.
4. **Test-review I-02 closed — denial ordering.** The repaired test replaces
   the evaluator's approval lookup with a raising mock and proves it is not
   called for inherited-selector branch and tag pushes
   (`tests/test_policy.py:197-222`). The independent re-review killed the
   approval-before-selector mutant.
5. **Test-review I-03 closed — both-empty selector presence.** The core table
   now covers both keys present with empty values
   (`tests/test_policy.py:174-176`), and the real hook subprocess covers the
   same case (`tests/test_hooks.py:235-255`). Both core and hook mutants were
   killed by the independent re-review.
6. **Independent repaired-head test verdict is PASS.** The route-selected test
   reviewer ran the 83-test focused suite successfully, reran the four repaired
   cases under exec/network tracing, observed zero Git-push executions and zero
   network syscalls, and recorded a final PASS for this exact head. The earlier
   test FAIL remains correctly scoped to the prior head.
7. **Independent repaired-head security verdict is PASS.** Production policy
   bytes are unchanged from the first reviewed source, the strengthened tests
   add no new disclosure or bypass, and the security re-review reports no
   Critical, Important, or Minor finding for this exact head.

### Residual and closure boundary

- The test review retains one non-blocking Minor limitation: the ordinary real
  hook regression is observational rather than a permanently hermetic
  process-level network sandbox. Independent tracing of both original and
  repaired cases observed no push and no network syscall; the core exploit test
  also retains its direct push tripwire. This does not block the bounded
  local-only fix.
- Root-local push-URL mutation and unscoped Git/config selectors remain the
  already documented residual scope; this change does not claim to solve them.
- Persisting the test, security, code, and this release re-review changes the
  repository fingerprint. The coordinator must therefore run final
  `python3 scripts/grok_verify.py --mode pr` and record fresh fingerprint-bound
  review receipts after all reports are frozen. That bookkeeping is required
  for local completion but does not change this exact-head readiness PASS.

Final local verdict for
`cb9af4073ba6c3d515145164d771c75ebdfa3224..57c249d2b8543742bdfdcbaba364797a86ab489f`:
**PASS**.
