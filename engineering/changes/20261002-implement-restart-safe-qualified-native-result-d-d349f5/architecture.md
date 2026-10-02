# Architecture — Implement restart-safe qualified native result dispatch

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Migration 024 durably admits immutable ResultEnvelopeV2 records but never creates outbox rows.

## Proposed behavior

Migration 025 adds a dormant, separately credentialed handoff state machine. It fails if any
unexplained pre-025 outbox row exists and never backfills or enqueues.

## Components and boundaries

- PostgreSQL owns immutable source identity, claims, leases, budgets and terminal state.
- PostgresResultDispatcherStore assumes only factory_result_dispatcher.
- UdsResultHandoffClient can reach one exact mode-0600 same-UID Unix socket.
- No provider/model SDK, TCP, DNS, proxy, redirect or live interception boundary exists.

## Data flow

Future qualified enqueue authority (absent) → SKIP LOCKED claim → mark sending → one POST.
Any post-send uncertainty becomes observation-only GET; exhaustion becomes blocked.

## API and event contracts

native-result-handoff.v1 is an internal UDS JSON Schema, not a public HTTP or model API.
result-channel-qualification.v2 keeps every one of the seven channels unavailable.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

- Composite source/outbox FK plus live authority checks at claim/start/record.
- Separate persisted send and observation counters with a monotonic unknown state.
- Lease strictly exceeds HTTP timeout plus processing margin.

## Risks and mitigations

- Ambiguous remote effects: never POST again; observe exact deterministic operation only.
- Credential/socket substitution: descriptor-safe private token and inode-bound trusted UDS.
- Upgrade drift: additive 025, pre-row fail-closed, immutable 024.
