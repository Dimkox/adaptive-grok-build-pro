# Independent release/readiness review — issue #218 delivery

## Verdict

**FAIL — the committed source candidate is coherent, but local readiness is
blocked by stale gate binding and stale package-current-state claims.**

This is not a product-code rejection. The exact candidate has the required
one-commit topology, bounded source-relative delta, truthful product/user
documentation, rollback/observability plan, and no issue #219 or `trust-ci/**`
delta. It must not be declared locally ready until the two Important evidence
findings below are repaired and final post-report verification/receipts bind the
resulting frozen one-commit candidate.

**EXTERNAL DELIVERY: NOT AUTHORIZED.** No push, pull-request write, merge, tag,
release, deployment, production mutation, network access, or Daybreak operation
was performed or is authorized by this review. Local verification and reviews
do not substitute for the GitHub App-owned exact-PR-head Trust CI check.

## Review binding

- Route: `566746aef130`
- Change: `20260925-fix-github-issue-218-locally-deliver-the-verifie-566746`
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Reviewed HEAD: `cdad4de5cd9620a97d3919bc47c89ff923839623`
- Reviewed Git tree: `49ec3bd103c7e22b9019b10e084bc7f9b4602d70`
- Verified development source: `68dfc70c5f58adcc927f731c5d88de09a1b4b242`
- Development-source tree: `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`
- Scratch path: not created; this release review used read-only inspection and
  no mutation probe.
- The worktree already contained a concurrent lifecycle-only modification to
  this package's `state.json` before this report was written. It did not change
  HEAD, the Git tree, or reviewed product bytes.
- `reviewed-tree-modified: no` — this reviewer writes only this assigned report.

## Findings

### Critical

None.

### Important

1. **The required scope-and-design gate is stale for the current package
   scope.** The typed spec requires `scope_and_design_approval`
   (`change-spec.yaml:10`), but `python3 scripts/grok_gate.py status` reports
   `state=stale`, reason `recorded decision no longer matches route, change, or
   scope`, and current scope digest
   `82dd5ab96a5ae3b67d50980527ae2552f048d9334059f07a37ce7867a2268940`.
   The only recorded decision is bound to digest
   `20cf865a0bbcc7948231e3ab22246e69d6e47a08b331328967625e0cc3a9b11c`
   (`human-gates.json:8-14`). The local-only user scope remains clear, but a
   high-risk required gate cannot be treated as current until the repository
   workflow binds valid explicit consent to the current digest.
2. **The durable package does not yet truthfully describe its current delivery
   state.** `tasks.md:11-12` says the single candidate is uncommitted and the
   full verifier/reviews have not run, although HEAD is the candidate commit and
   the concurrent state transition records the pre-review verifier PASS.
   `brief.md:44` still says the named gate is unminted, while
   `human-gates.json` contains a decision (currently stale), and
   `evidence/implementation-general_implementer.md:5,36` still labels the base
   as delivery HEAD and says full verification remains pending. These are
   understandable pre-review artifacts, but AC-005 requires durable truthful
   provenance and evidence. Reconcile them before `ready`; preserve the
   one-direct-child topology when freezing reports/package state, then rebind
   verification and reviews to the resulting exact candidate.

### Minor

None.

## Readiness evidence

### One-commit topology and provenance

- `git rev-list --count BASE..HEAD` returned `1`.
- The commit object has exactly one parent,
  `cb9af4073ba6c3d515145164d771c75ebdfa3224`; it is not a merge.
- The source commit resolves locally to tree
  `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`, matching the package's recorded
  pre-package squash projection (`brief.md:11-19` and
  `evidence/implementation-general_implementer.md:5-11`).
- The exact `68dfc70c...source..cdad4de5...candidate` delta contains only the
  active delivery package, three change-package templates,
  `tests/test_change_receipts.py`, `tests/test_hooks.py`, and `mistakes.md`.
  This matches the declared six-path compatibility repair plus package evidence;
  no scanner/receipt implementation path differs from the verified source.
- `git diff --check BASE..HEAD` passed with no output.

### Package and documentation truth

- The source-relative inventory satisfies AC-001 through AC-003's bounded
  topology/provenance contour. The compatibility repair removes generated
  trailing whitespace and routes stale fixtures through the existing closed
  scan-scope helper; it does not weaken receipt or scanner validation
  (`evidence/implementation-general_implementer.md:38-47`).
- README retains truthful release identity: product `2.0.19` remains a candidate,
  `v2.0.18` remains the latest published release, and publication/deployment are
  not claimed (`README.md:1-23`). Its worker defaults, dependency barriers,
  full-chain scan behavior, closed Factory inventory, and unverified local
  review provenance match this candidate (`README.md:25-35,67-71`).
- QUICKSTART correctly separates preliminary
  `grok_verify --mode pr --no-record` from the later clean committed final
  recording verification and verification-bound review receipts
  (`QUICKSTART.md:84-92`). It continues to identify local verification as
  preflight rather than merge authority (`QUICKSTART.md:120-124`).
- Factory inventory statements are internally consistent: 641 stateless plus
  154 database and nine harness/resource-sensitive tests equals 804; the
  installed profile totals 217 (`factory/README.md:31-33`,
  `factory/tests/factory_test_manifest.py:12-39`).

### Verification evidence

- The coordinator's exact-HEAD pre-review full verifier completed **PASS** for
  `cdad4de5cd9620a97d3919bc47c89ff923839623`; reported dynamic durations were
  Core `78.590s` and Factory `193.585s`.
- The concurrent package state transition records that the exact-head
  pre-review full verifier passed and moved the lifecycle from `verifying` to
  `reviewing` (`state.json:154-169` in the current worktree).
- No completion receipt exists yet, which is correct for the pre-review
  `--no-record` phase. Final recording verification belongs after all review
  reports and package truth are frozen. The present PASS must not be promoted
  into final completion evidence.

### Issue #219 and Trust CI exclusion

- `git diff --name-only BASE..HEAD -- trust-ci 'engineering/changes/*219*'
  '.github/workflows'` returned no paths.
- The exact source-relative inventory likewise contains no `trust-ci/**` or
  #219 package path. The candidate therefore does not absorb the parallel
  runner/holdout/policy/digest lane.
- Existing README/QUICKSTART references to Trust CI describe the unchanged
  external authority; they are documentation, not a Trust CI implementation
  delta.

### Rollback, observability, and compatibility

- Rollback is bounded and recoverable: before external delivery, abandon only
  the isolated branch; after delivery, use a reviewed revert of the single
  squash. No migration, database recovery, deployed-policy change, or secret
  recovery is involved (`rollback.md:3-17`).
- Observable go/no-go signals are the candidate SHA/tree, selected scan-scope
  status, exact source-relative delta, local verification/review receipts, and
  later external exact-SHA check (`release.md:10-16`,
  `change-spec.yaml:27-31`).
- No API/event/schema version, database migration, runtime rollout, or feature
  flag is introduced by the delivery topology repair. Backward compatibility is
  preserved by delivering the already verified cumulative tree plus the narrow
  fixture/template compatibility adjustment.

## Required closure

1. Rebind the required local scope-and-design decision to the current package
   scope through the repository workflow; do not fabricate or broaden consent.
2. Reconcile the brief, task checklist, implementation evidence, package state,
   and all selected review reports so they truthfully describe the frozen
   candidate and retain the one-commit invariant.
3. On that clean exact candidate, run the final recording
   `python3 scripts/grok_verify.py --mode pr`, record all four routed review
   receipts, and require zero gaps from read-only `grok_status.py`.
4. Keep external delivery separate. Any future PR/merge still requires explicit
   operation authority and the App-owned policy-epoch Trust CI check on the
   exact pull-request head.

Final local release/readiness verdict for
`cb9af4073ba6c3d515145164d771c75ebdfa3224..cdad4de5cd9620a97d3919bc47c89ff923839623`:
**FAIL pending the two Important evidence-closure repairs above.**

---

## Bounded final re-review — repaired candidate

### Verdict

**FAIL — the refreshed gate and the original review findings are closed, but
the exact repaired candidate is not locally release-ready because an independent
code re-review found a remaining root-binding bypass and the committed task
checklist still misstates the refreshed approval as pending.**

**EXTERNAL DELIVERY: NOT AUTHORIZED.** This re-review authorizes no push,
pull-request write, merge, tag, release, deployment, network access, Daybreak
operation, or production mutation. Local verification and review evidence do not
substitute for the GitHub App-owned policy-epoch Trust CI check on the exact
future pull-request head.

### Exact re-review binding

- Route: `566746aef130`
- Change: `20260925-fix-github-issue-218-locally-deliver-the-verifie-566746`
- Base: `cb9af4073ba6c3d515145164d771c75ebdfa3224`
- Re-reviewed HEAD: `ddd9988e4b43fd1502796de42fdcc52170233c61`
- Re-reviewed Git tree: `9a1dab623ee74f9f1d65e56ed5e6564c94ca5310`
- Verified development source: `68dfc70c5f58adcc927f731c5d88de09a1b4b242`
- Development-source tree: `0914b5d6ad8c9f35211c4ac96ea96807f5ee8a66`
- `reviewed-tree-modified: no` — this reviewer made no product, test,
  runtime-state, receipt, or configuration change and appended only this report
  section. Before the append, the active worktree already contained the
  coordinator's lifecycle-only `state.json` update and the three other reviewers'
  report appendages; none changes the reviewed Git tree.

### Findings

#### Critical

None.

#### Important

1. **Repository-local `core.worktree` can redirect the supposedly root-bound Git
   diff checks and produce a false whitespace PASS.** The hardened helper uses
   the resolved root as `cwd` and isolates ambient selectors/configuration, but
   it does not pass an explicit `--work-tree=<resolved root>`
   (`.grok-stack/adaptive_grok/util.py:19-59`). The endpoint and history
   whitespace checks consume that helper (`.grok-stack/adaptive_grok/verification.py:1742-1778`).
   The independent code re-review reproduced the defect in an exact-HEAD private
   clone: after setting local `.git/config core.worktree` to an empty foreign
   directory and adding trailing whitespace to the real root's tracked
   `VERSION`, `_git_diff_check(...)` returned `status=pass`, while explicitly
   binding Git to the real worktree reported the defect and exited nonzero
   (`evidence/review-code_reviewer.md:89-94`). This leaves AC-008's explicit-root
   and configuration-isolation requirement unmet. Bind every worktree-sensitive
   Git operation to the resolved supplied root, fail closed on inconsistent
   repository/worktree relationships, and add the local-configuration regression
   required by the code reviewer.
2. **The committed task checklist still marks an already completed approval as
   pending.** `tasks.md:15` leaves the refreshed scope/design decision unchecked,
   although the exact candidate commits the current approved decision and digest
   `27333d393f8284064aa1df968bea50c56a3869557cfb93f9dc79102d788fbe49`
   (`human-gates.json:16-26`), and `python3 scripts/grok_gate.py status` reports
   `state=approved`. This is now a narrow package-truth defect: the revised brief
   truthfully records the expanded repair scope (`brief.md:17-30`), and
   `tasks.md:16` appropriately remains incomplete while the re-review wave has a
   FAIL. Correct the completed approval step before final receipts; because that
   changes the candidate tree, bind the next verification/review wave to the new
   exact SHA.

#### Minor

None.

### Re-review evidence

- Topology remains exact: `git rev-list --count BASE..HEAD` returned `1`, and the
  sole commit's only parent is
  `cb9af4073ba6c3d515145164d771c75ebdfa3224`; it is not a merge.
- `git diff --check BASE..HEAD` passed. The exact base-to-HEAD query for
  `trust-ci/**`, `.github/workflows/**`, and issue-#219 package paths returned no
  paths, so this candidate has no Trust CI/#219 delivery delta.
- The required gate is current and approved at scope digest
  `27333d393f8284064aa1df968bea50c56a3869557cfb93f9dc79102d788fbe49`.
  It is local workflow evidence only, not delegated operational or merge
  authority.
- The coordinator-owned exact-`ddd9988e...` pre-review
  `python3 scripts/grok_verify.py --mode pr --no-record` run reported **PASS**.
  The principal dynamic checks were Core/Python unittest `83.888s` with 22
  workers and Factory PostgreSQL exit tests `190.977s`; the current lifecycle
  transition records the exact-head PASS (`state.json:196-211`). No final
  verification receipt exists yet, correctly, because reviews are not all PASS.
- The prior forged-scope blocker is closed: the independent test re-review is
  PASS and reports 12 focused tests, the unchanged exploit rejected, and two
  mutants killed (`evidence/review-test_reviewer.md:67-124`). The independent
  security re-review also closes its original four findings and reports zero
  findings on this SHA (`evidence/review-security_reviewer.md:58-94`). Those
  results do not override the code re-review's distinct local-configuration
  bypass, whose final verdict is FAIL (`evidence/review-code_reviewer.md:67-110`).
- Rollback remains bounded to abandoning the isolated branch before delivery or
  a reviewed revert of the single squash afterward, with no migration, database,
  deployed-policy, secret, or runtime recovery (`rollback.md:7-17`). Release
  observability remains the candidate SHA/tree, scan-scope status, local
  verification/review receipts, and the later external exact-SHA check
  (`release.md:10-16`). No API/event/schema version, data migration, runtime
  rollout, feature flag, or backward-compatibility break is introduced.

### Required closure

1. Repair and regression-test the repository-local `core.worktree` redirection
   path without weakening the sanitized Git environment, replacement-ref
   suppression, bounded diagnostics, or no-follow scanner behavior.
2. Reconcile `tasks.md:15`, preserve the one-direct-child topology, and rerun the
   full verifier plus every routed review on the resulting exact SHA. Record
   final receipts only after all reports are PASS and the worktree is clean.
3. Keep external delivery separate. A later PR still requires explicit operation
   authority and the App-owned policy-epoch Trust CI result for its exact head.

Final local release/readiness verdict for
`cb9af4073ba6c3d515145164d771c75ebdfa3224..ddd9988e4b43fd1502796de42fdcc52170233c61`:
**FAIL with 0 Critical, 2 Important, and 0 Minor findings.**

## Historical final-review appendix — `de23e5da`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `de23e5dac4cfe9fc8d832078ec867ae05e096db1`, reviewed-tree-modified **no**, verdict **FAIL**.
- Important I-2: AC-002, `brief.md`, and `requirements.md` understated the actual source-relative contour. The truthful inventory is the three templates; `.grok-stack/adaptive_grok/{util,verification}.py`; `tests/{test_change_receipts,test_hooks,test_util_fingerprint,test_verification_doctor}.py`; `decisions.md`; `mistakes.md`; and this route package.
- Release readiness remained blocked by the unbudgeted comparison and legacy compatibility findings; the measured repetitive-line series culminated at 12.732s for only 8,000 lines/16 KiB. No later review result is implied by this historical appendix.

## Historical final-review appendix — `f2789117`

- Binding: base `cb9af4073ba6c3d515145164d771c75ebdfa3224`, reviewed HEAD `f278911796e843089cff33e2f8e59a963e79ffd8`, tree `5f3275e0eb81e82a68dd8419d18bd8b7b65fae70`, reviewed-tree-modified **no**, verdict **FAIL** with 0 Critical, 2 Important, and 1 Minor finding.
- Important blockers were the greedy-anchor compatibility false positive and missing mutant-killing proof that both production callers preserve one cumulative budget. The Minor finding was the avoidable full anchor-list copy/zero-cost empty-interval traversal; security review independently passed, but local readiness and closure remained blocked.
