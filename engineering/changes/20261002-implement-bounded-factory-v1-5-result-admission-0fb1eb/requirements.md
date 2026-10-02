# Requirements — Implement bounded Factory v1.5 result admission contract API

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] V2 is closed, immutable, digest-bound and rejects boolean fences or mismatched identity.
- [x] POST/GET authenticate exact scopes, bind repository/correlation and validate bounded inputs.
- [x] The real service returns explicit 503 with zero store/outbox/dispatch/model side effects.
- [x] Schema, OpenAPI and architecture ownership are bound by tests.
- [x] V1 and all seven unavailable/non-consuming channels remain intact.

## Failure and edge cases

- Duplicate or malformed outer JSON, unsupported media, secrets, nonfinite/invalid payloads and identity mismatches fail closed.
- Persistence absence cannot become mock-only success, `AttributeError`, generic 500 or accidental store access.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: bearer scope plus worker/owner/repository/grant identity checks precede capability failure.
- Reliability: deterministic unavailable is the only valid runtime result in this slice.
- Performance: request body remains bounded to 1 MiB; payload and metadata retain PR3a bounds.
- Observability: stable error code and response correlation header, with no sensitive echo.
