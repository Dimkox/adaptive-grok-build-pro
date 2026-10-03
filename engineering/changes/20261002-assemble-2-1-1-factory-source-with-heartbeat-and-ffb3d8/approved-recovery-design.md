# v2.1.1 Dirty-Worktree Recovery Design

**Status:** owner-approved recovery scope; design for later implementation  
**Date:** 2026-10-01  
**Release baseline:** `81cb7c21a4c4a7e098fe2947a55b6ea8d58e7f22` (`feature/factory-v15-unified-rc`, version `2.1.0`)  
**Target:** a successor `2.1.1` release assembled only from independently reviewed successor PRs  

## 1. Intent and authority

The owner asked for read-only analysis of every dirty worktree and for worthwhile unfinished changes to be planned for `2.1.1`. This design records the resulting recovery queue. It does not authorize cleanup, deletion, reset, merge, tag, publication, deployment, production mutation, or reuse of old approvals.

Release `2.1.0` is independent and must not wait for this work. Its exact source RC is the baseline above. Every `2.1.1` implementation contour starts in a new worktree from the released/merged `2.1.0` lineage; if the final merged `2.1.0` commit differs from the RC because of an artifact-only release child or merge topology, the implementer must prove the source-tree relationship and use the actual protected-branch base without silently changing the recovered behavior.

The recovery method is **reconstruction**, not branch integration. The old dirty worktrees are read-only source material. No contour may cherry-pick a historical aggregate commit, copy an entire dirty tree, import its workflow receipts as current authority, or clean the source worktree after extracting a candidate. Product changes are re-applied path-by-path with new tests and new evidence against the `2.1.0` baseline.

The previously approved platform decision remains in force: U4/macOS is excluded. Nothing in this recovery queue restores a macOS requirement, claims Apple qualification, or broadens the `2.1.0` U0–U3/U5–U7 release scope.

## 2. Audit disposition: all 31 dirty worktrees

Disposition meanings:

- **Reconstruct** — recover only the named outcome in a clean successor contour.
- **Defer** — preserve the worktree untouched; it is outside `2.1.1`.
- **Landed/obsolete** — no product recovery; the useful behavior is already present or the draft has been superseded.
- **Archive** — preserve for later forensic comparison; do not integrate it.

| # | Dirty worktree / branch | Disposition | `2.1.1` ruling |
|---:|---|---|---|
| 1 | `adaptive-grok-build-pro-state-reconcile` / `integration/m1-m3-aggregate` | Archive | Duplicate aggregate; discard as an integration source, preserve bytes. |
| 2 | `adaptive-grok-build-pro-project-completion` / `integration/project-code-completion` | Archive | Reconstruct selected unfinished outcomes only in a later scope; none belongs to the approved `2.1.1` core. |
| 3 | `adaptive-grok-build-pro-evidence` / `feat/m7-durable-evidence-lookup` | Reconstruct | M7.1 durable lookup, after four review repairs and migration renumbering; exclude historical evidence bulk. |
| 4 | `adaptive-grok-build-pro-m3` / `milestone/m3-controlled-knowledge-debt` | Reconstruct | Four-file governance/Git/filesystem hardening only. |
| 5 | `adaptive-grok-build-pro-workflow-adapters` / `feature/workflow-artifact-adapters` | Landed/obsolete | No recovery. |
| 6 | `adaptive-grok-build-pro-production-gate-task1` / `policy/promotion-task1-isolated` | Defer | Incomplete production-promotion prototype. |
| 7 | repository root / `feature/winston-wolfe-landing-v2` | Defer | Mid-cherry-pick; BB exact content already landed. Preserve current staged/user state; defer committed landing/provenance/lease slices. |
| 8 | `adaptive-grok-build-pro-truth-observer` / `feature/external-truth-projection` | Defer | Old base and failed reviews; truth-observer is not a `2.1.1` candidate. |
| 9 | `adaptive-grok-build-pro-trust-source-completion` / `integration/trust-ci-source-completion` | Reconstruct | Read-only current-authority endpoint/API/store/OpenAPI only; reject stale policy, CLI, worker, settings, example, and README changes. |
| 10 | `adaptive-grok-build-pro-d5-m8` / `feat/d5-m8-m9-qualification-accounting` | Defer | M8/M9 negative-spec and blocker accounting. |
| 11 | `adaptive-grok-build-cancel` / `fix/verify-cancel-evidence` | Reconstruct | Combine issue #118/#119 cancellation/lifecycle behavior with recovery and #226. |
| 12 | `adaptive-grok-build-pro-verification-recovery` / `fix/verification-recovery` | Reconstruct | Combine with the same verifier contour; do not ship separately. |
| 13 | `adaptive-grok-build-router` / `fix/router-release-intent-masking` | Reconstruct | Dedicated issue #123 PR. |
| 14 | `adaptive-grok-build-pro-m2` / `milestone/m2-executable-architecture` | Landed/obsolete | Superseded zombie behavior; no recovery. |
| 15 | `adaptive-grok-build-arch50` / `fix/issue-50-architecture-model-gaps` | Reconstruct | Dedicated architecture diagnostic/preflight PR. |
| 16 | `adaptive-grok-build-issue226` / `fix/issue-226-timeout-receipt-durability` | Reconstruct | Port only timeout/receipt durability commits; exclude stacked issue #227 ancestry. |
| 17 | `adaptive-grok-build-pro-lazy-cli` / `fix/trust-ci-lazy-cli-imports` | Landed/obsolete | No recovery. |
| 18 | `adaptive-grok-build-pro-qwen-grok-failover-evidence` / `docs/provider-failover-evidence` | Landed/obsolete | Historical/stale evidence only. |
| 19 | `adaptive-grok-build-repo157` / `fix/issue-157-repo-classifier` | Reconstruct | Dedicated repository classifier PR. |
| 20 | `adaptive-grok-build-pro-factory-runtime` / `feat/factory-live-task-runtime` | Landed/obsolete | Obsolete planning tree. |
| 21 | `adaptive-grok-build-pro-m4` / `feat/m4-durable-factory-control-plane` | Landed/obsolete | Old package/obsolete candidate. |
| 22 | `adaptive-grok-build-anyof` / `fix/fitness-anyof-composition-subset` | Landed/obsolete | Landed through #104/#133. |
| 23 | `adaptive-grok-build-pilot-ru` / `feature/pilot-russian-audit` | Defer | Incomplete pilot scaffold. |
| 24 | `adaptive-grok-build-pro-l5-env` / `feat/factory-env-landing-composition` | Landed/obsolete | Superseded; includes generated `egg-info` debris. |
| 25 | `adaptive-grok-build-pro-l5-split-g` / `feat/l5-split-g-backup-runtime` | Landed/obsolete | Obsolete scaffold. |
| 26 | `adaptive-grok-build-pro-token-accounting` / `feat/token-cache-cost-accounting` | Landed/obsolete | Landed in #46. |
| 27 | `adaptive-grok-build-pro-trust-ci-repo-profiles` / `feat/trust-ci-repository-profiles` | Landed/obsolete | Landed in #13; remaining `egg-info` is not source. |
| 28 | `adaptive-grok-build-pro-trust-ci-zombie` / `fix/trust-ci-zombie-process-group` | Landed/obsolete | Obsolete draft. |
| 29 | `adaptive-grok-build-qwen-cleanup` / `chore/qwen-issue-wave-cleanup-20260925` | Landed/obsolete | Stale audit only. |
| 30 | `adaptive-grok-build-rel19` / `feature/v2.0.19-release-sync` | Landed/obsolete | Historical inventory only. |
| 31 | `adaptive-grok-build-router12` / `feat/router-12-analysis-capacity` | Defer | Paused router redesign; not a small recovery. |

All 31 remain physically untouched. “Archive” and “landed/obsolete” are planning dispositions, not deletion instructions.

## 3. Delivery topology

Seven PR contours are approved. Each has its own route, clean branch/worktree, single write owner, change package, focused tests, full route-selected verification, independent reviews, and exact-head Trust CI check. A failure in one contour does not permit bundling it into another.

```text
released/merged 2.1.0 lineage (source RC 81cb7c21)
  ├─ A: verifier recovery + cancellation + #226
  ├─ B: #123 router intent precedence
  ├─ C: #157 repository classifier
  ├─ D: #50 architecture preflight
  ├─ E: M3 governance/Git/filesystem hardening
  ├─ F: M7.1 durable lookup (new migration after current tip)
  └─ G: Trust CI read-only current-authority endpoint

independently merged accepted contours
  └─ version/state/README/release aggregate → 2.1.1 candidate
```

Contours B–G are logically independent and may be implemented and reviewed in parallel in isolated worktrees. Contour A is internally ordered because #226 must preserve the final verdict produced by the recovered lifecycle and cancellation path. Contour F must resolve its migration number against the merge base immediately before implementation and again after any rebase. The final `2.1.1` release aggregate is serialized after all selected contours merge; a contour that is not accepted is omitted with an explicit release note rather than force-integrated.

There are no cross-contour source dependencies. If two contours touch the same shared documentation, `decisions.md`, `mistakes.md`, or state files, their product PRs keep only contour-local truth and the final release aggregate reconciles current-state prose. This avoids using shared paperwork as an artificial code dependency.

## 4. Candidate requirements

### A. Verifier recovery, cancellation, and issue #226

Source material: worktrees 11, 12, and the issue-#226-only commits from worktree 16.

1. The verifier must preserve and emit its terminal product verdict and structured report when receipt validation, receipt persistence, report publication, cleanup, or cancellation handling fails after tests have run.
2. Cancellation must terminate/reap the owned test process tree within bounded deadlines, distinguish requested cancellation from timeout and test failure, and retain the last known check/result metadata.
3. Partial or malformed runner output must fail closed without replacing a more specific already-established failure with a generic receipt exception.
4. Receipt writes must be atomic/durable and bound to the exact head, tree fingerprint, selected profile, check inventory, and terminal state. Timeout or interruption during receipt publication must not produce a valid-looking partial receipt.
5. Repeated cancellation/cleanup must be idempotent; unrelated processes and worktrees must never be targeted.
6. Only the issue #226 delta is reconstructed from its stacked branch. No commit, behavior, grant-boundary change, or evidence attributable to issue #227 is imported.
7. Required negative controls cover cancellation before spawn, during a running child, after result computation, and during receipt publication; child ignoring graceful termination; malformed/truncated report; receipt write/rename/fsync failure; and a prior failing verdict followed by cleanup failure.

Expected product surface is limited to the verifier/runner implementation and its tests (for example `.grok-stack/adaptive_grok/python_test_runner.py`, `.grok-stack/adaptive_grok/verification.py`, `scripts/grok_verify.py`, `tests/test_python_test_runner.py`, `tests/test_verification_doctor.py`, and receipt tests). Historical change packages and reviews are inputs, not candidate files.

### B. Issue #123: router intent precedence

1. Explicit release/deploy/publish intent must not be masked by lower-risk pull-request or review vocabulary in the same prompt.
2. Routing precedence must be deterministic, documented by tests, and preserve existing behavior for prompts that contain only PR/review intent.
3. Mixed-language, negated, quoted, and historical mentions must not accidentally authorize an operational route.
4. The selected route still carries the existing human gates and does not create operational authority.

Limit the contour to the router and its contract tests; reconstruct the behavior from worktree 13 rather than copying its evidence directory.

### C. Issue #157: repository classifier

1. Separate “detected signal” from “confirmed repository language”; one weak or masked signal cannot suppress disclosure of another.
2. Swift/package detection is bounded, deterministic, and does not follow symlinks outside the repository or accept a symlinked manifest as proof.
3. Source scanning has explicit file/byte/depth bounds and reports truncation/unknown status instead of silently classifying incomplete input.
4. Conflicting manifests, generated/vendor-only sources, unreadable paths, case variants, and an empty repository have explicit outcomes.
5. Existing supported language results remain backward compatible unless stronger current evidence requires an additive disclosure.

Expected product surface: `.grok-stack/adaptive_grok/repo.py` and focused language-disclosure/classifier tests only.

### D. Issue #50: exact architecture diagnostic preflight

1. Architecture model loading must reject malformed path shapes, unloadable referenced models, and line-skipping cases before downstream validation can turn them into cascaded or misleading findings.
2. Diagnostics identify the exact source file/location and preserve the document's line-count semantics.
3. PR verification invokes the architecture preflight mandatorily when its inputs can affect architecture results; it must not be reported as passed when skipped or unloadable.
4. Local filesystem aliases, symlinks, traversal, duplicate normalized paths, missing files, and malformed YAML/JSON fail closed with bounded diagnostics.
5. Existing valid architecture models and generated-view checks remain compatible.

Reconstruct the minimal product diff and current tests from worktree 15; do not import its historical evidence commits as fresh evidence.

### E. M3 governance/Git/filesystem hardening

This contour is exactly four product/test files: `.grok-stack/adaptive_grok/architecture_diff.py`, `.grok-stack/adaptive_grok/governance.py`, `scripts/grok_governance.py`, and `tests/test_governance.py`.

1. Resolve and validate the worktree root explicitly; all Git reads use a bounded environment and explicit `--git-dir`/`--work-tree` relationship rather than ambient repository discovery.
2. Bind base/head to existing commit objects of the repository's supported object format; reject missing, abbreviated, wrong-kind, replacement-object, or unsupported-format identities.
3. Read committed inputs from exact Git objects without executing clean/smudge filters, entering gitlinks, or trusting mutable worktree bytes.
4. For required working-tree projections, open regular non-symlink files, pin identity/content, enforce a shared unique-byte budget, and verify no mutation before publication.
5. Reject traversal, symlink swaps, FIFOs/devices, oversized inputs, mutation races, and mismatches between explicit head and working-tree governance bytes.
6. Repository-authored claims never confer external rule authority. Existing authority and fail-closed publication semantics remain intact.
7. The command-line interface keeps compatible successful output while surfacing bounded `git`/`io` error codes for the new refusals.

### F. M7.1 durable evidence lookup

Source material: worktree 3, but its historical `019_m7_durable_evidence.sql` collides with already-shipped migrations 019–025. On the current RC, the reconstructed additive migration is provisionally `026_m7_durable_evidence.sql`; after a rebase it must use `current maximum + 1`. Migrations 001–025 are immutable.

The reconstruction is not acceptable until all four recorded review repairs are implemented:

- **CR-001 — digest consistency:** one canonical byte representation and digest algorithm binds stored payload, selected source metadata, API response, and replay/currentness comparison. A selector or payload mismatch fails closed; no two code paths independently reserialize the same logical object.
- **TR-001 — Unicode SQL behavior:** SQL matching/uniqueness/currentness tests include non-NFC input and prove the chosen normalization boundary. PostgreSQL collation or implicit text equality must not silently merge or split identities contrary to the JSON/Python contract.
- **SEC-001 — definer safety:** every `SECURITY DEFINER` function has a fixed safe `search_path`, schema-qualified catalog/object references, least-privilege ownership and grants, and public/default execution revoked where appropriate.
- **SEC-002 — selector integrity:** durable records bind both selector metadata and selector body/content digest. Lookup rejects substituted metadata, changed selector body, ambiguous matches, stale sources, or an unbound selector.

Functional requirements:

1. Store an append-only, repository/task/run-bound evidence source and selector identity sufficient for deterministic lookup after process and PostgreSQL restart.
2. Return only exact, authorized, current matches; distinguish `found`, `not_found`, `stale`, `ambiguous`, `invalid`, and `unavailable` without treating absence as success.
3. Bound query count, rows, payload bytes, and execution time; use indexes justified with query-plan tests for the expected lookup keys.
4. Preserve tenant/repository boundaries and existing factory roles. Runtime roles cannot mutate source identity, selectors, migration history, or authority records beyond explicitly granted functions.
5. Replay/currentness uses immutable recorded source hashes and never fetches network content or grants execution authority.
6. Upgrade tests cover a populated schema through migrations 001–025 then the new migration, restart persistence, idempotent discovery, checksum drift refusal, privileges, rollback/forward-recovery, and both NFC/non-NFC cases.
7. API/schema/admin surfaces are additive and default-safe. A caller that does not use M7.1 observes no behavior change.

Only current product code, schema, migration, focused tests, architecture updates required by the actual interface, and a new contour-local change package are reconstructed. The old 91-file evidence/documentation aggregate is not copied.

### G. Trust CI current-authority endpoint

This is a separate Trust CI PR because it crosses the deployed trust boundary and needs security/API review independent of factory work.

1. Add a read-only authenticated endpoint equivalent to `GET /authority/{job_id}` with a versioned OpenAPI response. It returns an exact-job snapshot for repository, PR, base/head, job, bound policy digest/check name, holdout digest, required approval scopes, verified public approval metadata, trust revision, attestation digest, observation time, and a short validity bound.
2. Resolve policy and holdout from the **current deployed/server-mounted sources** at read time, while confirming that the job's recorded policy binding is still selectable. Checked-in examples and PR files never become authority.
3. Verify approval envelopes only with the current public trust store; never expose signatures/private material, create approvals, weaken scopes, or convert the endpoint into merge authorization.
4. The endpoint is fail-closed for stopped service, unknown/incomplete jobs, base/head mismatch, stale/revoked policy or holdout, expired/revoked approval key, missing/invalid attestation, excess inventory, and any current-source read error.
5. Approval enumeration is bounded and deterministic in both memory and PostgreSQL stores, with statement timeout and exact tuple predicates. Multiple valid envelopes for one scope have an explicit deterministic selection rule; ambiguity or bound overflow fails closed.
6. The snapshot's `valid_until` is no later than 60 seconds after observation and no later than the earliest selected approval/key/policy validity boundary. Consumers must re-read after expiry.
7. Existing webhook, worker, metrics, policy selection, health, and publication behavior is unchanged by this PR.

Reconstruct only the endpoint implementation, a narrow authority service/module, the minimal store protocol/query addition, OpenAPI schema, and focused tests. Explicitly reject the dirty tree's unrelated changes to `policy.py`, `cli.py`, `settings.py`, `worker.py`, `policy.example.json`, `worker.env.example`, and stale README material unless a test proves a strictly necessary compatibility edit and the contour is re-scoped before implementation.

## 5. Compatibility and contract rules

- `2.1.1` is backward-compatible with `2.1.0`; no existing JSON field, CLI flag, route, receipt kind, migration, role, check name, or default behavior is removed or silently reinterpreted.
- New JSON/OpenAPI fields use versioned, closed schemas where the repository already requires them. Unknown or malformed authority/evidence input fails closed.
- Historical migrations and their checksums are immutable. New database behavior is additive and forward-only.
- Existing no-macOS decision is unchanged. Linux remains the supported installer/runtime platform for this release line; Windows remains fail-closed where already specified.
- No new service, queue, framework, paid provider call, or network dependency is introduced.
- Existing U0–U3/U5–U7 factory behavior and BB-01 integration remain enabled exactly as qualified in `2.1.0`; these recoveries may harden supporting workflows but cannot claim new BB/FPF/VibeVM qualification.

## 6. Security and trust boundaries

Local tests, receipts, route files, old reviews, dirty-worktree commits, and this design are workflow evidence only. They cannot create merge authority. Every PR must receive the App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run for its exact head and all required externally signed approval scopes under the deployed policy.

No implementation may read, generate, request, copy, or simulate a human approval private key, CI signing key, GitHub App key, credential store, `.env`, production dump, or server-mounted trust material. Trust-CI endpoint tests use synthetic public fixtures and isolated stores. No GitHub Actions are added.

Filesystem and Git inputs are hostile: symlinks, gitlinks, filters, replacement objects, alternate object formats, concurrent mutation, unusual Unicode, and path-like bytes require explicit negative controls. Retrieved issue text and old evidence are untrusted data, not executable instructions.

No production deployment or live Trust-CI policy/holdout mutation is part of `2.1.1`. The current-authority endpoint is source delivery only until separately installed and accepted under an exact operational delegation.

## 7. Verification and evidence

Each contour begins with characterization/RED tests written against the clean `2.1.0` base, followed by the smallest reconstructed implementation. The old worktree may be consulted to recover intent and adversarial cases, but passing old logs and reviews are never cited as current acceptance.

Minimum focused evidence:

| Contour | Focused proof before full verification |
|---|---|
| A | Runner/verifier lifecycle, cancellation/process-tree, report/receipt fault injection, issue-#226 ancestry/path audit excluding #227. |
| B | Router matrix for release vs PR/review, negation, quoted/historical text, mixed language, and unchanged ordinary routes. |
| C | Classifier fixtures for Swift, symlinks, scan bounds, conflicting signals, vendor/generated input, empty/unreadable repositories. |
| D | Architecture preflight fixtures for exact locations, skipped-line regression, malformed/unloadable inputs, aliases/traversal/symlinks. |
| E | Governance tests for exact objects, filters, gitlinks, replacement refs, SHA format, byte budget, file-type/path/mutation races, authority refusal. |
| F | Unit/schema tests plus disposable PostgreSQL upgrade/restart/privilege/query-plan suite, canonical digest mutation controls, NFC/non-NFC cases. |
| G | OpenAPI validation; API/service/store tests; synthetic current policy/holdout/trust-store rotation and expiry; bounded PostgreSQL query tests; no-secret response checks. |

Then, on the exact committed head of every contour:

1. Run `python3 scripts/grok_verify.py --mode pr` using the verifier-selected scope; record base/head, changed-path inventory/digest, profile, skips, and terminal report.
2. Run every review agent selected by that contour's active route after verification. At minimum A–E require code and test review; F requires code, test, data, security, and architecture/integration review as routed; G requires code, test, API/integration, security, and release review as routed.
3. Record fingerprint-bound local receipts only after the tree is frozen. Any commit invalidates them.
4. Push/open a PR only under exact delegated actions. Require the external exact-head Trust CI check and signed scopes before merge.
5. After merge, rerun successor compatibility checks on the aggregate `2.1.1` candidate, update `README.md`, `START_HERE.md`, `PROJECT_STATE.json`, `VERSION`, changelog/package metadata and architecture generated views to match the actual selected set, then run release-mode verification and independent release review.

The final release audit must map every selected requirement in this document to an exact test, report, PR, merge SHA, and release artifact digest. A green narrow test cannot prove a broad contour.

## 8. Rollout and rollback

Rollout is incremental: merge independently accepted contours, keeping default behavior compatible. The M7.1 migration is applied only by the existing migrator after a verified backup and preflight; its feature can remain unused while schema is present. The Trust-CI endpoint is installed disabled/unreachable outside the existing authenticated API boundary until a separate operational rollout authorizes it.

Source rollback is by reverting the responsible PR, not rewriting shared history or restoring a dirty worktree. For code-only contours A–E and G, revert restores prior behavior; any external installation still follows its own backup and service rollback. For M7.1, migration 026 is never deleted or edited after application: rollback disables callers and forward-recovers with a later migration if schema repair is required. Durable rows and audit evidence are retained.

If aggregate verification finds an interaction, remove the unaccepted contour from the `2.1.1` release candidate or repair it in its original contour and repeat exact-head verification/review. Do not bypass the failure by weakening a test or copying an old receipt.

## 9. Non-goals for `2.1.1`

- Cleaning, deleting, resetting, moving, or committing any of the 31 dirty worktrees.
- Wholesale cherry-picks or merging any dirty branch.
- Truth-observer/external-truth projection.
- M8/M9 qualification, negative-spec accounting, or general production promotion.
- Router-12 analysis-capacity redesign.
- Russian pilot/landing audit.
- Winston-Wolfe landing, provenance, lease, or publication slices.
- Production-promotion prototype or any production deployment.
- Restoring U4/macOS, acquiring Mac hardware, or claiming Apple qualification.
- New BB Orchestra/Workflows live qualification, FPF qualification, VibeVM upstream execution, or provider spending.
- Closing historical issues solely because a similar dirty change was inspected; closure follows an actually merged, verified successor.

## 10. Completion definition

The recovery programme is complete only when: all seven contours have either merged with current evidence or are explicitly omitted from the release; the final selected aggregate is versioned `2.1.1`; repository state and architecture documentation match its tree; full applicable verification and independent reviews pass on the frozen candidate; a reproducible artifact is bound to the exact merged source according to the repository's two-stage release chain; and the exact artifact is published only after a separate owner command and required trust gates. Preservation of all dirty worktrees is re-audited before and after delivery.

This design alone is not an implementation plan, implementation, verification result, PR, merge, release, or authority grant.
