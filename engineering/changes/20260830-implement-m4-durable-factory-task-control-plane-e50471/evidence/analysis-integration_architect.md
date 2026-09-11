# Integration architecture analysis — M4 Durable Factory Task Control Plane

Route: `e50471553166`  
Change: `20260830-implement-m4-durable-factory-task-control-plane-e50471`  
Method: read-only repository and historical-plan analysis; this report is the sole write.

## Decision

**Do not implement or accept M4 intake on the routed base until the named scope-and-design gate records the exact reviewed M3 stack/head and frozen M1, M2, and M3 handoffs.** M4 is a new local control plane, not an adapter around Trust CI, GitHub, providers, systemd, or `baby-bot`.

The active route base is `1c06299894279a88b881defa3f19b004fa742223`, while the approved M4 plan is explicitly stacked on reviewed M3 head `42bd75d180beb18fae712c907c9c12d410f5c7de`. The base does not contain M2/M3 architecture/governance models or their handoff schemas. Recreating substitute handoffs in M4 would violate the roadmap requirement that M4 consume stable interfaces rather than invent replacements.

## Boundary map

```text
M1 typed spec digest ─┐
M2 architecture handoff ─┼─> authenticated local Factory intake ─> factory.* PostgreSQL
M3 governance handoff ──┤                                      ├─> local scheduler/reconciler
M0 availability observation┘                                    └─> future M5 packet reference

baby-bot (future scoped client) ── Unix socket ──> versioned public/admin API
Trust CI ── exact-SHA App verdict ──> branch protection (separate authority; no M4 edge)
```

`factory.*` is the sole operational source of truth for accepted intent, task, run/attempt, lease/fence, capacity, budget, kill, reconciliation, event, and audit state. It may retain immutable references to Trust-CI/check evidence, but cannot query or update `trust_ci.*` and cannot publish a check or attestation.

## Contract compatibility gates

| Boundary | Required compatibility gate | M4 action when unavailable/mismatched |
| --- | --- | --- |
| M1 → M4 | Valid, frozen, placeholder-free M1 change spec; canonical digest and selected acceptance IDs bind intake. | Reject intake. Do not treat the active template as authority. |
| M2 → M4 | `ArchitectureHandoffV1`: version, architecture digest, evidence digest, exact base SHA, exact head SHA. | Reject unknown version, invalid digest/SHA, missing interface; no Markdown reconstruction. |
| M3 → M4 | `GovernanceHandoffV1`: version, governance digest/evidence digest, architecture digest, exact base/head SHA. | Reject unknown version and mismatch with M2/intake. |
| M0 → M4 | Immutable availability observation fresh within 300 seconds, not health checked by proxy. | Fail closed unless a user-recorded bootstrap exception names issuer, scope, and expiry. Current M0.2 webhook evidence remains not live. |
| M4 → M5 | Only immutable, size-bounded packet reference/digest plus durable state. | No workspace, provider/repository command, task secret, or packet execution in M4. |
| M4 ↔ Trust CI | Separate packages, schemas, roles, credentials, policy/holdout, audit chain, and authority. | No `adaptive_trust_ci` import, `trust_ci.*` query, App/approval/attestation key, or check publication. |

The idempotency digest must be canonical SHA-256 over version, repository/source identity and source digest, exact base SHA, and M1/M2/M3/policy digests. Exact repeats return the active task without capacity cost; changed frozen authority or source supersedes a nonterminal predecessor rather than mutating accepted intent.

## Local API, CLI, and future `baby-bot` gate

- Default transport is HTTP over operator-created Unix socket `/run/adaptive-factory/control.sock`, group-controlled `0660`. TCP is disabled by default; M4 supports no non-loopback bind. This avoids assuming `baby-bot.service`'s VPN network namespace can reach host TCP.
- Tokens come only from root/operator-provisioned regular no-follow files of mode `0600`; compare with `hmac.compare_digest`. Never use task data, URL/query parameters, or logs as token sources.
- Token digests map to closed scopes. Versioned public/admin `/v1` comprises health, submit, show, list, and cancel; claim, heartbeat, proposal, kill, unkill/reconcile, and migrate are separately scoped. Enforce repository authorization server-side for show/list/cancel as well as intake.
- Every mutation requires `Idempotency-Key` and `X-Correlation-ID`. Persist actor, action, resource, idempotency outcome, and correlation ID with the transition/audit transaction. Echo or generate a bounded correlation ID for reads.
- Reject bodies over 1 MiB and unknown JSON; bound cursors, projections, error detail, events/audit metadata, and logs. Redact Authorization, token values, query strings, settings, and bodies.
- The deferred bot credential is only `task:submit`, `task:read`, `task:list`, and `task:cancel`; never claim, heartbeat, propose, kill, reconcile, or migrate. M4 does not read/edit/restart/deploy `/home/pall/baby-bot` or authenticate Telegram. A later bot slice must verify sender against an explicit admin allowlist before it calls M4.

## Explicit non-capabilities and operational gates

OpenAPI and CLI must contain no provider/model run, Git/worktree, GitHub fetch/push/PR/merge, deploy/release, connector, systemd, shell, repository-execution, or external-write capability. Paths such as `/v1/providers/run`, `/v1/git/push`, `/v1/pull-requests`, `/v1/deploy`, and `/v1/systemd` are forbidden.

Provider text, issue projections, notes, logs, and future adapter output are untrusted data; they cannot choose state, retry class, budget, authority, executable path, credential, network policy, or capability. Only typed authenticated control-plane commands can do so. Use factory-only migrations/runtime roles and disposable factory PostgreSQL tests—never Trust CI or production database/roles.

- PostgreSQL is the correctness boundary: `FOR UPDATE SKIP LOCKED`; 20 global readers, 10 per-repository readers, one writer; proposals/heartbeats/releases bind task, run, owner, live lease expiry, monotonic fence, packet digest, state, budget, and idempotency in one transaction.
- Only closed infrastructure classes retry (initial attempt plus two retries); third failure is `dead`. Contract/auth/policy/stale/budget/security/capability/provider-quality failure never retries implicitly.
- Missing handoff, M0 observation, usage/pricing, capacity, fence, or transition evidence fails closed. Kill switches block new claims while retaining evidence. Reconciliation is idempotent, max 100 candidates, five-second statement timeout, restart-safe.
- Real-PostgreSQL proof must cover duplicate intake, competing claims, 20/10/1 capacity, late-fence rejection after restart, retry/dead-letter, supersession, budget/WIP stop, kill retention, and reconciliation without double counters.

## Trust CI separation

M4 verification/reviews are preflight evidence only. Merge remains the deployed GitHub App-owned `adaptive-trust-ci/verified@<policy-sha12>` Check Run for the exact PR head SHA, subject to server policy/holdout and required human-signed scopes. M4 must not modify deployed Trust CI policy, holdout, images, PostgreSQL state, keys, trust stores, GitHub App configuration, branch protection, or external attestation. A local receipt/grant cannot bridge this boundary.

## Release decision

**Blocked at `scope_and_design_approval`** pending: (1) exact reviewed M3 stack/rebase decision, (2) completed frozen M1/M2/M3 authority inputs, and (3) a named time-bounded M0 bootstrap exception if M0 availability cannot be observed. After approval, encode all listed gates as contract/API/integration tests and M2 architecture rules before implementation.

## Sources inspected

- `DARK_FACTORY_ROADMAP.md` §§5–7 and M0–M5.
- `c1e4203:docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md`.
- `c1e4203:docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md`.
- Active route/M4 analyses, `AGENTS.md`, `README.md`, and M0.2 availability evidence.
