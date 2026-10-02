# Architecture — Implement durable Factory v1.5 result admission persistence

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

PR234 validates and authorizes V2 admission but returns 503 before persistence.

## Proposed behavior

Migration 024 installs immutable result, command replay and dormant outbox tables. The PostgreSQL function owns the atomic authority/replay decision; the Python store validates returned bindings.

## Components and boundaries

API retains parsing/authentication. Service binds actor, grant and repository. Store owns transactions. SQL revalidates canonical wire data and current-run authority. No dispatcher consumes the outbox.

## Data flow

POST -> strict V2/service grant checks -> one SQL transaction -> immutable result plus command record -> created/replay response. GET -> repository authorization -> repository+task+digest query.

## API and event contracts

The byte-stable v1 OpenAPI remains as the unavailable seam; a new v2 snapshot adds 200/404/409 while retaining 503 for database unavailability. No event contract or publication is introduced.

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

Adapt source `efc003f57` instead of cherry-picking; strengthen tenant reads, structured payload validation, rollback and actual-restart evidence.

## Risks and mitigations

Lock contention is bounded by two transaction advisory locks and statement timeout tests. Schema rollback is forward-fix because admitted evidence is immutable and non-destructive.
