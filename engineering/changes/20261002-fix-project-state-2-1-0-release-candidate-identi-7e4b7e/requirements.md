# Requirements — Fix PROJECT_STATE 2.1.0 release candidate identity so the new source-only candidate has no artifact hashes while preserving the immutable 2.0.19 artifact record

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Published/latest identity is v2.0.19 with its immutable release metadata.
- [x] Local candidate identity is v2.1.0 on `release/2.1.0-rc` and has no artifact or delivery claims.

## Failure and edge cases

- Candidate fields must not inherit v2.0.19 hashes, sizes, merge SHA, PR, or check status.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: do not manufacture trust or publication evidence.
- Reliability: binding tests rederive state and manifest relationships.
- Performance: documentation/state-only.
- Observability: current and published identities remain separately machine-readable.
