# Integration architecture review — one route, no branch loss

Route: `944abd96ddb3`
Repository: `Dimkox/adaptive-grok-build-pro`
Observation: 2026-09-01 after `git fetch --all --prune`
Observed protected base: `origin/main@1c06299894279a88b881defa3f19b004fa742223`

## Verdict

Use one canonical delivery route/change package to reconcile and sequence the existing branches; do not create a route per milestone or per pull request. Branches may remain isolated integration units, but each completed unit must be folded into the same current `main` lineage and reflected in one authoritative state model before the route advances.

The accepted M2+M3 stack is `origin/milestone/m2-executable-architecture@67714a1f1b87effcfabe55d5ca2770d0a68d17c1`. M4 is not accepted: PR #17 exposes only `8e6504168462bbabad359fec3d23838c87f5ba22`, while the local branch has two unpublished repair commits through `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`. M5-M9 have no implementation branches that meet milestone completion criteria.

The live main protection is authoritative and currently requires strict/up-to-date status:

- `adaptive-trust-ci/verified@06ecf1c875bc`;
- GitHub App ID `4694114`;
- exact pull-request head SHA, with a new run and new external approvals after any head or base change.

## Evidence that controls the ruling

- PR #10 merged M2 into the M1 staging branch at `c23fd49f80c7d1c74ca3393b6079a74f251a72d8` after PR #16 supplied the accepted M2 repair head `022411b05924618cfde0cb97b8c8aff4955e6013`.
- PR #11 merged the restacked M3 head `1e73ff9b91d9b711cafccad7ccccb1a992d5e84d` into M2, producing `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Neither `67714a1` nor the remote M4 head is reachable from `origin/main`; stack merge is not main delivery.
- PR #17 is mergeable only in the Git graph. Its current-epoch Trust CI failed `repository-verification`, and GitGuardian failed because commit `c7bdb9138d6fb34db46362b371fee0feb99b5c39` introduced password-like values in `factory/.env.example` and `factory/compose.yaml`.
- The local M4-only delta after the PR head is `7520b33829dd6f538544e312741ecce7a36729b1` plus `cf0219b2510dd1a8d5f34e7a6d44e1e4c633dd06`; it changes `.grok-stack/adaptive_grok/verification.py`, `tests/test_verification_doctor.py`, and `mistakes.md`.
- PR #19 is currently clean at `ecc85d903d0394f99a139fd4e74a7cc452e386c6`; both current-epoch Trust CI and GitGuardian succeeded. Strict protection means this eligibility is lost if `main` moves and GitHub marks the branch behind.
- PRs #12 and #13 are not failed implementations. Their old-epoch checks ended `action_required` with the exact message `Missing exact-SHA approval scopes: governance`; after any update they need new current-epoch checks and newly signed governance approvals.
- PR #15 failed current-epoch root unit tests. It contains the pre-restack M3 head `d4cc01f`, not accepted M3 `1e73ff9` or aggregate `67714a1`; therefore it cannot be merged as an umbrella. It nevertheless contains a unique investor-demo slice beginning with `9dcdf58` and subsequent packaging/test repairs through `165d5dd`, so closing it without extraction would lose work.

## Challenge to the first architect report

The first report has the right state axes and correctly refuses to call M2/M3/M4 delivered, but its integration sequence needs four corrections.

1. **Pushing `cf0219b` to PR #17 is insufficient.** GitGuardian reports the offending historical commit, not merely the current file content. An appended repair leaves that commit in the PR range and does not reliably clear the external scan. Prefer a clean successor branch based on delivered M2+M3, containing only the reviewed final M4 tree and safe non-secret examples; alternatively a human may classify the findings as false positives, but the agent must not make that security decision.
2. **Closed PR #14 cannot disappear from the inventory.** `cb2fe7ce637c464179e20b5b37aae334e56c1838` is unmerged and contains a unique production-promotion subsystem, SQL migration, API/contracts, and operational controls. It must be retained for explicit re-evaluation or a clean successor; it is not proven superseded by PR #15 or another branch.
3. **PR #15 is partly superseded, not wholly disposable.** Its embedded M1/M2/pre-restack-M3 history is superseded by accepted stack SHAs, while its investor demo and clean-package repairs are unique and must be replayed onto the accepted main lineage.
4. **“SEO first” is conditional.** It is the cheapest ordering only while PR #19 remains clean at `ecc85d9`. If the state-repair PR moves `main` first, PR #19 must be refreshed and rechecked; its present success cannot be reused on a changed base.

## Branch disposition

### Must retain until integrated or explicitly abandoned

| Ref / PR | Disposition | No-loss rule |
| --- | --- | --- |
| `origin/feature/seo-landing-codex-main@ecc85d9` / #19 | deliver to `main` | Keep exact head while main is unchanged; otherwise refresh, verify, and obtain a fresh exact-SHA check. |
| `origin/milestone/m1-typed-intent-evidence@c23fd49` | stack evidence | Retain until the M2+M3 aggregate is delivered; do not treat its branch name as M1 delivery head. |
| `origin/milestone/m2-executable-architecture@67714a1` | accepted M2+M3 aggregate | This is the source tree for clean main integration. |
| `origin/fix/m2-trust-ci-zombie-process-group@5b2a259` | accepted repair evidence | Already stack-merged by #16; retain through aggregate delivery, then archive. |
| `origin/milestone/m3-controlled-knowledge-debt@1e73ff9` | accepted M3 source evidence | Already stack-merged by #11; retain through aggregate delivery, then archive. |
| `origin/milestone/m4-durable-control-plane-accepted-m3@8e65041`, local `cf0219b` / #17 | rejected remote gate plus newer local repair | Preserve both refs. Build a clean successor from the final local tree; do not force-push or delete #17 before the successor lands. |
| `origin/fix/human-approval-cli@0f7f508` / #12 | independent Trust CI fix | Rebase/restack after milestone integration; rerun reviews and acquire fresh `governance` approval. |
| `origin/feat/trust-ci-repository-profiles@f2fd8a7` / #13 | independent Trust CI feature | Rebase after #12; resolve overlapping Trust CI policy/docs/tests and acquire fresh `governance` approval. |
| local `policy/production-only-human-approvals@cb2fe7c` / closed #14 | unique, unresolved production-promotion feature | Remote branch was pruned, but the local commit survives. Preserve it and create a reviewed clean successor after #12/#13 if the feature remains approved. |
| `origin/mvp/investor-ready@165d5dd` / #15 | obsolete umbrella, unique demo slice | Never merge wholesale. Replay the unique demo/package commits onto current accepted main, verify, then supersede #15. |
| `origin/milestone/a-plus-autopilot@90a5da2` | design-only reference | Preserve the spec as planning evidence. It is not M8 implementation and must not advance milestone state. |
| local `feature/workflow-artifact-adapters@dccaeec` | local-only unresolved work | Inventory and compare against the accepted aggregate before any cleanup; absence of a PR is not evidence of supersession. |

### Superseded for integration, retain only as archival evidence until reconciliation is accepted

- PR #1 / `origin/hardening/trust-boundary-v2-1`: explicitly closed as superseded and contains prohibited GitHub Actions-era design; never merge.
- `origin/feature/trusted-self-hosted-ci-v2`: pre-PR2 alternate in-process CI implementation; the delivered Trust CI authority lives under `trust-ci/`, so this branch is not a delivery source.
- `origin/fix/pretooluse-shell-targets` and `origin/handoff/m0-2-live-authority`: M0 precursor/handoff branches superseded by the delivered PR #5 lineage; preserve citations, not code integration.
- Source branches of merged main PRs #2-#9 are historical after their merge commits are recorded. A source SHA need not be an ancestor of main when GitHub used a merge/squash strategy; the merged PR plus resulting main commit is the delivery fact.
- `origin/feature/seo-landing-codex-side-project` and the advanced staging ref `origin/fix/path-aware-shell-policy-circuit-breaker@341d72b` become archival after #19 reaches main.
- Local aliases `feat/m4-durable-factory-control-plane@67714a1`, `milestone/m4-durable-control-plane-local@d4cc01f`, and `fix/m3-restack-accepted-m2@1e73ff9` carry no additional accepted product beyond the named aggregate/source refs.
- Local `main@c54fd01`, local `fix/path-aware-shell-policy-circuit-breaker@7c61e3b`, local M1/M2/M3 tracking branches, and local `feat/trust-ci-control-plane@b9c1e42` are stale pointers. Never push them over their newer remotes.

No remote or local branch should be deleted as part of state repair. Cleanup is a later explicit external/destructive action after every retained SHA is recorded and its unique diff is either delivered or explicitly abandoned.

## Concrete integration sequence

All phases below stay in one canonical milestone-delivery ledger. Each product integration may use an isolated branch/PR, but completion returns to the same route state; no separate “M2 route”, “M3 route”, or “M4 route” is created merely because a branch exists.

### Phase 0 — finish truthful state repair

Record all refs/PRs above, the current protection tuple, and the distinction between implementation, review, stack merge, and main delivery. Because `mistakes.md` is in the change, the current policy example classifies the state PR as `governance`; expect an externally signed governance approval for its exact head. Merge only after the current-epoch App check succeeds on an up-to-date head.

If #19 can be merged before the state PR is committed/pushed, doing so preserves its already-green `ecc85d9` check and the state repair must then be rebased and re-observed. If state repair lands first, update #19 from the new main and obtain new local evidence plus a fresh App check.

### Phase 1 — deliver SEO side project

Merge #19 only at an exact green head and with the exact delegated PR merge operation. After merge, fetch `origin/main` and record the resulting merge commit. #18 is only staging integration and does not substitute for this delivery.

External gates: GitGuardian success; `adaptive-trust-ci/verified@06ecf1c875bc` success from App `4694114`; strict current base; any policy-requested exact-SHA approvals; exact local merge grant.

### Phase 2 — deliver the accepted M2+M3 aggregate once

Create a clean delivery branch from then-current `origin/main`, integrate the tree represented by `67714a1`, and resolve conflicts on the delivery branch. Do not merge M2 and M3 separately and do not rewrite their historical remote refs. The delivery PR updates state so M2 and M3 become delivered only after its merge commit is observable on `origin/main`.

External gates: full high-risk verification and code/test/security/data/release reviews on the integrated head; fresh signed scopes requested by deployed policy (the current path set is expected to trigger at least `governance` and `database`); current-epoch exact-SHA Trust CI; strict current base; exact merge grant.

### Phase 3 — rebuild and deliver M4 cleanly

From the new main, apply only the M4 delta from `67714a1..cf0219b`. Before the first public successor commit, replace password-like example assignments with a structure that contains no credential value and rerun secret scanning. This avoids importing the GitGuardian-flagged `c7bdb91` history while preserving the final M4 tree and the two local verifier repairs.

Run the original M4 high-risk suite, including disposable PostgreSQL restart/reconciliation proof, and rerun code/test/security/data/release reviews. Open a new clean PR to main. Close #17 as superseded only after the successor is merged and its mapping is recorded.

External gates: GitGuardian success on the full successor PR range; fresh signed `governance`, `database`, and `production` scopes expected from `.grok-stack/**`, SQL resources, and `factory/compose.yaml`; current-epoch exact-SHA Trust CI; strict current base; exact merge grant. A human false-positive decision on the old PR is optional and never synthesized by an agent.

### Phase 4 — restack independent Trust CI work

Integrate #12 first, then #13, each onto the latest main. Their overlaps are mostly `trust-ci/README.md`, `decisions.md`, `mistakes.md`, and policy/tests, so sequencing prevents the broader profiles feature from obscuring the smaller CLI fix. Do not reuse their `@6737355947c2` checks.

Then re-evaluate `cb2fe7c` from closed #14. If still desired, reconstruct a clean successor on top of #12/#13 and current main rather than reopening the stale branch blindly. Its migration, production compose, promotion contracts, and deployed-source separation need fresh high-risk review.

External gates: #12 and #13 each require new exact-head signed `governance` approval plus current-epoch Trust CI. The #14 successor is expected to require `governance`, `database`, and `production` signed scopes, full security/data/release review, current-epoch Trust CI, strict base, and an exact merge grant. Repository source merge still does not deploy Trust CI policy, database state, keys, images, or branch protection.

### Phase 5 — salvage the investor MVP without the obsolete umbrella

Create a clean branch from the latest accepted main and replay only the unique PR #15 slice: the loopback fitness fix, investor-demo implementation, and clean-package/runtime-inventory repairs from `544c6d2` through `165d5dd`, excluding the merge of old main and excluding pre-restack M1/M2/M3 history already delivered. Resolve the slice against current M4 rather than letting #15 overwrite it.

External gates: reproduce and fix the existing `root-unittest` failure, then full verification and the route-selected reviews; fresh policy scopes (at least `governance` for `.grok-stack/**`); current-epoch exact-SHA Trust CI; strict current base; exact merge grant. Close #15 only after the clean successor lands.

### Phase 6 — continue M5 through M9 under one consolidated milestone route

After phases 1-5, refresh state and begin the roadmap at M5. `milestone/a-plus-autopilot` is input to design, not proof of M8. M5, M6, M7, M8, and M9 must each gain explicit implementation/review/delivery evidence, but the orchestration ledger and route remain consolidated: isolated branches are folded back before advancing the canonical state, and abandoned experiments are marked superseded rather than silently forgotten.

## Stop conditions and recovery

- Stop a phase if its exact source SHA changes, `main` moves under strict protection, a required signed scope is missing, Trust CI is not the App-owned `@06ecf1c875bc` check, or any independent review is stale.
- Do not use admin bypass, force-push a shared milestone branch, generate human signatures, mark GitGuardian incidents safe, or merge a failed check.
- If a clean successor fails, preserve its branch and return the failure to the same consolidated route/write owner; do not spawn a new milestone route to hide the failure.
- After every merge, fetch main, record the merge commit, update the one state model, and re-evaluate all remaining PRs because strict checks and conflict status can change.
- Rollback is per delivered PR through a protected forward-fix or revert PR. Deleting or editing state documentation cannot roll back product, Trust CI source, migrations, or a production service.
