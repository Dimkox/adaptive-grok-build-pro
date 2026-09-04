# Test plan — M6 bounded semantic validation on exact M5 85cd434

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Closed contracts, exact M5 bridge, deterministic contradiction precedence, cycles 1-3, fourth-cycle escalation | dedicated pure semantic tests |
| P0 | Disjoint database capabilities, append-only exact replay, repair source/claim binding, schema-17 to 018 preservation | focused disposable PostgreSQL 17 tests |
| P1 | Additive API/server composition and preservation of current M4/M5 surfaces | semantic service/API/store/server tests plus focused M5 seams |
| P1 | Architecture ownership and generated-artifact parity | focused architecture validation |

## Automated checks

- Unit: `test_semantic_contracts`, `test_semantic_adjudication`, `test_semantic_bridge`, `test_semantic_repair`.
- Integration: `test_semantic_persistence`, `test_semantic_store_runtime`, `test_semantic_service_api`, `test_semantic_repair_lifecycle`.
- Contract: seven JSON Schemas plus six additive semantic operations in the existing control OpenAPI.
- E2E: one disposable PostgreSQL 17 schema-17 upgrade, replay/role/repair proof; no live provider.
- Static analysis: syntax, JSON/spec validation, migration/architecture inventories, and diff checks only.

## Manual checks

- Confirm exact M5 migrations `001`-`017` and execution v1/v2 contracts are byte-identical to the predecessor.
- Confirm no provider/network/credential/systemd/external path becomes enabled by default.
