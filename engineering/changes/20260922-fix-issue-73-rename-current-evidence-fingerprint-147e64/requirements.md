# Requirements — Fix issue #73: rename current evidence fingerprint fields that trigger GitGuardian secret heuristics while preserving historical evidence immutability and schema/test compatibility.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given explicit scope/design approval, new delegated grants emit `grant_binding_digest`
  instead of `tree_fingerprint` while legacy schema-version-2 grants remain readable.
- [x] Grants containing both field names fail closed instead of selecting an ambiguous binding.
- [x] Given the current tree, when historical evidence is inspected, then the two immutable
  artifacts containing `authorization_tree_fingerprint` remain unchanged.
- [x] The current delegated-grant producer and both policy/publication consumers are covered by focused migration tests.

## Failure and edge cases

- Historical evidence must not be rewritten.
- A real credential must not be allow-listed or renamed as a workaround.
- External GitGuardian behavior cannot be declared fixed by local tests alone.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: named security/design gate; no key material or trust-store changes.
- Reliability: compatibility reader/schema coverage required for any approved rename.
- Performance: no runtime impact expected.
- Observability: focused detector-shaped regression and explicit external disposition.
