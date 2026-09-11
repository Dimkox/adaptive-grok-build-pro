# Documentation research — M4 Durable Factory Task Control Plane

**Route:** `e50471553166`  
**Mode:** repository-local, read-only analysis (except this report)  
**Conclusion:** M4 has a detailed approved design and implementation plan on the reviewed M3 stack, but the route base does not contain the required M2/M3 handoff interfaces. This is a scope-and-design gate: implementation must stack on the exact M3 baseline or receive a recorded, versioned compatibility decision. It must not invent replacement handoffs.

## Authority and document reconciliation

| Authority | Location | Finding / binding requirement |
| --- | --- | --- |
| Repository operating contract | `AGENTS.md` | PR-only delivery; `factory.*` must remain separate from `trust_ci.*`; no GitHub Actions; one write owner; source changes require `python3 scripts/grok_verify.py --mode pr`, route reviews, fingerprint-bound receipts, then external App-owned exact-SHA Trust CI for merge. README must match VERSION/tree and retain a complete graph before release. |
| Program roadmap | `DARK_FACTORY_ROADMAP.md`, §§5–7 and M4 | M4 is a separate durable factory control plane. It uses `factory/`, `factory.*`, authenticated Issue/manual intake, idempotency, PostgreSQL `FOR UPDATE SKIP LOCKED`, leases/reclaim/dead letter, 20/10/1 capacity, kill switches, budgets, append-only audit, reconciliation, and a Trust-CI-availability gate. It explicitly forbids using `trust_ci_jobs` as the queue. |
| Frozen M4 design | `feature/model-agnostic-factory:docs/superpowers/specs/2026-08-26-model-agnostic-autonomous-factory-design.md` | This is the detailed control-plane design. It makes PostgreSQL `factory.*` operational truth, requires M1/M2/M3 handoffs, fencing on every worker proposal, typed retry classes, fail-closed accounting, bounded/no-secret durable storage, and no M5+ execution or external-write capability. Its own status says the document freezes scope/interfaces and does not itself authorize implementation; the current user task/route is the later implementation authorization subject to named gates. |
| Approved implementation plan | `bc5ef65` / `feature/model-agnostic-factory:docs/superpowers/plans/2026-08-28-m4-durable-factory-control-plane.md` | Exact intended file map, contracts, limits, migrations, API/CLI surface, test sequence, and final evidence flow. It says M4 stacks on the **exact reviewed M3 head**. It is the most precise source when it narrows roadmap language. |
| Route and active change | `.grok-stack/runtime/active-route.json`; `engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471/` | Route is high-risk data/API/security, selects `data_implementer`, and has scope/design, migration/external-write, and production-action gates. Current package documents are generated stubs: `change-spec.yaml` has template values and all Markdown plans are placeholders, so they are not frozen M1 authority. |

## Prerequisite interfaces and current availability

M4 intake must bind a valid frozen M1 specification plus M2 and M3 versioned handoffs; all relevant architecture/base/head digests must agree. `DARK_FACTORY_ROADMAP.md` prohibits M4 from replacing these interfaces with Markdown-derived values.

| Prerequisite | Required repository contract | Route-base state (`1c062998`) | Reviewed stack state |
| --- | --- | --- | --- |
| M1 typed intent | `schemas/change-spec.schema.json`, `.grok-stack/adaptive_grok/spec.py`, `scripts/grok_spec.py`, `tests/test_change_spec.py`; schema v1 is closed and supports IDs/evidence/approval scopes. | Present. The active M4 spec is invalid/placeholder-filled and cannot be used as its frozen input. | Present in M3 stack. |
| M2 architecture | `ArchitectureHandoffV1`: five fields in the M4 plan — version, architecture digest, architecture evidence digest, exact base SHA, exact head SHA. Architecture model/rules/fitness are under `architecture/`, `schemas/`, `.grok-stack/adaptive_grok/architecture.py`, scripts/tests. | **Absent:** no `architecture/system.yaml`, `architecture/rules.yaml`, or architecture module. | Present on `milestone/m3-controlled-knowledge-debt`; architecture evidence produces v1 digests/bindings. |
| M3 governance | `GovernanceHandoffV1`, schema `schemas/governance-handoff-v1.schema.json`: `governance_contract_version`, governance/evidence digests, architecture digest, exact base/head SHAs. | **Absent:** no governance module or handoff schema. | Present on M3 head (`d4cc01f`); schema is closed with exactly the six fields above. |
| M0 availability | Current observed authority is required and must be no older than 300 seconds; absent live authority needs a named, issuer/scope/expiry-bounded bootstrap exception. | README says the App-owned check is **not live** and PR #2 is a bootstrap exception. | Planning docs assumed an M0-established state; this cannot be silently transferred to the route base. |

**Required ruling before code:** select the exact reviewed M3 commit/stack strategy and frozen M1/M2/M3/M0 digest evidence, or explicitly approve a versioned compatibility handoff with its scope and expiry. The route’s named `scope_and_design_approval` gate is therefore materially active.

## M4 implementation contract

- New isolated service boundary only: `factory/pyproject.toml`, `src/adaptive_factory/`, `sql/resources`, `config`, tests, `compose.yaml`, and `README.md`; never add a root packaging marker.
- `TaskIntakeV1` is closed and canonical: repository/source identity and digest, route/change IDs, exact base SHA, M1 spec, M2/M3 handoffs, policy digest, fresh M0 observation, sorted unique acceptance IDs, and bounded limits. Canonical SHA-256 JSON produces immutable intent/idempotency digests. Unknown versions/fields, non-NFC or excessive values, invalid/dirty SHAs/digests, mismatched handoffs, stale authority, and ceilings above policy fail closed.
- State surface is `inbox`, `triaged`, `waiting_design_approval`, `queued`, `leased`, `analyzing`, `implementing`, `verifying`, `reviewing`, `ready_for_human`, and exceptional `retry`, `needs_human`, `dead`, `cancelled`, `superseded`. `pr_open`, `merged`, and delivery states are rejected future values in M4. Provider/untrusted output cannot choose a state or failure/retry class.
- Three immutable, contiguous, checksum-locked factory-only migrations create accepted intent/task/event/audit; run/attempt/fence/capacity; and budgets/usage/kills/reconciliation. Apply under a factory advisory lock; never reuse a Trust CI role, database URL, migration registry, table, credential, key, policy, holdout, or App identity.
- PostgreSQL claim is atomic: stable capacity locks, kill-switch check, `FOR UPDATE SKIP LOCKED`, monotonic fence, run/attempt/allocation, lease/state/event/audit. Every heartbeat/proposal/usage/phase/terminal/release validates task/run/owner/fence/live expiry/packet digest/current state/deadline/budget/proposal key in one transaction.
- Exact limits: readers ≤20 globally and ≤10 per repository; live application writers ≤1; lease 30–300 seconds; wall time ≤14,400s; cost ≤25,000,000 USD micros; tokens ≤2,000,000; output ≤10MB; events ≤100,000; infrastructure retries are initial attempt + at most 2; semantic repair capacity is 1–3 but execution is deferred.
- Only four typed infrastructure classes retry: database unavailable, worker lost, provider transport unavailable, and temporary resource exhaustion. The third infrastructure failure becomes `dead`; invalid/auth/policy/security/budget/stale/protocol/provider-quality conditions do not retry implicitly. Missing trustworthy usage/price blocks new reservation.
- Global/repository kills stop **new claims** but preserve durable evidence. Audit is insert-only hash chained. Reconciliation is ordered, idempotent, ≤100 candidates, 5-second statement-timeout-bounded, and covers expired leases, orphan allocations, deadlines/accounting/stale inputs, and incomplete terminal projections.

## Local API / CLI and security boundary

The exact plan resolves the roadmap’s generic “authenticated manual API/CLI” into a default Unix-domain-socket interface (operator-created `0660` socket) with no TCP/non-loopback bind. Token files must be regular/no-follow/`0600`, scope-mapped, compared with `hmac.compare_digest`, and never logged. Request bodies are ≤1 MiB; unknown JSON, unbounded cursors/projections, credentials, bodies, and query strings are rejected/redacted.

Public/admin API is versioned `/v1`: health, submit, show, list, cancel. Worker/operator endpoints are separately scoped: claim, heartbeat, proposal, kill, reconcile. CLI is `migrate`, `intake`, `show`, `list`, `cancel`, `kill`, `unkill`, `reconcile`. The OpenAPI file is `factory/contracts/openapi/factory-control.v1.json`. No endpoint may run a provider, repository/Git/GitHub/PR command, deploy, install/restart systemd, or use Trust CI authority. A later `baby-bot` client is limited to submit/read/list/cancel; its integration is expressly out of scope.

## Dependencies, packaging, and PostgreSQL test expectation

- Planned factory pins: Python `>=3.11`, FastAPI `0.128.2`, Uvicorn `0.48.0`, psycopg `3.3.4`, PostgreSQL `15+`, canonical JSON, `unittest`. Existing scoped precedent is `trust-ci/pyproject.toml`, which pins the same FastAPI/Uvicorn/psycopg versions (plus Trust-CI-only cryptography). Do not inherit Trust CI functionality merely because its pins/patterns are reusable.
- `trust-ci/compose.test.yaml` and `trust-ci/tests/test_postgres_integration.py` are a mechanical test reference only: M4 needs its own `FACTORY_TEST_DATABASE_URL`, disposable factory database/schema/roles, and may not truncate/query `trust_ci.*`.
- Real PostgreSQL is a mandatory M4 exit gate, not a mock substitute. It must prove duplicate intake, competing claim, exact 20/10/1 ceilings, late-fence rejection, initial-plus-two retry then dead, stale supersession, WIP/budget stopping, kill evidence retention, restart/reclaim, and idempotent reconciliation. A bounded two-process restart probe is planned.
- Focused sequence from the plan: contracts → state → migrations → service/intake + PostgreSQL intake → lease/capacity/fence → retry/budgets → kill/reconciliation/restart → API/CLI → M2/M3 architecture integration. After final product changes, run exactly one root `python3 scripts/grok_verify.py --mode pr`, then all route-selected code/test/security/data/release reviews against that fingerprint.

## Release / README obligations

`README.md` currently identifies product `2.0.12`, Trust CI `2.1.0`, and only Trust CI/PostgreSQL 17 in the complete graph. If M4 lands, README must state that `factory/` is a **source-only local control plane**, locate its isolated DB/API boundary and its non-capabilities, keep M5 absent, preserve the product VERSION, and update the complete graph so every core node has a `---` edge to every other core node. `tests/test_structure.py` enforces current version identity and graph completeness.

Rollout is local/disposable only: back up a disposable/staging `factory` schema, migrate under advisory lock, manually start the API, exercise a synthetic intake/claim/heartbeat/release/kill/restart/reconcile path. Before first intake, only the explicitly named disposable schema may be removed; after intake, no down migration—kill/stop claims, preserve audit/evidence, restore separately or forward-fix with migration `004+`. No external write, production mutation, GitHub Issue webhook registration, deploy, PR/merge/publish, or systemd activation is authorized here.

## Stale paths, contradictions, and required cleanup

1. **Blocking base/plan mismatch:** plan/design paths exist on `feature/model-agnostic-factory` / `milestone/m3-controlled-knowledge-debt`, not route base `1c062998`; M2/M3 are missing in the active tree. Do not copy their field names into an ad hoc local replacement.
2. **Historical evidence destination is stale:** plan tasks 10–11 name `engineering/changes/20260826-model-agnostic-autonomous-factory-355689/evidence/...`; the active route’s evidence belongs under `engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471/evidence/`. Historical package content remains reference-only.
3. **Active package is unscoped:** all change-package Markdown files are placeholders and `change-spec.yaml` contains `{{OBJECTIVE_STATEMENT}}` / `UNKNOWN` / empty criteria. It cannot pass M1 validation or satisfy the scope/design gate until completed.
4. **M0 wording conflicts across refs:** the detailed design claims M0 established, whereas route-base README explicitly says the App-owned check is not live. The active M4 contract must use a fresh observation or an explicit bootstrap exception, never rely on the old planning assertion.
5. **Transport wording is resolved, not a real conflict:** roadmap says authenticated manual API/CLI; plan sometimes says “localhost HTTP,” then mandates Unix socket and disallows TCP/non-loopback. Implement the later detailed Unix-socket contract.
6. **PostgreSQL versions are compatible:** plan requires 15+; README’s Trust CI topology says PostgreSQL 17. Factory test/runtime must remain separate, but 17 meets the planned minimum.
7. **README is necessarily stale for M4 until implementation is integrated.** Its graph/current-state map currently contains no factory node/boundary; update only with the final source tree, not prematurely.

No upstream research was needed: all design, plan, handoff, packaging, verification, and test facts are available in repository history/current tree.
