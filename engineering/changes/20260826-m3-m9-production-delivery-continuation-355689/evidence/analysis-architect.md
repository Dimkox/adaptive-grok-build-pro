# Architect analysis — bounded M3-to-M9 sequence

Route: `35568941ae59`
Role: route-selected `architect` (read-only except this report)
Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-m3`
Observed branch/HEAD: `milestone/m3-controlled-knowledge-debt` at `bc5ef65052f7f0b3727faaac6c4ada11871d8a23`
Exact M2 parent: `635c9ddf2d63c1ea823074106976a8f3de6299a9` (one commit behind HEAD)
Pre-report tree fingerprint: `94700384a42bc1f6f24a8de4d0fb48e0281f95813e267960b82a36c3caa0e052`
Scope: architecture recommendation only; no product implementation, external action, secret read, systemd action, verification receipt, or merge claim.

## Ruling

The safest route is a gated chain, not a combined M3-M9 implementation: first reconcile the current change-package/route lineage, finish and externally deliver M1/M2/M3 in order, then build M4 through M9 as separately versioned planes with an exact immutable handoff at every boundary. M4 must end at `ready_for_human`; M5 may execute only inside isolated task workspaces; M6 may recommend only `pass|repair|needs_human`; M7 external writes and M8 auto-merge remain unavailable under the current “no autonomous external writes” scope; and M9 production promotion remains a human-signed, operator-owned action.

A narrow M9 foundation can be developed before M4-M8, but only as offline schemas, signature/digest verification, and a disposable local preview simulator. It cannot be called an M9 exit slice, and doing it now consumes the single writer, delays M3, and creates contract adapters or migrations once M4 task/run identity, M6 verdicts, M7 merge provenance, and M8 trust-profile identity exist. The bounded foundation has moderate standalone cost and high opportunity/rework cost; an early delivery runtime or deployment API has unacceptable cost and should not be started.

## Exact current-state findings

1. **M3 is at its first implementation slice.** The dirty tree contains four governance schemas, three empty registries, and `tests/test_governance.py`. There is no governance engine/CLI/handoff emitter, no M3 architecture/receipt integration, and no tracked `factory/**` implementation. The observed files are consistent with Task 1 of `docs/superpowers/plans/2026-08-28-m3-controlled-knowledge-debt.md`, not with completed M3.
2. **The current authority package is incoherent and must be repaired before another product commit.** `.grok-stack/runtime/active-route.json` and both package route copies still name base commit `069fe822...`, while the actual M3 base is `635c9dd...`. The new package `20260826-m3-m9-production-delivery-continuation-355689` is draft/placeholder and its `route.json` names the old change ID `20260826-model-agnostic-autonomous-factory-355689`. The older tracked package is approved and detailed, but its referenced canonical design spec and typed `change-spec.yaml` are absent from this branch. These are exact-state and source-of-truth failures, not documentation nits.
3. **Upstream work is local source evidence, not yet the deployed dependency.** The README records M1 PR/check/approval/merge/deployed reader/holdout work as incomplete, and M2-B independent enforcement plus M2 PR/external check/deployment as incomplete. M2's durable state now says local `ready`, but its release text and README contain older pending-language. M3 can be developed locally on the exact reviewed M2 source, but M4 runtime intake and every later activation must wait for the upstream external Trust CI and deployment gates.
4. **The external trust boundary already has the correct shape and must not be absorbed.** `trust_ci.*`, its App key, attestation key, human trust store, deployed policy/holdout, and App-owned Check Run remain outside `factory.*`, agent workspaces, delivery services, and repository authority. Local receipts and future factory verdicts remain preflight/proposal evidence.
5. **The roadmap conflicts with the currently approved capability boundary at M7/M8.** `DARK_FACTORY_ROADMAP.md` describes automated PR creation and earned auto-merge, while the approved package explicitly keeps all autonomous external writes unreachable and defers M7-M9. Under the higher-priority current scope, M7 may prepare a branch/PR bundle and collect shadow evidence, and M8 may calculate/demote trust profiles, but neither may push, open, merge, release, or deploy without a later explicit scope decision and exact delegated operation.

## Required convergence gate before M3 continues

The sole write owner should resolve this once, with no parallel product writer:

1. Select one durable change package and make its change ID match the active route.
2. Regenerate the route against the actual exact base/current tree; do not hand-edit stale base identity into apparent validity.
3. Restore or replace the absent canonical design spec and schema-valid typed spec on this lineage. Freeze measurable acceptance criteria, forbidden outcomes, required `architecture`, `security`, `release`, and any production/external-write approval scopes. A new factory service, PostgreSQL schema, FastAPI boundary, execution runtime, and later delivery service require explicit ADR/design approval.
4. Reconcile M1 and M2 status/doc facts. Deliver M1, then M2, through their PRs and App-owned exact-head checks; deploy any independent M1 reader/holdout and M2-B policy only through operator-controlled changes outside the PR trust domain.
5. If the M2 merge changes M3's applicable base SHA, rebase/recreate the M3 change from protected main and regenerate every base/head-bound handoff, digest, local receipt, review, and external check. Never carry an approval or receipt across that SHA change.

No M4 code should be added while the M3 handoff producer and current typed authority are absent.

## Safest bounded architecture sequence

| Gate | Smallest coherent slice | Required proof before the next gate | Explicitly absent |
| --- | --- | --- | --- |
| M3-A | Closed governance/debt/example schemas and empty/candidate-only registries | Adversarial schema tests; no fabricated active record or approval | `factory/**`, provider, systemd, network, external write |
| M3-B | Bounded no-follow loader, lifecycle/conflict/debt semantics, exact six-field `GovernanceHandoffV1` | Candidate-only agent behavior; independent review/human activation; expiry/revocation; mutation/symlink/duplicate-key tests | Runtime service or policy self-promotion |
| M3-C | M2 model/fitness, installer, verifier/receipt binding, non-authoritative Markdown projections | One final fingerprint, four selected reviews, M3 PR exact-SHA App check, required signed scopes, human merge | Trust CI mutation or merge authority |
| M4-A | Isolated `factory/` contracts, closed state machine ending at `ready_for_human`, checksum-bound migrations | Frozen M1/M2/M3/policy/SHA validation; future PR/merge/deploy states rejected | Provider/workspace/systemd/external endpoints |
| M4-B | PostgreSQL intake, idempotency, supersession, `SKIP LOCKED` leases, monotonic fences, 20/10/1 capacity, budgets, kill, append-only audit, bounded reconciliation | Real PostgreSQL concurrency, worker-death/restart, late-fence, initial-plus-two retry, budget/accounting, role-isolation tests | Any read of `trust_ci.*` |
| M4-C | Authenticated Unix-socket API/CLI for intake/status/list/cancel/claim/proposal/reconcile | Closed OpenAPI, request bounds, scoped token-file auth/redaction, no shell/provider/git/systemd route; M4 PR exact-SHA Trust CI and human merge | Runtime activation and external writes |
| M5-A | Immutable `TaskPacketV1`, provider-neutral JSON/JSONL protocol, content-addressed artifact and run-manifest contracts | Canonical reconstruction; version/capability/identity/sequence/terminal-event adversarial fixtures; no raw reasoning persistence | Native provider events as authority |
| M5-B | Workspace/tool/note/artifact brokers and Codex-first adapter in an isolated runtime | Cross-task/Git/symlink/mount escape tests; repo subprocess sees no credentials and no network; adapter egress isolated and allowlisted | Docker socket, Trust CI/human/production keys in task runtime |
| M5-C | Fixed systemd source topology and orphan reconciliation | Dedicated non-production host, fixed unit identities, resource limits, restart/fence drill, operator install/activation of exact reviewed artifacts | Task-derived units/commands; agent activation |
| M6-A | Typed durable findings and independent same-head validators | Every verdict maps to M1/M2/M3 IDs; implementer cannot write evidence; reviewers see immutable diff/evidence, not implementer reasoning | Self-approval |
| M6-B | Meta-review and maximum three same-writer repair cycles | Contradiction/duplicate/unsupported-pass tests; repeated finding/risk/architecture change/fourth cycle -> `needs_human`; all changed-code evidence regenerated | A second writer or stale evidence reuse |
| M7-A | Exact branch/commit/PR **preparation bundle** and WIP/shadow-mode ledger | Reproducible bundle bound to task/run/base/head/spec/architecture/governance/policy/verdict; overlap/WIP/cost/age stops | Network credential or automatic push/open |
| M7-B | Optional operator external-action broker, only after a new scope gate | Exact resource/action/HEAD/fingerprint/TTL delegation; idempotent audit; human merge; App-owned check success | Broad PAT, direct main push, factory-published Trust CI check |
| M8-A | Trust-profile cohort calculation and immediate demotion policy | At least 30 accepted tasks per exact tuple; false-negative, defect, rollback, security, disagreement and drift accounting | Auto-merge activation under current scope |
| M8-B | Optional low-risk merge activation, only after separate explicit authorization | App-bound branch protection, exact profile tuple, sampled audit, immediate fail-closed demotion, no red/yellow eligibility | Production deployment and protected/control-plane paths |
| M9-A | Exact-artifact delivery contracts and disposable preview | Offline signature/attestation verification; exact merged SHA -> one immutable artifact digest; deterministic smoke/teardown; no credentials | Staging/production mutation |
| M9-B | Separate delivery control plane for staging/canary evidence | Environment revisions, single-flight deployment fence, same-artifact promotion, typed metric/abort policy, immutable outcomes; human-authorized staging action | Factory/Trust CI DB or keys |
| M9-C | Human production promotion and exercised recovery | Human-signed exact candidate/environment/policy request created outside agents; canary thresholds; automatic halt; human-triggered rollback drill; production outcome feeds M8 evidence and M3 candidate only | Agent approval, agent production credentials, policy self-promotion |

Each slice gets one write owner, a dedicated change package/branch/PR, focused red-green tests, one final repository verifier on its final product fingerprint, the route-selected independent review wave, and the App-owned policy-epoch Check Run on the exact PR head. A code, base, policy, holdout, environment-policy, or artifact change invalidates downstream evidence rather than being patched into an existing envelope.

## Stable plane boundaries through M9

```text
M1 spec + M2 architecture + M3 governance
  -> immutable authority handoff
factory.* control plane (M4)
  -> fenced TaskPacketV1 / proposals only
isolated execution plane (M5)
  -> content-addressed diff/artifacts/run manifest
independent semantic plane (M6)
  -> exact-head pass|repair|needs_human verdict
human-authorized PR preparation/action + shadow ledger (M7)
  -> protected merge plus App-owned exact-head Trust CI attestation
trust-profile evaluator/demoter (M8)
  -> eligibility evidence, never production authority
delivery.* control plane (M9)
  -> preview/staging/canary evidence
human-signed production promotion
```

The factory application writer owns only its isolated repository workspace. Read/note agents receive OS-enforced read-only repository views and can append bounded, untrusted notes through a broker. Repair always returns to the same live writer/fence. PR credentials and delivery credentials live in separate operator/action brokers; the writer, model adapter, `factory.*`, and Trust CI never receive them. M9 also needs a separate per-application/environment deployment fence so two valid human requests cannot race, but that fence does not weaken the single repository-writer invariant.

## Exact-SHA and artifact chain

Every boundary should use a closed, versioned envelope containing only bounded identifiers/digests and explicit provenance. The chain is:

1. M4 accepts immutable M1/M2/M3 handoffs plus repository/base SHA and deployed policy digest.
2. M5 packet digest binds task/run/fence, exact source SHA, role, model/adapter/tool/image/network/secret-scope versions and budgets. Any control-field change creates a new run.
3. M6 verdict and every review bind the exact result head SHA and artifact/run-manifest digests. A repair creates a new head and invalidates prior verdicts.
4. M7's prepared PR bundle binds base/head SHA and all prior digests. Trust CI independently checks that exact PR head and signs its own attestation; the factory cannot submit or simulate that signature.
5. After protected human merge, the build starts from the exact merged commit and produces one content-addressed artifact, SBOM and signed supply-chain manifest. Preview, staging and canary promote that same digest; they never rebuild per environment.
6. An M9 promotion request binds merged SHA, artifact/SBOM/manifest digests, Trust CI attestation reference, environment revision/config digest, delivery-policy digest, canary/metric contract, rollback artifact, expiry and nonce. A human signs production scope outside the agent environment.
7. Delivery outcomes append the exact deployment/canary/rollback identities. They may demote an M8 profile immediately and create an M3 `candidate`; they cannot activate governance or authorize another deployment.

Trust CI remains source-merge authority, not the factory scheduler or deployment controller. M9 may verify its published attestation with a public key/read-only interface, but it must not query `trust_ci.*`, hold the App or attestation private key, rename the required check, or mutate policy/holdout/branch protection.

## Early M9 slice: feasibility and cost

### Technically safe before M4-M8

A standalone, inactive `delivery-contracts` slice can define closed `ArtifactManifestV1`, `DeliveryCandidateV1`, `EnvironmentRevisionV1`, `CanaryPolicyV1`, `PromotionRequestV1`, and `DeliveryOutcomeV1` schemas; implement canonical digest and offline signature/attestation verification; and run a no-network disposable preview/smoke/rollback simulator from a locally supplied exact-SHA artifact. `promote` must be absent or prepare/print only. No database, daemon, cloud/cluster API, secret, provider, GitHub call, systemd activation, staging mutation, or production endpoint is permitted.

This provides useful early pressure on exact-artifact identity, same-artifact promotion, metric contracts and rollback semantics. It does **not** prove M9 because there is no durable factory task/run/fence, no independent semantic verdict, no protected merge provenance, no shadow cohort/trust profile and no live environment outcome.

### Cost

- It takes the only product-writer slot away from the currently incomplete M3 critical path and adds a separate high-risk architecture/security/release review cycle.
- Unless kept experimental and purely functional, it will duplicate M4 scheduling/audit/reconciliation and later require deletion or migration.
- Strict v1 contracts frozen now will need adapters or new versions for at least four not-yet-stable subjects: M4 task/run identity, M6 verdict identity, M7 merge/Trust CI provenance, and M8 trust-profile cohort identity.
- A runtime slice would introduce premature production-adjacent credentials, network, environment state and rollback authority without the preceding WIP, semantic and empirical gates; that cost is unacceptable.

Recommendation: record the M9 contract sketch now in architecture, but defer product code until M4 contracts are stable. If schedule requires early implementation, limit it to one isolated, version-0/offline contracts-and-simulator PR after the current M3 authority package is repaired; accept that it earns no M9 completion credit and will need an explicit integration/versioning pass after M8-A.

## Rollout and recovery policy

- Source rollout is always PR-only. Local verification/reviews are preflight; the App-owned exact-SHA Check Run and required human-signed scopes are the merge gate.
- Runtime rollout uses immutable signed artifacts, operator-provisioned secret files, least-privilege OS/DB identities, no network by default, staged non-production activation, synthetic tasks, kill/restart/reconcile drills, and explicit go/no-go observations.
- Schema rollback is forward recovery after durable intake: kill new work, preserve audit/evidence, restore into a separate database or apply a new migration. Never down-migrate or reuse `trust_ci.*`.
- Delivery rollout promotes the same artifact digest through preview/staging/canary. Production requires a fresh human signature for the exact request. Under the current no-autonomous-write boundary, a breach automatically halts further progression and pages the operator; rollback is a separately authenticated human action and must be exercised in staging/canary. A future deterministic rollback-only controller would require a separate security decision and narrowly signed preauthorization.
- No GitHub Actions are introduced anywhere. Persistent scheduling uses reviewed systemd units and PostgreSQL correctness; Trust CI stays the existing self-hosted App-owned system.

## Exit interpretation

“Reach M9” must be reported in layers:

- **source-ready:** reviewed M9 contracts/controller code exists on an exact fingerprint;
- **merge-ready/merged:** exact PR SHA passed external Trust CI and human merge;
- **staging-proven:** same signed artifact passed preview/staging/canary and recovery drills;
- **production-qualified:** a human promoted the exact candidate and outcomes were recorded;
- **program complete:** only after every M0-M9 dependency and empirical gate is met.

No local report, factory verdict, simulator, or early M9 contract may collapse those states into “production delivered.”
