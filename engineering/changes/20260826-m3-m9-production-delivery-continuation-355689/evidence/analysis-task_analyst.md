# Task analysis — M3→M9 production delivery

## Status and decision boundary

This is a delivery map, not an implementation authorization. The current route
(`35568941ae59`) is red-risk/high-risk (`ai`, `security`), selects one
`ai_implementer`, and requires `scope_and_design_approval`, final PR-mode
verification, and code/test/security/release review evidence. The active change
package is still a draft with an empty typed acceptance/evidence map. It must be
completed and approved before its selected writer implements anything.

The repository shows local source readiness, not integrated production readiness:

- M1 is `ready` locally at product SHA `98649e4…`; its delivery still requires
  an authorized PR update, the App-owned exact-SHA check, required external
  approval scopes, merge, and separately proven deployed reader/emitter/holdout
  work.
- M2-A is `ready` locally at product SHA `72927ee…`, the parent of the current
  M3 branch. Its state record is newer than its stale release prose. It likewise
  is not merged and M2-B (independent deployed enforcement) is explicitly open.
- `main` is `c54fd015…`; therefore neither M1 nor M2-A is in the protected-main
  baseline. The current M3 tree has uncommitted schema/registry/test scaffolding
  only; no `factory/` package yet exists.
- M0 live authority is an operational fact that cannot be inferred from source:
  a current policy-epoch App-owned check, branch protection binding the App ID,
  signed-attestation verification, protected-path approval proof, restore/restart
  drill, and kill-switch proof must be independently observed.

## Dependency-ordered delivery map

Every row is a separate red-risk change package/PR after its predecessor has
merged into protected `main`, unless a user records the roadmap's narrowly named
bootstrap exception. Each PR is based on current protected `main`, has a typed
spec with criterion-level evidence, one application-code writer, local PR-mode
verification and independent reviews on its final fingerprint, then the exact
head's App-owned Trust-CI check and all externally required signed scopes. A
source PR never deploys Trust CI policy, its holdout, keys, database, App setup,
or production.

| Order / PR | Dependency and bounded contents | Acceptance criteria / required proof | Human gates and hard stops |
| --- | --- | --- | --- |
| **P0 — prerequisite authority** | Complete/refresh **M0**, plus deliver the locally ready M1 and M2-A source through their own PRs. M2-B is a separate trust-plane rollout, not a factory PR. | M0 exit set is live: App-owned current-policy exact-SHA check, app-bound protected `main`, independently verified attestation, protected-path approval/requeue, backup/restore/restart and kill-switch drills, no GHA. M1 gives valid typed evidence; M2 gives a stable architecture handoff/digest and externally enforced critical rules only after its own rollout. | Operator-only secret provisioning/deployment; exact delegated external operations; human-signed external approvals; no bootstrap exception unless explicitly named and time-bounded. **Do not start M4 from locally ready but unmerged M1/M2.** |
| **P1 — M3 Controlled Learning and Debt** | Implement strict rule, canonical-example, debt, and handoff records. Agent output may create only candidate records; produce `GovernanceHandoffV1` for M4. Keep Markdown a non-authoritative projection. | Closed, canonical, bounded no-follow input validation; lifecycle `candidate→reviewed→approved→active→deprecated→revoked`; active rules require independent review, human governance approval and live evidence; expiry/revocation removes effect; deterministic conflict/duplicate detection; intentional debt has owner/trigger/deadline/tests; reviewed versioned examples exist for all seven categories; factory task cannot self-activate a rule. | M3 scope/design approval; distinct reviewer and human governance approver for activation; no `trust-ci/**`, factory runtime, provider, systemd, or external action. |
| **P2 — M4 Durable Factory Control Plane** | Add isolated `factory/` package and `factory.*` PostgreSQL control plane consuming frozen M1/M2/M3 handoffs. Intake/control only; no provider/workspace/systemd/external capability. | Idempotent authenticated Issue-projection/manual intake; immutable intent plus audit; `SKIP LOCKED` lease/heartbeat/reclaim/fencing; initial + at most two infrastructure retries then dead-letter; stale input supersession; kill switches; 20 global readers/10 per-repository readers/one writer; hard WIP/time/token/USD/PR-age ceilings; restart reconciliation; versioned Unix-socket API with no execution endpoints; real disposable PostgreSQL concurrency/restart exit drill. | M4 scope/design approval; database migration and recovery design review; operator supplies only disposable test DB credentials; block dispatch if M0 observation is stale/unavailable (unless named bootstrap exception); no reads of `trust_ci.*`, no Telegram/bot activation. |
| **P3 — M5 Isolated Background Execution** | Add persistent supervisor/worker host, workspace manager, immutable packet builder, adapter launcher, secret broker, network controller, artifact/manifests, and orphan reconciliation. Codex is first adapter behind a versioned model-agnostic protocol; up to 20 readers remain read/note only. | One branch/workspace per task; durable writer lease materially enforces one writer; task-to-task filesystem/artifact/state isolation; fresh packet reconstruction is digest-identical; task-scoped short-lived secrets absent from logs; default-deny network and manifest-matching allowlist; provider protocol fails closed (no silent fallback); run manifest records model/effective reasoning/prompt definition/tools/image/egress/scopes/tokens/cost/time; disconnect/restart and orphan-cleanup drills pass. | Scope/design and security/isolation approval before privileged host setup; human/operator provisions host, images, credential broker and egress policy. No Trust-CI/human/production credentials in workspaces; no Docker socket; no GitHub write capability yet. |
| **P4 — M6 Semantic Validation and Bounded Repair** | Add independent typed finding store, semantic validator and adjudicator around immutable final SHA; route repairs only to the original write owner. | Every finding maps to AC/invariant/forbidden outcome/architecture/NFR; parallel reviewers, semantic coverage, contradiction/meta-review evidence; validator sees spec/diff/deterministic and holdout evidence—not implementer reasoning; decisions are pass/repair/needs-human; at most three repair cycles; recurrence, risk/architecture/diff escalation or proposed fourth cycle goes `needs_human`; all affected evidence is regenerated on every changed SHA; PR evidence has verdict/findings/residual risk/cost. | Scope/design gate; use an independently defined validator context/provider where available; human decision for `needs_human`; prevent implementer edits to validator evidence, holdout, adjudication policy, or self-approval. |
| **P5 — M7 PR Lifecycle and Shadow Mode** | Add controlled branch/commit/PR lifecycle, source-linking, exact-SHA factory summaries, supersession and review-capacity controls. Begin shadow mode only. | Reproducible PR summary binds task/run/base/head/spec/architecture/risk/models/evidence/verdict/cost/residual risk; WIP, overlap, daily-cost/token, age and human-capacity controls prevent PR flooding; stale/superseded work reconciles; human merge decisions persist as evaluation evidence; at least one complete report per candidate low-risk class, with the 30 accepted-task minimum before M8 consideration. **Auto-merge remains disabled.** | A user must delegate each external branch-push/PR operation or an exact bounded operational equivalent; App-owned exact-SHA check and humans still decide every merge. No policy auto-promotion from shadow results. |
| **P6 — M8 Earned, Revocable Low-Risk Autonomy** | Implement durable trust profiles and only allow promotions from measured M7 cohorts for expressly approved green classes. | Trust tuple includes repo/class/agent+validator/model+prompt/policy/image/holdout digests; cohort invalidated by material tuple change; configured sample and quality thresholds, zero duplicate dispatch, no critical security miss/protected-path/secret violation, acceptable rollback/escaped-defect/false-negative rates and operational observability; only approved green classes gain the approved level; sampled human audit continues; production incident/security miss/incorrect merge/rollback/bypass/metric regression/invalid attestation demotes immediately to L0/L1. | Human approval sets class, profile and promotion thresholds; authentication/PII/payments/migrations/secrets/side-effect integrations/production/Trust CI/factory governance/holdout/branch protection/destructive work are never initially eligible. External merge remains gated by protected branch/Trust CI; autonomy does not create authority to deploy. |
| **P7 — M9 Preview, Canary and Recovery-Aware Delivery** | Build delivery environment integration only after M8 evidence. Exact merged artifact moves through preview, smoke/contract/migration/rollback checks, staging, signed promotion request, canary and metrics. | Preview/staging reproducible from exact merged SHA; artifacts/supply-chain manifest signed and verified; deterministic smoke/contract/migration/rollback checks; typed-objective business metrics; defined canary cohort, success and abort thresholds; automatic halt/rollback on health/error/latency/security/business breach; rollback exercised; deployment/canary/rollback outcomes feed the trust profile and M3 candidate learning. | Human production promotion is mandatory for red/yellow and non-approved classes; no agent bypass. Environment provisioning, signing/promotion authority, production deployment and any recovery that mutates production need exact delegated operations and applicable external approvals. |

## Minimum separate PRs

**Seven new milestone PRs are the irreducible M3→M9 minimum:** one each for M3, M4, M5, M6, M7, M8 and M9. Combining them would violate the roadmap's dependency graph, erase independent evidence boundaries, and mix factory implementation with delivery authority.

From the repository's actual current state, the minimum route to M9 is **at least ten separately gated source PRs/changes (M0, M1, M2-A, M3–M9), plus a separate M2-B/deployed-Trust-CI rollout**. M0 and M2-B include operator-owned external activation rather than ordinary product implementation; their exact number of operational change windows is not safely inferable from the repository. Any defects found in a PR are repaired in the same PR by its single writer, then its final verification/review evidence is renewed; they do not justify joining milestones.

## Meaning of “production at M9”

At M9, production does **not** mean an agent has unrestricted production credentials or may independently push, merge, deploy, approve, alter Trust CI, or bypass branch protection. It concretely means that an already protected and merged exact SHA can be rebuilt into a signed/verified artifact, deployed to an isolated preview and staging path, evaluated through explicit canary cohorts and objective-linked health/business metrics, and halted or rolled back through a rehearsed policy when thresholds breach. Delivery outcomes are durably correlated to the M8 trust-profile tuple and can immediately revoke automation.

Human production promotion remains the final authority for red/yellow and all non-approved classes. M8's narrow earned merge autonomy does not imply production-deploy autonomy; M9 retains explicit operator delegation, external approvals where required, auditability, and the App-owned exact-SHA Trust-CI merge boundary.

## Cross-cutting acceptance and release evidence

For every implementation PR: strict typed spec and exact base/head/digests; no secrets/raw reasoning in durable logs; structured correlation (`task_id`, `run_id`, repository, SHA); Prometheus-compatible queue/lease/cost/repair/PR/validator/rollback metrics; adversarial secret/network/replay/isolation tests; real PostgreSQL and process-restart drills wherever durable state is changed; immutable dependencies/images/SBOM/signature verification; README current-state and complete stack graph updated before proposing release; forward recovery/kill-switch first rather than destructive rollback. The final exact PR head requires fresh local evidence, route-selected independent review reports, the external App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run and any human-signed scopes. Local receipts, roadmap checkboxes and this report are not merge or production authority.
