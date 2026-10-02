# Requirements — Implement restart-safe qualified native result dispatch

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Migration 025 is additive, pre-row fail-closed and never enqueues.
- [x] Composite identity and current run/fence/packet/open-attempt authority fence every handoff.
- [x] One POST precedes observation-only recovery with finite persisted budgets.
- [x] UDS configuration is default-off, bounded and isolated behind a dedicated database login.
- [x] All seven qualification-v2 channels remain unavailable and PR235 admission stays dormant.

## Failure and edge cases

- Mismatched identity, stale claim, expired lease and closed attempt reject.
- Redirect/auth/5xx, duplicate/malformed/oversize/non-JSON responses remain unknown.
- A crash after sending never returns the row to pending.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no TCP/provider path; least-privilege DB and private local token/socket.
- Reliability: durable leases/counters/deadline; restart preserves deterministic operation identity.
- Performance: batch max 100, partial dispatch index and SKIP LOCKED.
- Observability: payload-free phase, reason, attempts and observation metadata.
