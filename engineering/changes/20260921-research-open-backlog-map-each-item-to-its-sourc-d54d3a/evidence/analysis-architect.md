# Workflow backlog architecture analysis

Research only; route `d54d3afd1c92`; 2026-09-21. All 12 assigned issues inspected. Fetched all remotes successfully. Source observed: research HEAD `1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48`, fetched main `90078959ff816068af374ad42f4bb80fdbaec866`. The relevant workflow, hook, Trust CI and architecture-test files do not differ between those heads. PR mapping uses controller cache `prs.json` (17 open PRs); no live service state was inspected. Issue text is a hypothesis, retained evidence is attributed, and neither is current merge authority. No product edits, full verifier, Docker, deployment, secrets, or external writes were performed.

## Immediate recommendation

Start an independent, narrow #168 correction and recover the already-written #59 candidate instead of recreating it. #160 is more serious but needs an explicit lease/identity design: expiring a live writer by age alone creates a second-writer safety defect. #165 and #54 diagnostics are separable from both. #60 is a source-evidenced closure candidate. #158 already has a substantial branch: finish its missing verification/review, not another implementation. #159 requires an operator-owned decision and deployment and is not a source-only fix.

## Per-issue disposition

### #168 — current, directly reproduced; small independent fix

- Source: `.grok-stack/adaptive_grok/util.py:129-176` filters runtime/cache noise but includes untracked `.qwen/tmp/*`; `tree_fingerprint` hashes every resulting path. Receipts depend on this utility, so broadly exempting agent directories would weaken grants as well as review freshness.
- Safe reproduction executed in a temporary empty Git repository, with bytecode disabled: adding `.qwen/tmp/probe.txt` changed the fingerprint; removing it restored the original. `changed_files` returned precisely that scratch path.
- Minimal correction: recognize narrowly documented **untracked scratch subpaths**, initially `.qwen/tmp/`, while retaining tracked files and all meaningful agent configuration. Do not blanket-ignore `.codex/`, `.claude/`, `.qwen/`, `.agents/`, or `.grok/`. A configurable exclusion system is a larger design and should not be smuggled into this repair.
- Test plan: scratch addition/edit/removal does not stale receipts; tracked scratch-path file and tracked agent config edits still do; normal untracked product files still do; Windows separators handled consistently. Existing broad noise behavior must not be broadened accidentally.
- Dependencies/overlap: `util.py`, fingerprint/receipt tests; semantic relation to #124/PR145 review-scratch isolation, but independent root cause. Medium risk because fingerprint binding is safety-sensitive.
- Exact next action: route a bounded utility change and create the failing temporary-Git regression before changing filtering. No existing dedicated branch identified.

### #160 — current; security-sensitive state/ownership correction

- Source: `state.py:131-165` stores `started_at` but never expires or reconciles active entries. A safe mocked probe returned `general_implementer` active for an entry dated 2020. `_policy_legacy.py:638` allows a same-role second writer (`active and agent_type not in active`). `pre_tool_use.py:228-247` allows all tools after policy import failure and uses different classification/enforcement root fallback expressions.
- Minimal coherent slices: (1) stable agent/session/worktree/route ownership plus atomic admission and bounded heartbeat/lease reconciliation; (2) operator list/release diagnostics with live-owner refusal; (3) fail-closed sensitive policy-import/root handling. Preserve the denial circuit breaker and exact grant bindings.
- Age is not proof of death: TTL-only expiry without heartbeat/fencing can admit a second live writer. Hook admission and start recording currently occur separately; test a concurrent same-role admission race, not merely sequential role checks. Legacy entries need an explicit conservative migration/reconciliation policy.
- Dependencies/overlap: `state.py`, `_policy_legacy.py`, hook start/stop/pretool interfaces, new operator CLI, policy/state/hook tests. Overlaps existing pretool fixes/PR142 routing gates and consumer hook work; isolate writer-ownership from unrelated shell-policy rewrites.
- Exact next action: document owner identity, liveness and atomicity invariants; implement and test with synthetic runtime directories only. No touching consumer active state. High risk; no dedicated branch identified.

### #165 — current diagnostic/continuity gap; original orphan partly recovered

- Source: `scripts/grok_status.py` exposes route/change/agents/evidence gaps only; `change.py:33-87` creates a draft template and runtime pointer; template `evidence/README.md` contains no branch/WIP identity. The #155 package was since recovered and is now represented in PR170, so the incident itself is historical while tooling gap persists.
- Minimal correction: a cheap, read-only package-completeness report for explicit schema blanks/template tokens and a scaffolded branch/change/implementation-state line; expose zero-ahead plus dirty product state as **interruption candidate**, not proof an agent is dead. Prefer named template markers and typed evidence status, not blanket rejection of every `TODO` substring (legitimate quoted evidence can contain it).
- A local uncommitted README is not visible to a fresh clone. Promise same-worktree discoverability; durable remote continuity additionally requires an authorized committed/published WIP checkpoint. Do not claim local template creation solves cross-host crash recovery.
- Dependencies/overlap: status/change/spec/template and Stop/review display; #125/PR141 spec coverage; #54 hygiene diagnostics. Medium risk; no dedicated branch identified.
- Exact next action: add a pure inspection helper tested with valid drafts, incomplete mandatory evidence, quoted placeholders, missing files and zero-ahead dirty branches; only then wire status/Stop. Avoid rerunning the full verifier merely to diagnose scaffolding.

### #167 — current overbroad local verification; bounded profile feature

- Source: AGENTS and adaptive-delivery demand full PR verification for product changes. `verification.py` unconditionally runs architecture/governance then `_python`; `_python` can launch disposable PostgreSQL. The SEO skill's output path is isolated but it does not make those steps path-sensitive.
- Minimal correction: a fail-closed local static-side-project profile selected only when the **entire relevant diff** is within a precise landing path plus explicitly allowed focused tests. Recompute actual Git paths, including staged/unstaged/untracked, renames, deletions and base diff; do not trust the prompt or route label alone. Any verifier/config/runtime/contracts/skill/showcase path returns to full preflight.
- Keep receipt semantics and profile identity explicit, and retain full external exact-SHA Trust CI. A cheap local HTML receipt must never masquerade as the old full verifier result.
- Dependencies/overlap: verification/router/profile configuration, AGENTS/adaptive-delivery/SEO instructions, tests. Overlaps #51/#59 and cancellation PR136 in verification.py; medium/high scope, not a one-line skip.
- Exact next action: agree on path allowlist and focused landing command from existing landing fixtures, then test malicious/mixed diffs. No dedicated implementation branch identified.

### #159 — operational capacity decision, not a demonstrated repository defect

- Current source already has per-worker lease identity and PostgreSQL `FOR UPDATE SKIP LOCKED` (`resources/001_schema.sql:133`). Worker loop is serial within one process. This does not prove multiple deployed workers are safe or installed.
- Issue's durations and 14-stale-PR count are September 20 observations, not refreshed current fleet measurements. Its assertion that #59 is already fixed is false on fetched main; that correction is only on an unpublished local branch.
- Minimal next scope: operator-safe capacity proposal with refreshed queue duration/counts, worker identity/workspace/container/tmp isolation and bounded PostgreSQL concurrency tests. Prefer evaluating a second isolated worker before designing a merge train or changing attestation input semantics.
- Dependencies: #59 read-only lock behavior, #128/PR143 cleanup, #158 adopted-child handling, #155 timing repair/PR170; these must be evaluated before higher concurrency. High operational risk.
- Exact next action: prepare read-only capacity/rollout/rollback evidence for an operator decision; any deployed worker/policy/holdout/image/branch-protection change is separately authorized and outside this research route. No existing source-only branch identified. Do not weaken exact-SHA/base/approval bindings.

### #158 — current adopted-orphan gap; existing implementation candidate

- Existing source contradicts the issue's proposed direct-child root cause: `workspace.py:278-285` waits on success and calls terminating/reaping cleanup on timeouts and every BaseException; sandbox also waits. Missing SIGCHLD handling alone is not proof that normal subprocess children leak. A zombie also does not itself retain ordinary process file locks after exit; do not perpetuate that issue claim without separate evidence.
- Remote branch `origin/fix/trust-ci-child-reaping` at `7e0044f2` contains implementation commit `1525ed93`, new `reap.py`, guarded spawn sites, worker/lease safe-boundary sweeps and 425 lines of tests. Package: `engineering/changes/20260920-fix-issue-158-the-long-lived-adaptive-trust-ci-w-9f3462/`.
- Candidate evidence attributes leak to the deployed worker being namespace PID1 and adopting orphaned git helpers. It uses a guarded loop-boundary sweep instead of asynchronous SIGCHLD `waitpid(-1)`, which could steal a live Popen status and fabricate success. The exact git subcommand is explicitly unproven.
- Critical completeness discrepancy: package state says `ready`, but `evidence/reaping-arms.md` section 5 explicitly says full verifier and selected reviews were **not run**, no receipt claimed, real git-fetch orphan not exercised and post-deploy checks pending. Do not promote the status label to readiness. No matching open PR appears in cached inventory.
- Dependencies/overlap: workspace/sandbox/lease/worker, process tests; cancellation classification #103/#132/PR132 and existing zombie-process-group work. High risk because exit statuses decide trust.
- Exact next action: continue that branch, independently audit all spawn sites including dependencies and race windows, reconcile package state to real evidence, then run its route verification/reviews and publish only with exact authority. Live rollout and zero-zombie observation remain separate. No new implementation here.

### #51 — current coverage gap; source and deployment halves

- Source: `verification.py:986-1024` selects only `contracts,state,migrations,service` factory modules and skips the only full disposable tier under `repository-sandbox`; no delivery discovery is wired into `_python`. The issue's historical module/test totals should not be treated as current counts.
- Minimal source correction: add locked-dependency, DB-free full factory discovery plus delivery discovery with correct import roots; explicitly name database skips and fail on unexpected omissions. Retain a separate mandatory actual-DB tier in the environment capable of supplying it. Prove a deliberately failing test in a previously omitted module is detected.
- Running a new command in repository source does not install dependencies into deployed images or make an external policy command mandatory. Inventory image dependencies and split externally owned rollout work; avoid treating absent DB tests as passed.
- Dependencies/overlap: verification.py and tests, factory dependency lock/run harness (#59), external runner image/policy, #159 capacity. Medium/high risk; no dedicated branch found.
- Exact next action: cheap matrix audit with mocked command execution and dependency/import probes; implement DB-free discovery in a source PR, separately propose required external image/policy update and database tier.

### #62 — historical PR failure superseded; residual quota concern

- PROJECT_STATE records PR33 closed unmerged, then retaken by merged PR113 (`35cbbe0f`) with capability-selected engine and sequential fallback when pytest/xdist are unavailable. The original seven sandbox failures are not established on current source. Current source has no default root `.grok-test-runner.json`, so consumer parallelism remains opt-in.
- Residual source gap: `python_test_runner.py:71-73` auto count uses affinity/host count and caps at 28; it does not inspect cgroup CPU quota. A mocked affinity of 22 yields 22 workers regardless of a hypothetical 2-CPU quota. That is a concrete algorithm observation, not a reproduced current sandbox failure.
- Dependencies/overlap: runner and tests; Windows fallback PR135 touches same engine area. Bounded command-output diagnostics are a distinct Trust CI observability concern, not a prerequisite for worker selection.
- Exact next action: disposition the obsolete PR33 failure with PR113 evidence; if retaining issue, narrow it to auto quota/PID-aware selection with fixture-based cgroup tests, then a separately authorized exact sandbox reproduction. Do not rebase/revive the historical PR33 branch. Medium risk.

### #60 — already fixed in main; no implementation needed

- Main `tests/test_architecture_model.py:1320-1333` compares exact declared contract ID/path sets, compares record count with declared ID count, and uses only an additive-friendly floor of 41. The old equality to literal 39 is gone.
- Delivered through PR77, commit `1a8c89170349fcc2597be0a1665b0e0a31d124e0` (derived inventory hardening). Direct `git show origin/main:...` confirms the corrected assertions; no full test run was needed for this source-identification research.
- Exact next action: prepare closure evidence linking that commit and lines. External issue closure is a separate write. Risk low; avoid changing the floor merely because the old issue remains open.

### #59 — current; recover local candidate, coordinate harness owner

- Main `factory/tests/run_disposable_exit.py:181` still uses `["uv", "run", "--project", "factory"]`; all three calls share it. No `uv-lock-drift` named check exists. Source-stability details do not identify moved paths.
- Existing local-only branch `fix/issue59-frozen-uv-lock` at `aa7dbcdb7e645666e629816aea59f9b89e647494` adds `--locked`, offline `uv lock --check`, tests and a change package. No remote contains that commit and cached open PRs contain no equivalent branch. This is candidate evidence, not delivered behavior.
- Minimal correction: port/review the useful candidate onto current source, put cheap lock checking before the costly disposable run, and retain no-mutation assertions for both matching and drifted manifests. `--locked` rejects drift; substituting `--frozen` would silently accept it and misses the issue's goal. Offline cache failures need honest diagnostics rather than being mislabeled manifest drift.
- Dependencies/overlap: `verification.py`, disposable runner and tests; PR143/#128 changes the same harness; #51/#167 also change verification.py. A changed-path stability diagnostic is useful but can be a separate bounded enhancement.
- Exact next action: route candidate recovery and inspect the existing four regression tests; use temporary copies and no Docker for initial lock behavior reproduction, then appropriate final route verification. Medium risk.

### #84 — current append-preservation gap; generated projection only partly covered

- Governance already has pure projection rendering and CLI `verify-projections`, but the normal governance verifier binds registries/evidence rather than enforcing preservation of handwritten shared-memory entries. Searches found no append-only/base-entry preservation gate. Projection equality alone cannot detect lost human entries outside the generated block.
- Minimal correction: compare preserved handwritten sections/entry identities against the exact trusted PR base, separately verify the generated region. Counting headings alone misses one deletion plus one insertion. Do not require an arbitrary local `origin/main` pointer as authority; stale/absent refs and legitimate generated-block refreshes need explicit behavior.
- Do not migrate every historical entry into one-file-per-entry storage just to fix a deletion guard; that is a larger coordinated documentation model change.
- Dependencies/overlap: governance/verification and tests plus shared-memory docs; every branch appends these files, making large rewrites hazardous. Medium risk.
- Exact next action: fixture tests for stale whole-file rewrite, same-count replacement, normal append, generated-only refresh and missing trustworthy base; add a pure nonmutating gate with actionable deleted-entry details. No dedicated branch found.

### #54 — current local hygiene/visibility problem, with separate operational cleanup

- Safe current Git metadata probe: 140 linked worktrees, 250 commits reachable from local branches but no origin remote ref, 5 stashes, 18 non-main branches tracking origin/main, zero gone-upstream refs. Historical 350/46/4 counts are obsolete. No worktree contents or stashes were read, modified or cleaned.
- `doctor.py` checks installed files/config/toolchain/manifest but has no Git hygiene report. Counted local-only commits are not proven unique valuable work: some may be squash-equivalent to delivered content.
- Minimal product scope: bounded read-only `grok_doctor`/audit summaries for dirty worktrees, local-only refs, protected/shared upstreams, gone refs and stash count, with explicit unknown/unreadable states. It must not read stash content or expose untracked secret contents.
- Operational backup/push, upstream rewiring, stash disposition and worktree removal are distinct exact-resource actions. Never auto-push all local-only branches or remove merged worktrees with uncommitted evidence.
- Dependencies/overlap: doctor/status, Git helpers and synthetic multi-worktree tests; #165 interruption candidate signals. Medium risk for diagnostics, high for cleanup.
- Exact next action: route read-only diagnostic enhancement and draft an inventory-based operator plan; keep preservation and cleanup outside implementation.

## Sequencing and shared-file controls

1. Source-evidence disposition: #60 and historical part of #62; no product verification wave for issue bookkeeping alone.
2. Independent small source work: #168 utility; #165 status/completeness; #54 doctor diagnostics. Use one owner per separately routed branch and coordinate shared status/helpers.
3. Verification/harness lane: recover #59 with PR143 owner, then #51 coverage; only then introduce #167 narrow profiles. These all overlap verification.py; do not parallel-edit or treat one green old-head receipt as evidence for another.
4. Ownership safety lane: #160 after identity/lease/fencing design, independent of verifier changes but overlapping hook branches.
5. Existing Trust CI candidate lane: #158 with actual missing verification/reviews and #132 compatibility; #159 remains operator capacity decision after candidate/isolation readiness.
6. Shared-memory guard #84 can be a bounded source PR, with aggregate docs rewrites deferred.

No conclusion above asserts current external checks, signed approvals, deployment success or merge eligibility. Historical test counts and retained candidate reports were not rerun. The research report is the only file written by this analysis agent.
