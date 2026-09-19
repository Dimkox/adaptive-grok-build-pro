# #104 repository exploration

## Finding

The contract-fitness failure is caused by a referenced schema construct the bounded comparator does not support yet. `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1` in `architecture/system.yaml:373-378` references `factory/contracts/openapi/landing-failover.v1.json`; its `200` response at `factory/contracts/openapi/landing-failover.v1.json:123-131` references `../jsonschema/landing-attempt-status.v1.schema.json`. That schema uses `anyOf` for nullable `reason_code`, `artifact`, `provider_evidence_digest`, and `observation` (first occurrence at `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json:43-53`).

The comparator's closed keyword allowlist includes `oneOf`, `allOf`, `if`, and `then`, but not `anyOf` (`.grok-stack/adaptive_grok/architecture.py:1044-1058`). `_unsupported_schema` rejects unknown keys (`:1354` onward), and its composition traversal only handles `oneOf` and `allOf` (`:1487-1520`). Consequently `_openapi_schemas` rejects the failover OpenAPI document as `unsupported_openapi_construct`, which `compare_contracts` maps to status `unsupported` (`:2567-2573`). The direct test probe confirmed `_unsupported_schema` returns true for the attempt-status reference and `_openapi_schemas` returns `None` for the failover OpenAPI document.

When the capability contract changes, `_contract_dependency_closure` correctly adds declared reverse-reference dependents (including the failover OpenAPI record) to the comparison scope (`.grok-stack/adaptive_grok/architecture_fitness.py:905-925`). Fitness then compares the dependent OpenAPI record against its unchanged predecessor; unsupported comparator semantics become a finding (`:875-885`). This is why a harmless capability-schema edit can make the fitness result `unsupported`, even though the capability schema itself is supported.

## Minimal characterization

Using `load_architecture('.')`, `contract_inventory('.')`, and `compare_contracts` against the existing inventory, I copied the `CONTRACT-FACTORY-LANDING-BACKEND-CAPABILITY-V1` document, appended text to its root `description`, and constructed base/head inventories differing only in that referenced schema. Comparing the unchanged `CONTRACT-FACTORY-LANDING-FAILOVER-OPENAPI-V1` record with `bidirectional` compatibility returned:

```text
description_only unsupported ('unsupported_openapi_construct',)
```

The same result occurs for an optional-property addition. A focused regression should exercise the actual architecture-fitness closure with a baseline commit and a head commit changing only the capability schema; assert that the dependent failover OpenAPI is included in `scanned_scope` and the result is no longer `unsupported` for a compatible change. A separate change to one composition branch should prove the new `anyOf` comparison reports compatibility/breakage accurately, rather than accepting a blanket equality shortcut.

## Existing test gap and affected files

- `tests/test_architecture_fitness.py:4282-4345` proves the landing contracts can be *added* and are in the resulting scan scope. It does not compare a changed landing schema to an existing baseline: `_contract_compatibility` skips comparison for records with `old is None` (`.grok-stack/adaptive_grok/architecture_fitness.py:870-872`). Thus this test does not detect the unsupported referenced composition.
- Primary implementation: `.grok-stack/adaptive_grok/architecture.py` (closed schema keywords, recursive validation, compatibility comparison and OpenAPI preflight).
- Fitness integration/closure: `.grok-stack/adaptive_grok/architecture_fitness.py` (dependency closure is already present; add/extend coverage here).
- Regression target: `tests/test_architecture_fitness.py`.
- Existing input demonstrating the unsupported construct: `factory/contracts/jsonschema/landing-attempt-status.v1.schema.json`; no contract change is required to reproduce the blind spot.

No product files were edited for this analysis.
