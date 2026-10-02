# Architecture — Implement bounded Factory v1.5 result admission contract API

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

PR3a provides a hardened offline V1 sanitizer and declares all seven runtime channels unavailable. No durable result-admission store exists.

## Proposed behavior

Add an identity-bound V2 and local HTTP seam. Validate contracts and authority completely, then stop at an explicit unavailable exception before store or dispatch.

## Components and boundaries

- `result_contracts.py` owns V1/V2 semantic admission; V1 is unchanged.
- `result_broker.py` optionally emits V2 while preserving V1 callers and non-consuming inspection.
- `api.py` owns strict HTTP parsing; `service.py` owns authority/identity validation and the unavailable boundary.

## Data flow

Bearer/auth headers → strict closed JSON → V2 semantic validation → lease/repository binding → deterministic 503. There is no persistence, replay, outbox or transport edge.

## API and event contracts

Canonical files are `result-envelope.v2.schema.json` and `factory-result-admission.v1.json`; OpenAPI references the JSON Schema rather than duplicating it. No event is emitted.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `FIT-BOUNDED-FACTORY-CONTRACT-CHANGE`, `FIT-BOUNDED-FACTORY-TEST-CHANGE`, `FIT-OPENAPI-BIDIRECTIONAL`.
- Applicable canonical example IDs/versions:
- Open or overdue debt IDs:
- Expected governance handoff or receipt impact:

## Bitrix-specific impact

- Modules/events/agents/components affected:
- Cache and managed cache impact:
- Installation/update/uninstall impact:
- Core modification: forbidden unless explicitly approved.

## Decisions

Expose explicit unavailable routes instead of success-shaped mocks so clients can integrate authentication and validation without mistaking the seam for durable replay.

## Risks and mitigations

Contract drift is blocked by schema/OpenAPI/architecture tests. Future persistence must be a separate slice with replay/outbox/concurrency evidence.
