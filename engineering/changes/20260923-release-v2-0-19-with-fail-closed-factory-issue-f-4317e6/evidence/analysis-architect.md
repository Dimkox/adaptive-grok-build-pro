# Architect analysis — v2.0.19 fail-closed factory bugfix integration

Route: `4317e673390b`  
Worktree: `/tmp/agbp-release-factory-bugfixes`  
Base/HEAD inspected: `130ce4a42d9f9bbd1b56772d40b19ae530283205` (`origin/main`)  
Requested issue scope: `#35`, `#36`, `#39`, `#48`, `#73`, `#167` only  
Role: route-selected read-only `architect`

## Architectural ruling

The smallest defensible v2.0.19 integration boundary is a source-only bugfix train based on the
exact current `origin/main`, with one independently reviewable commit per accepted issue candidate,
followed by a separate release-metadata commit only after the combined bugfix tree passes the full
route gate. It must not import M8/DEV work, runtime activation, provider calls, deployment changes,
Trust CI policy/holdout changes, historical evidence rewrites, or unrelated cleanup.

The six dirty candidate worktrees are not yet collectively eligible for that train. They share the
same base, but their durable packages and implementations disagree on ownership and completion:

- #36 has no product change and is explicitly deferred to #186.
- #35 and #39 analyses classify the filed defects as external/unowned, while their worktrees now
  contain newly scoped repository-verifier implementations.
- #48 is an explicitly bounded repository-owned smoke hardening follow-up, not closure of all
  behavior in filed issue #48.
- #73's package says implementation is blocked on a security scope/design gate, while its worktree
  changes the live local-grant field contract.
- #167 is large and cross-cuts verifier selection, Git inventory, workflow command validation, and
  workflow documentation; its package says final full verification is stale/pending.

Therefore v2.0.19 must not claim all six filed issues fixed merely by copying these worktrees. The
write owner must first reconcile each candidate to the acceptance boundary below. A no-product
disposition may be retained as evidence, but it is not a release fix and must not automatically
close its issue.

## Release boundary and sequence

1. Freeze the base at `130ce4a42d9f9bbd1b56772d40b19ae530283205`; if `origin/main` advances,
   rebase/reconstruct each accepted candidate and repeat all evidence on the new exact base.
2. Import only the product/test paths explicitly accepted below. Keep each issue as a distinct
   commit so it can be reviewed or reverted independently.
3. Resolve shared verifier code in this order: #35, #39, then #167. This is a dependency/order rule,
   not permission to combine their commits. Re-run each issue's focused tests after every later
   verifier edit.
4. Integrate #48 and #73 as separate commits because they touch independent trust/safety seams.
   #73 requires an explicit package/gate reconciliation before import.
5. Do not create an empty "fix #36" commit. Either obtain and implement the exact repository-owned
   recorder seam with RED/GREEN evidence, or leave #36 out of the release-fix/closure claims.
6. Run the full `python3 scripts/grok_verify.py --mode pr` against the combined product tree, then
   the route-selected code and test reviews. Focused issue evidence is necessary but not sufficient.
7. Only after the bugfix tree is frozen and verified, update `VERSION`, README/current-state release
   text, release records, package artifact/sidecar, and other established v2.0.19 metadata in a
   distinct release commit. The artifact must be generated from the exact verified source tree.
8. Deliver by PR and require the App-owned policy-epoch check on the exact final head. Local receipts,
   issue reviews, and focused mode never replace that merge authority.

## Candidate acceptance and invariants

### Issue #35 — independent shell syntax parsing

Candidate product paths:

- `.grok-stack/adaptive_grok/verification.py`
- `tests/test_verification_doctor.py`

Acceptance:

- Every selected existing `.sh` target is passed to its own `bash -n <one-path>` process.
- A valid first script cannot mask a syntax error in a later selected script; the result is `fail`
  and identifies the later path.
- Missing Bash with applicable targets fails closed.
- The check runs only when the trusted changed-file inventory includes an applicable shell target.
- Test the successful multi-file case, unavailable-Bash case, empty/direct-helper invocation, and
  invocation cardinality in addition to the existing later-file regression.

Invariants:

- Never construct `bash -n` with multiple file operands.
- Do not present Bash parsing as proof of POSIX `/bin/sh` compatibility.
- Do not expand this commit into Trust CI scripts, deploy behavior, or a repository-wide shell
  policy not stated by the acceptance contract.
- Reconcile the package's earlier "external/no-op" disposition with the later local implementation
  before import; package text must describe one final outcome.

### Issue #36 — real recorder exit status

Current candidate: no product diff; package defers the missing owner to #186.

Acceptance required for release inclusion:

- Name the repository-owned recorder path and reproduce the `if ! cmd; then code=$?` false-success
  behavior there.
- Preserve exact success (`0`), command failure (original nonzero status), and launch/not-found
  failure as distinct outcomes, with diagnostics.
- Add a failing regression before the repair and verify Bash/Dash behavior where both are claimed.

Invariants:

- Never read `$?` after shell negation as the wrapped command's status.
- Do not invent a recorder in unrelated Python verifier code.
- With the current no-op candidate, #36 is excluded from product/release-fix and automatic issue
  closure claims. Evidence-only files may be retained only as non-product historical context.

### Issue #39 — bounded lint discovery

Candidate product paths:

- `.grok-stack/adaptive_grok/verification.py`
- `tests/test_verification_doctor.py`

Acceptance for the repository-local re-scope:

- `fast` lint receives only existing changed Python files under explicitly owned quality roots.
- `pr`/release deep lint derives files from tracked repository inventory plus explicit changed files,
  never from root `.` or unconstrained recursive discovery.
- Out-of-root, deleted, generated, package, engineering, runtime, and arbitrary untracked scratch
  paths cannot enter lint argv.
- Ruff and Bandit reports state their selected scope; applicable failures remain failures.
- Git inventory failure must fail closed or use a demonstrably bounded fallback. A broad fallback to
  directories that reintroduces untracked recursive discovery is not acceptable.
- Preserve Bandit's intended recursion/file semantics and prove both tools still inspect nested
  owned files; the removal of `-r` needs executable compatibility evidence.

Invariants:

- Do not add Node/ESLint dependencies or claim this local Python change repairs an external
  JavaScript `eslint .` owner.
- Do not silently reduce full PR/release lint coverage.
- Reconcile the package's no-op/external disposition with this later local implementation. If the
  filed issue remains external, describe this as a separately scoped local fix and do not close #39.

### Issue #48 — fail-closed Trust CI smoke observations

Candidate product/test paths:

- `trust-ci/scripts/smoke.sh`
- `trust-ci/tests/test_smoke.py` (currently untracked and therefore must be explicitly imported)
- `decisions.md` and `mistakes.md` only where the entries directly document this fix

Acceptance:

- Required command resolution accepts only executable non-directories and fails with status 127
  when unavailable; tests cover empty, malformed, and non-executable path candidates.
- Health, readiness, metrics, and rendered Compose output are captured, required non-empty, and
  matched without a live producer piped to early-exiting quiet grep.
- Existing endpoints, bearer-token header, isolated Docker host assertion, forbidden host-socket
  rejection, migration-status command, Compose `ps`, and final PASS line remain intact.
- Disposable runtime tests execute the real script with sentinel fake tools and prove both valid
  success and each fail-closed observation path.

Invariants:

- No live service, Docker daemon, credential, deployment, policy, holdout, or GitHub Actions change.
- Never read secrets; preserve token handling through the existing environment variable.
- The candidate fixes only the repository-owned smoke seam. The external `VAR=x break`, `grep -lf`,
  and original PATH guard remain tracked by #186; do not over-claim issue #48 closure.

### Issue #73 — neutral current grant binding field

Candidate product/test paths:

- `.grok-stack/adaptive_grok/state.py`
- `tests/test_policy.py`
- `tests/test_history.py`

Acceptance, only after gate/package reconciliation:

- Newly emitted local grants use `grant_binding_digest` and no
  `authorization_tree_fingerprint`-shaped key.
- Existing grants using `tree_fingerprint` remain readable during the compatibility window.
- A record containing both new and legacy binding fields fails closed, as does a mismatched digest.
- Every current producer/consumer/schema/documentation reference is inventoried and tested; no
  grant-validity path may bypass repository, route, change, head, action/resource, TTL, or tree
  binding checks.
- The two archived `historical-qwen-probe.json` files remain byte-identical; their fixed digest
  regression must pass.

Invariants:

- Never rewrite historical evidence, suppress generic 64-hex values, touch private keys/trust
  stores, or claim local tests control GitGuardian's external detector.
- Compatibility must be fail closed: conflicting fields are invalid, absent binding is invalid,
  and legacy support must not weaken any other grant binding.
- This is a live authorization-contract change, despite being local-only. The issue package currently
  names a `scope_and_design_approval` gate while the release route lists no human gate; the coordinator
  must obtain/record the required ruling or explicitly cancel this implementation. Do not infer it.

### Issue #167 — explicit focused static-landing verification

Candidate product/documentation/test paths:

- `.grok-stack/adaptive_grok/util.py`
- `.grok-stack/adaptive_grok/verification.py`
- `.grok-stack/adaptive_grok/workflow_artifacts.py`
- `scripts/grok_verify.py`
- `tests/test_util_fingerprint.py`
- `tests/test_verification_doctor.py`
- `tests/test_workflow_artifacts.py`
- `AGENTS.md` and `.agents/skills/adaptive-delivery/SKILL.md`
- directly relevant `decisions.md`/`mistakes.md` entries

Acceptance:

- Focused mode is explicit; ordinary `--mode pr` always remains the full path and never auto-downgrades.
- Eligibility requires one trusted complete comparison inventory containing exactly one
  `side-projects/seo-landings/<landing>/**` directory and exactly one matching focused unittest
  contract. Multiple/missing/mismatched tests or landing directories fail closed.
- Unknown, malformed, traversal/control-character, deleted, renamed, copied, showcase, skill,
  runtime, factory, contract, Trust CI, package, architecture, or workflow paths reject focused
  execution before its subprocess runs.
- Git status/range provenance is complete and trusted; ambiguous/missing bases and malformed status
  records fail closed.
- Focused execution includes git-diff integrity, scope-selection evidence, the exact named landing
  contract, and source-stability. JSON output identifies checked/skipped scope.
- Workflow artifacts allowlist only the exact focused command and reject arbitrary extra flags.
- The current final combined tree passes full PR verification; #167's focused-mode evidence cannot
  self-qualify this release.

Invariants:

- App-owned exact-SHA Trust CI remains merge authority.
- Full PR behavior and its checks remain backward compatible.
- No landing content, SEO skill/showcase, runtime, contract, Trust CI, package, architecture, factory,
  PostgreSQL, M8, or DEV behavior is changed by this issue.
- Keep this commit independently revertible despite its size. If it cannot be reviewed as one
  coherent vertical change, split internal commits under the same issue without interleaving other
  issues.

## Conflict and integration risks

### Direct textual conflicts

- #35, #39, and #167 all modify `.grok-stack/adaptive_grok/verification.py` and
  `tests/test_verification_doctor.py`. Blind patch application or cherry-picking dirty worktrees is
  unsafe. #167 changes the verification/range machinery extensively (about 593 verifier lines and
  341 verifier-test lines), so it has the highest overwrite/regression risk.
- #167 also changes `decisions.md` and `mistakes.md`, overlapping #48's learning-log edits. Retain
  only non-duplicative, still-true entries and preserve the three-sentence decision rule.
- `trust-ci/tests/test_smoke.py` is untracked in the #48 candidate and can be accidentally omitted by
  a diff limited to tracked files.

### Semantic conflicts

- #39 changes lint selection based on changed-file inventory; #167 changes how that inventory and
  status provenance are derived. The merged behavior must prove that full PR lint remains complete
  and focused mode cannot feed a reduced inventory into ordinary PR verification.
- #35 registers a new check based on changed `.sh` paths; #167's inventory/range changes can alter
  when it runs. Test shell changes in worktree, route-base range, and local PR-target range.
- #73 changes a current approval/grant contract even though its package analysis recommends no
  current producer change and names a gate. This is a source-of-truth conflict, not routine merge
  friction.
- #48's command resolver adds fallback search directories after an explicit `TRUST_CI_TOOL_PATHS`
  miss. Verify this is intentional: if the variable is meant to be an exclusive hermetic allowlist,
  falling back to ambient/default paths violates fail-closed selection.

### Scope/closure conflicts

- #35, #36, #39, and #48 were initially classified as external-owner/target issues. Local analogous
  repairs do not by themselves prove the original external defects fixed.
- #36 cannot be represented as a product fix at all in the current candidate set.
- #48 explicitly leaves three reported behaviors to #186.
- #73 local compatibility cannot clear a historical external GitGuardian finding from Git history.
- Release notes and PR closure keywords must distinguish "repository-owned bounded fix" from
  "original issue fully fixed". Do not use automatic closure for an issue whose stated acceptance
  remains deferred or external.

### Evidence freshness risks

- The candidate implementations are uncommitted and their packages are untracked; branch refs still
  point at the common base. Branch names alone contain no importable fix commit.
- #35/#39 packages contain contradictory outcome text as writers progressed. #73 package gate text
  contradicts its product diff. Normalize durable package truth before relying on it.
- #167 records passing focused reviews but also states full PR verification is stale after later
  changes. All candidate receipts become stale when combined into the release tree.
- The release worktree currently contains only the untracked release package; no product fix has yet
  been integrated. Verification/reviews must bind to the eventual combined fingerprint.

## Backward compatibility and fail-closed release invariants

- Existing `--mode pr` behavior remains full verification; focused execution is opt-in and rejects
  uncertainty.
- Missing tools, missing/empty observations, ambiguous Git provenance, conflicting grant fields,
  and applicable syntax/lint failures cannot become pass results.
- Existing local grants remain compatible only through a narrowly tested legacy read path; no scope,
  action, resource, TTL, head, route, change, repository, or fingerprint binding is relaxed.
- Existing APIs/events/schemas are unchanged unless #73's grant record is treated as an explicit
  versioned compatibility contract. No network/event producer or consumer is added.
- No database migration, backfill, provider operation, deployment, runtime activation, M8 cohort,
  DEV work, or external-system write is part of v2.0.19 preparation.
- Published v2.0.18 and prior tags/artifacts remain immutable. v2.0.19 metadata/artifacts are created
  only from the verified final tree and never overwrite a prior artifact.
- Rollback is issue-granular commit reversion before release; after publication, use a forward
  patch/new release rather than retagging or rebuilding the immutable release.

## Go/no-go recommendation

Current recommendation: **NO-GO for release integration as a six-fixed-issue candidate**.

Proceed to implementation only after the coordinator records final ownership/disposition for #35,
#36, #39, and #48; reconciles the #73 gate and contract decision; and gives the single write owner
the exact accepted path manifest. A valid reduced release may contain only candidates that satisfy
their acceptance criteria, but its notes and closure actions must omit unresolved issue numbers.

Once reconciled, go requires: independently reviewable issue commits; no out-of-scope paths; focused
RED/GREEN evidence per issue; full combined PR verification; fresh code/test review on the combined
tree; release metadata/artifact generation after verification; and the exact-head App-owned Trust CI
success before merge. This report is architecture evidence only and is not verification, approval,
merge authority, or authorization for release publication.

reviewed-tree-modified: no product files; this requested analysis report is the only authored file.
