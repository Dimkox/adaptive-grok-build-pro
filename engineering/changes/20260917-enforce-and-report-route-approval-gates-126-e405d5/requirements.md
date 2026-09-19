# Requirements — Enforce and report route approval gates (#126)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Every declared gate has a durable explicit approve/reject record bound to route ID, change ID, gate ID and a digest of the approved scope files.
- [x] Missing, rejected, malformed, mismatched or stale decisions block the matching approved transition or production/external-write grant/action.
- [x] `production_action_approval` remains independent from exact production grants; `migration_or_external_write_approval` remains independent from exact action/resource grants.
- [x] `grok_status.py` reports declared gates, status, scope digest, evidence path and local-only authority notice.
- [x] Legacy routes with no decision artifact report pending and never inherit approval.
- [x] Local decisions do not alter route v1, delegated grant schema v2, or Trust CI approval behavior.
- [x] The route's persisted human-gate declaration is digest-bound at change creation; missing, malformed, or changed active/package declarations fail closed even when route_id is unchanged.

## Failure and edge cases

- Route/decision mismatch: stale and denied.
- Scope digest mismatch: stale and denied.
- Unknown or malformed declared gate: invalid and protected grant/transition denied.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: exact existing grants remain required; route decisions are mutable local workflow evidence and never cryptographic identity or Trust CI authority.
- Reliability: fixed-size scope inputs and decision-list bounds; malformed data fails closed.
- Performance: five bounded file digests per gate resolution; no network or provider call.
- Observability: gate status includes exact evidence path, scope digest, target and actionable reason.
