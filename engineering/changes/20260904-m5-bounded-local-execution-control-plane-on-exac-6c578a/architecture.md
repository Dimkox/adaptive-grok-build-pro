# Architecture — M5 bounded local execution control plane on exact M4 67dc4dd

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Exact M4 `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` supplies durable task/run/attempt/event truth, authenticated UDS control API, immutable history, lease/fence/capacity/budget/accounting controls, transitions, reconciliation, and migrations `001`-`013`. It has no trusted M5 execution surface.

## Proposed behavior

Add a disabled-by-default execution capability that consumes, but never replaces, M4 authority. Reuse final M5 semantics from `3940267ac5754ad07a047894102015d33eb759b1` through a selective semantic port; no whole-tree merge or overlapping file replacement is permitted.

## Components and boundaries

| Boundary | Responsibility |
| --- | --- |
| `execution_contracts.py` and four JSON Schemas | Closed immutable packet, manifest, invocation/event, and workspace-result representations with separate canonical digests. |
| `protocol.py` and `adapters/` | Strict bounded UTF-8 JSONL projection for exact offline Codex/Grok fixtures; no invocation capability. |
| `brokers.py` and `workspace.py` | Capability-shaped proposal validation, opaque workspace handles, trusted snapshot and artifact-attestation boundaries. |
| Migrations `014`-`017` and additive store methods | Canonical persistence, disjoint attestor authority, atomic terminalization, recovery claims/outcomes, and metrics. |
| Additive service/API/server integration | Authenticated repository-scoped orchestration; execution routes are absent unless complete trusted composition is ready. |
| Execution OpenAPI v1/v2 | Six logical operations per version; v2 adds the factual finalized result while the M4 control document remains unchanged. |

## Data flow

`authenticated worker -> M4 claim/lease/fence -> trusted exact execution selection -> immutable packet and manifest -> bounded stages/proposals -> trusted snapshot and artifact attestations -> atomic workspace result and M4 disposition -> bounded recovery/cleanup`.

Request and provider data are never authority inputs. Every write is rebound to persisted repository, task, run, owner, role, fence, allocation, packet, manifest, workspace, deadline, budget, and idempotency identities.

## API and event contracts

Keep `factory-control.v1.json` byte-identical. Add separate closed `factory-execution.v1.json` and additive `factory-execution.v2.json`, backed by the four declared JSON Schemas. Canonical stage/proposal/recovery facts are append-only, bounded, correlated, retry-safe, and versioned; provider-native records do not become business authority.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none currently published.
- Applicable canonical example IDs/versions: applicability is rederived by architecture fitness; no example is declared authoritative here.
- Open or overdue debt IDs: none currently published.
- Expected governance handoff or receipt impact: final architecture and contract inventory must pass on the exact product tree.

## Bitrix-specific impact

- Modules/events/agents/components affected: not applicable; the repository is not a Bitrix product.
- Cache and managed cache impact: none.
- Installation/update/uninstall impact: no activation is authorized; source and forward migrations only.
- Core modification: forbidden unless explicitly approved.

## Decisions

- Exact M4 wins every conflict; canonical M5 is source material, not ancestry or evidence.
- Migrations `014`-`017` are one ordered forward unit and `001`-`013` are immutable.
- Repository identity is the existing tenancy boundary; no unproven organization hierarchy is introduced.
- Built-in adapters remain `execution_eligible=false`; tests may inject closed deterministic profiles and brokers.
- Terminal disposition and recovery remain server-owned and factual.

## Risks and mitigations

- M4 regression: additive grafts plus exact control/migration regression assertions.
- Cross-tenant or stale-fence mutation: server-side repository and durable authority checks in service and SQL.
- Partial/fabricated terminal state: one fenced transaction requiring trusted snapshot and attestation evidence.
- Migration incompatibility: PostgreSQL 17 guard, advisory lock, timeouts, precondition gates, checksums, and forward-fix only.
- Accidental capability exposure: disabled default and fail-closed readiness before UDS exposure.
