# Architecture analysis — issue #104 continuation

## Finding

The object-valued enum part of #104 was already addressed by the merged #112 change (`b1ac155`). In this routed continuation, the capability schema itself now passes `_unsupported_schema`; the remaining `unsupported_openapi_construct` for `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1` is caused by the other response schema referenced from `landing-failover.v1.json`: `landing-attempt-status.v1.schema.json` uses `anyOf` for nullable `reason_code`, `artifact`, `provider_evidence_digest`, and `observation`. The current bounded subset does not admit the `anyOf` keyword. I reproduced this with `compare_contracts(record, record, "bidirectional", base_inventory=inventory, head_inventory=inventory)`: it returns `unsupported_openapi_construct`; direct checks show the capability ref supported and attempt-status ref unsupported.

## Relevant implementation and contracts

- `.grok-stack/adaptive_grok/architecture.py:1033-1058` defines the closed JSON Schema keyword subset. It includes `oneOf`, `allOf`, `if`, and `then`, but omits `anyOf`.
- `.grok-stack/adaptive_grok/architecture.py:1487-1524` validates composition arrays as non-empty, at most 16 object schemas, then recursively preflights their children. The same bounded rule should cover `anyOf`.
- `.grok-stack/adaptive_grok/architecture.py:1334-1374` performs schema validation and safe reference expansion under `MAX_DEPTH` and the resolver's shared `MAX_PARSED_NODES` budget (`:21-22`, `:1148-1150`). External references must resolve to declared contract inventory entries (`:1216-1231`); cycles and excessive depth are rejected (`:1365-1374`).
- `factory/contracts/openapi/landing-failover.v1.json:49-51` references `../jsonschema/landing-backend-capability.v1.schema.json` and `:127-129` references `../jsonschema/landing-attempt-status.v1.schema.json`. The latter contains four `anyOf` nullable unions in `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json:27-73`.
- `.grok-stack/adaptive_grok/architecture.py:1995-2047` validates OpenAPI 3.1 documents and every component schema; `:2252-2262` / `:2265-2340` compare operations and schema directions after preflight.
- `.grok-stack/adaptive_grok/architecture.py:1602-1764` is the bounded directional comparator. It already treats any changed `oneOf`/`allOf`/`if`/`then` semantics conservatively as `changed_constraint` (`:1649-1651`), while recursively comparing branches for directional findings (`:1738-1764`). `enum` members are compared using canonical values at `:1676-1686`; after #112, bounded object-valued members participate without changing producer-output rules.
- `tests/test_architecture_model.py:2610-2670` characterizes supported bounded rich schemas and conservatively incompatible composition changes. `tests/test_architecture_model.py:2141-2222` already verifies fail-closed unsupported OpenAPI constructs.

## Smallest safe recommendation

Add `anyOf` to the same closed, bounded composition subset, not to the producer's capability facts or output policy:

1. Include `anyOf` in `_SUPPORTED_SCHEMA_KEYS` and validate it with the existing composition-array shape/size/depth/node-budget logic.
2. Include it in the comparator's canonical composition-change check and branch-wise recursive comparison, with exactly the same conservative semantics as `oneOf`/`allOf`: any change produces `changed_constraint` (therefore incompatible), while unchanged branches continue into normal consumer/producer checks. Do not claim full logical-equivalence reasoning for arbitrary unions.
3. If any accepted `anyOf` schema may occur in an event contract, include its branches in bounded event-meaning traversal as well, so descriptive meaning extraction does not silently skip a now-supported branch.
4. Add focused tests for a self-identical OpenAPI inventory containing the actual referenced nullable shapes (including the attempt-status ref), for a changed `anyOf` branch remaining incompatible, and for work-limit/depth overflow remaining `unsupported`. Keep existing object-enum producer widening tests intact.

This reuses extant safety limits and conservative composition policy. It does not alter producer-output policy, introduce profile facts, widen accepted OpenAPI constructs beyond this JSON Schema composition keyword, or add a dependency. Do not simply whitelist the landing contract/digest or downgrade `unsupported`: that would leave future referenced-schema changes unexamined.
