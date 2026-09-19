# Tasks — complete the technical #104 comparator fix

- [x] Freeze the current contract/dependency closure and expected outcomes in the change package.
- [x] Reproduce that adding root `description` to capability schema makes its dependent failover OpenAPI return `unsupported_openapi_construct`.
- [x] Analyze union and reference semantics with route-selected independent agents.
- [x] Add failing directional, reference, format, budget, and dependency-closure regressions; red run observed the expected unsupported results before implementation.
- [x] Implement bounded resolver and `anyOf` inclusion semantics in the sole writer.
- [x] Run focused comparator tests and confirm remaining producer widening stays incompatible.
- [x] Run the full architecture-model module and architecture fitness CLI against the route base.
- [x] Fix review-discovered nested `date-time` format drift, including concurrent `minLength` changes; exact red regression failed before the fix in both directions, then passed fail-closed.
- [x] Fix directional `anyOf` proofs for unconstrained source branches versus finite `enum`/`const` destinations; red regressions failed before the fix and pass with unknown/unsupported where inclusion is not proven.
- [x] Treat integral floating JSON numbers as integer values in scalar inclusion proofs; regression reproduced false disjoint for `const: 2.0` versus `type: integer` before the fix.
- [x] Gate numeric and string interval proofs by JSON Schema type applicability; regressions reproduced false disjoint for ignored `minLength`/`maxLength` on integers and `minimum`/`maximum` on strings before the fix.
- [x] Compare finite JSON Schema values using numeric JSON equality; regressions reproduced false incompatibility for `const: 1` vs `const: 1.0` and `enum: [1]` vs `enum: [1.0]` before the fix.
- [ ] Run the route-selected full PR verifier once on the final tree.
- [ ] Run code, test, and security reviews against the verified tree; persist reports and record exact receipts.
- [ ] Confirm `grok_status.py --json` has zero evidence gaps and record unresolved product gate for the v1 producer-policy choice.
