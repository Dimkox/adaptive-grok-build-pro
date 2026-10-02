# Requirements — Implement new Factory runtime behavior for bounded pre-model result envelopes and deterministic result-channel sanitization, based on source commit aa53f300d and stacked on PR2c; add the closed schemas, Python feature modules and regression tests, excluding persistence and dispatch from this slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Valid text/JSON yields immutable deterministic envelopes; real channel inspection remains unavailable and non-consuming.
- [x] Structured Authorization/nested secrets never appear in exported envelopes; ambiguous duplicate keys fail closed.
- [x] Limits are positive bounded integers; bytes/chunks/records/depth reject deterministically without silent truncation.
- [x] Closed schemas plus semantic admission reject forged digests, invalid parity and false channel qualification.
- [ ] Existing predecessor pins and PR2c behavior remain unchanged; full verifier and independent reviews pass.

## Failure and edge cases

- Malformed UTF-8/JSON, nonfinite JSON, invalid chunk type, iterator/redaction failures and key collisions return payload-free rejection.
- A synchronous iterator may still block inside `next()`; timeout ownership remains deferred with runtime wiring.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no secret-bearing payload, authority or unsafe diagnostic export.
- Reliability: closed semantic admission and deterministic reason codes.
- Performance: bounded resource consumption for all locally controlled dimensions.
- Observability: envelope outcome/reason/policy/digests and explicit unavailable qualifications.
