# Requirements — Implement repository custody for already-built deterministic v2.1.0 package bytes from source e5856acfd4bc7a186f40a740b54ec86459462db5: add ZIP and checksum, update candidate state documentation and binding tests without publication or activation

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Exact ZIP and sidecar hashes are recorded and tested.
- [x] Source commit/tree and build count are recorded.
- [x] Publication and activation remain false; delivery identities remain null.

## Failure and edge cases

- Hash drift, inherited v2.0.19 identity, or non-null delivery fields fail tests.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no external action or credential use.
- Reliability: byte hashes and source identity are exact.
- Performance: focused binding tests only.
- Observability: machine-readable candidate custody state.
