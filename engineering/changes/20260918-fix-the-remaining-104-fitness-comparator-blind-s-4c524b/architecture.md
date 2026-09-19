# Architecture: complete the technical #104 comparator fix

## Scope and decision

The remaining #104 defect is an incomplete, inventory-bound JSON Schema subset. Editing the landing capability schema pulls its declared OpenAPI dependent into compatibility analysis; that OpenAPI reaches a seven-contract schema closure containing `$defs` pointers, nullable `anyOf`, and `format: date-time`. The comparator must resolve and compare this closure rather than report `unsupported` solely because supported existing constructs are missing from its model.

This change does not alter the producer-output policy or add profile facts. Whether a new capability enum member is allowed remains a separate product/governance decision: current `producer_accepted_by_old` semantics correctly reject a widened closed producer enum.

## Proposed behavior

1. Preserve the current three-valued compatibility contract. Report `compatible` only when direction-specific inclusion is proven, `incompatible` only when the supported model proves a violation, and `unsupported` when this subset cannot establish either result.
2. Extend schema resolution only within the declared contract inventory. Support strict local JSON Pointers into the current document (including `$defs`), relative references to declared schema documents, and references whose URI base is an exact declared `$id`. Never fetch a URI or resolve a file outside the inventory.
3. Validate and traverse `$defs` under the existing depth and shared parsed-node budgets. Identify references by normalized target record plus decoded pointer so alias spellings cannot bypass cycle checks. Continue to reject cycles, dangling targets, malformed escapes, path traversal, ambiguous IDs, excess depth, and exhausted budgets.
4. Support `anyOf` as a JSON Schema union. Do not use array position or `oneOf` exclusivity. For each direction, prove source-union inclusion only when every source branch is proven contained by at least one destination branch using the existing bounded schema comparison. A branch may be rejected as outside a destination when disjointness is proven; if coverage cannot be established because branches overlap or coverage would require reasoning beyond the subset, return `unsupported`. Deduplicate and canonicalize unordered alternatives, and charge normalization and pair attempts to the shared work budget with a per-union maximum of 16×16 comparisons.
5. Accept only the observed `format: date-time` on string schemas in this closure. Treat a format change as semantic contract drift (`changed_constraint`); do not claim date parsing/validation. Unknown formats remain unsupported. This matches the repository's conservative contract treatment of meaning-bearing schema metadata.
6. Apply numeric intervals only to source types `integer`/`number`, and string-length intervals only to source type `string`, matching JSON Schema keyword applicability. For mixed source type sets where interval proof would need per-type reasoning, return `unknown` rather than claiming inclusion or disjointness.
7. Keep other keywords, including `prefixItems`, outside the supported subset. Keep `$ref` authority inventory-bound and the existing object-valued enum behavior from merged PR #112 intact.

## Components and boundaries

- `.grok-stack/adaptive_grok/architecture.py`: bounded resolver, schema preflight, compatibility validation, and directional union inclusion.
- `tests/test_architecture_model.py`: pure characterization and adversarial tests for reference resolution, union semantics, formats, work budgets, and fail-closed behavior.
- `factory/contracts/**`, `architecture/rules.yaml`, and deployed Trust CI policy: unchanged.

## Data flow

Architecture fitness builds the base and head contract inventories. Each resolver validates the current document, follows only references to declared records or local JSON values, and records normalized graph identities. The OpenAPI comparator validates response schemas across the dependency closure, then applies consumer/producer direction. A composition/reference result that cannot be proven stays unsupported and fails closed.

## Compatibility semantics

For finite `const`/`enum` values, equality follows JSON Schema JSON-value semantics: integer and floating-point representations of the same JSON number compare equal, while booleans remain distinct from numbers. Object and array enum values compare recursively under the same rule.

For consumer acceptance, the required proof is `L(base) ⊆ L(head)`. For producer outputs, it is `L(head) ⊆ L(base)`. The union inclusion algorithm may conservatively return `unsupported` for a real inclusion it cannot prove; it must never report compatible from one matching pair, positional matching, or partial overlap. Ref cycles remain unsupported; no fixed-point semantics are introduced.

## Rollback and recovery

All behavior lives in one local analyzer module and tests. Revert the code/test change to restore the previous fail-closed subset. No persisted data, contract document, deployment, or external service is mutated.

## Risks and mitigations

- Union inclusion may over-accept if it mistakes partial branch overlap for containment. Use proof-producing pair checks and return unsupported for ambiguous cases; include adversarial split-coverage tests.
- Reference aliases may evade cycle/budget accounting. Normalize `(record path, decoded pointer)` and charge every resolution and branch-pair attempt to shared limits.
- Adding known schema forms could imply general JSON Schema support. Keep the allowlist narrow and explicitly test that unrelated constructs stay unsupported.
- `format` is annotation by default. Compare its declared value as contract metadata only; do not implement a validator or imply runtime enforcement.
