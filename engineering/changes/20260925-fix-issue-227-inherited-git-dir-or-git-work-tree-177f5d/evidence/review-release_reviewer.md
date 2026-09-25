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
