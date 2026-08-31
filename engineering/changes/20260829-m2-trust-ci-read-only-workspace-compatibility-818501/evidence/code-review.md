# Independent code review

## Identity and verdict

- Route: `81850148d1f6`
- Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m2`
- Reviewed HEAD: `635c9ddf2d63c1ea823074106976a8f3de6299a9`
- Reviewed worktree fingerprint before this report: `58854a896966d3ec160697d61ca4e1dded628eddc028ef994a032d5a135483c7`
- Scope: the tracked worktree diff from HEAD plus the untracked active change package.
- **Verdict: FAIL** — one Important performance/contract finding remains. No Critical findings.

The supplied pinned-runner result is 378/378 PASS, but local review evidence and repository reports are not merge authority. The exact PR head still requires the GitHub App-owned policy-epoch check and required external approvals.

## Strengths

- Repository Git operations resolve the repository once and add only `-c safe.directory=<canonical-root>` to that command; isolated global/system configuration remains disabled. The non-repository `git diff --no-index` path does not acquire repository trust (`.grok-stack/adaptive_grok/architecture_diff.py:173-227`, `:631-654`).
- Manifest generation remains backward-compatible and explicitly source-writing, while package construction uses a pure rendered manifest and no longer creates, replaces, or removes the source `MANIFEST.sha256` (`.grok-stack/adaptive_grok/manifest.py:50-59`, `scripts/package_stack.py:19-40`).
- The receipt regression preserves `clone --no-local` and provides its child process a temporary global config containing the exact `ROOT/.git` trust entry while disabling system and host-global configuration (`tests/test_change_receipts.py:322-351`).
- The finite 10,100-line budget is explicit, worktree fitness passes, and the published rules/composite digests exactly match the canonical summary (`architecture/rules.yaml:37-49`, `engineering/changes/20260826-m2-executable-architecture-015603/requirements.md:17-25`).
- No `trust-ci/**` or `.github/workflows/**` path is changed; public API/event/data contracts are unchanged.

## Findings

### Critical

None.

### Important

#### I1 — Archive checksum still materializes the entire ZIP in memory

**Evidence:** `scripts/package_stack.py:33-38` correctly streams each source member into the ZIP, but line 38 immediately calls `output.read_bytes()` and passes the resulting whole-archive allocation to `hashlib.sha256`. This contradicts the approved constraint that only paths, metadata, and synthetic manifest bytes are retained in memory (`engineering/changes/20260829-m2-trust-ci-read-only-workspace-compatibility-818501/brief.md:36-41`). The focused tests validate archive determinism and content, but do not bound checksum memory.

**Rationale:** Peak memory remains proportional to the complete compressed archive, so a large otherwise-valid package can exhaust the isolated runner after the new streaming member path succeeds. The implementation and durable architecture description currently make a stronger bounded-memory claim than the code provides.

**Required fix:** Hash the completed archive through a bounded read loop (the existing 1 MiB pattern in `adaptive_grok.manifest.sha256` is sufficient), then write the unchanged sidecar format. Add a regression that prevents `Path.read_bytes()`/an unbounded archive read in the package checksum path.

### Minor

#### M1 — The active package records the full-suite size as 377 after the suite became 378

**Evidence:** `tasks.md:12`, `test-plan.md:30`, and `release.md:22` all say “377-test” while the supplied pinned run for this exact fingerprint is 378/378. The documents appropriately leave parent-owned verification/review incomplete, but the frozen count is stale.

**Suggested fix:** Update the count to 378 when recording the parent verification evidence, without changing the package's draft/merge-authority disclaimers.

## Commands and evidence inspected

- `git rev-parse HEAD` -> `635c9ddf2d63c1ea823074106976a8f3de6299a9`.
- `git status --short`, `git diff --stat HEAD`, `git diff --name-status HEAD`, and `git diff --check HEAD` -> the expected 11 tracked files plus the active untracked package; no whitespace error and no Trust CI/GitHub Actions change.
- Read the active route, typed change spec, brief, requirements, architecture, tests, release/rollback/tasks, actual diff, and surrounding implementation.
- Independent `tree_fingerprint(root)` -> `58854a896966d3ec160697d61ca4e1dded628eddc028ef994a032d5a135483c7`, matching the supplied preflight identity.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_architecture.py summary --json` -> architecture `07b1081b...`, rules `196481e7...`, system `da6453d9...`, schema `c702531d...`, inventory `039feea9...`; all match the frozen handoff literals.
- Five focused unit regressions (different-owner architecture Git, source-manifest preservation, archive determinism, receipt clone/staleness, frozen digest summary) -> 5/5 PASS in 8.504 s.
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/grok_architecture.py fitness --base 25bfbe59ea188d9687b20a9caad19e7db3d031f8 --worktree --pre-risk red --json` -> PASS; bounded-architecture budget result PASS.
- Final pre-report `git diff --check HEAD`, HEAD, status, and fingerprint recheck remained unchanged.

## Residual/cannot-verify items

- I did not rerun the broad 378-test suite or recreate the privileged/non-root read-only container; the parent supplied that pinned-runner result, and the focused review was intentionally non-duplicative.
- This report is local review evidence only and does not authorize push, merge, release, deployment, or substitute for the exact-SHA external Trust CI check.
