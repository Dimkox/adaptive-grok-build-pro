# Architecture — Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Native v1.5 context contracts exist, but no executable bounded FPF reader,
projection, offline replay or comparative qualification mechanism exists.

## Proposed behavior

Add optional `fpf_runtime`, accepting only frozen caller-supplied data and
emitting digest-bound sidecars without an I/O or authority surface.

## Components and boundaries

- Selector retains mandatory rules and chooses only bounded topics.
- Snapshot/reader resolve `spec://` within one tenant-bound package.
- Projection/evidence/handoff preserve semantics without a second registry.
- Adapter/evaluator/upgrade helpers report qualification honestly.

## Data flow

Frozen snapshot -> selection -> progressive read -> delivery capture -> existing
consumer/evaluator. Offline replay uses the same selected bytes.

## API and event contracts

Python-only additive API; no REST/event/schema compatibility change.

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

- Keep FPF default-off and data-only; add no DB, service, manager or executor.
- Unknown usage and unavailable live packages remain unknown/not-evaluated.

## Risks and mitigations

- Reject network, secret, grant and MCP requests at the reference boundary.
- Compare normative signals and negative controls to catch semantic loss.
- Offline replay cannot fetch; fallback applies only to a new attempt.
