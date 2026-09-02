# Test Plan — M6 M5-Aligned Semantic Validation

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | complete exact M5 bridge, authenticated missing facts, all mutation/substitution failures | `factory/tests/test_semantic_bridge.py` |
| P0 | append-only SQL, exact replay/divergent replay, cross-binding, role/DML separation | `factory/tests/test_semantic_postgres_integration.py`, `factory/tests/test_migrations.py` |
| P0 | closed API/OpenAPI, repository/scope isolation, assignment evidence, deterministic verdict | semantic API/OpenAPI tests |
| P0 | cycles 1..3, cycle four/recurrence/stale fence/head/policy escalation, child uniqueness | semantic repair/lifecycle tests |
| P1 | restart keyset/replay, no duplicate verdict/child, fixed low-cardinality metrics | recovery/metrics tests |
| P1 | legacy M5 behavior, installer symmetry, architecture/source/contract inventory | existing M5, installer, structure and architecture suites |

Each product slice records an observed RED and focused GREEN. SQL behavior uses a disposable local PostgreSQL instance/container when available; absence is reported as not run, never as pass. No live provider/model, network, shared DB, credential, Git, Trust CI, approval, production, or external action is exercised.

Final focused matrix includes existing M5 contracts/protocol/API/recovery/result integrity, existing M6 pure suites, bridge, semantic SQL/API/lifecycle/recovery/metrics, schema/OpenAPI closure, installer, root structure/architecture, architecture validate/drift/diagram-check, and `git diff --check`.

Connectivity: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ [design](../../../docs/superpowers/specs/2026-09-01-m6-semantic-validation-provisional-design.md) ↔ [plan](../../../docs/superpowers/plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [package](brief.md) / [release](release.md) / [rollback](rollback.md) / [evidence](evidence/README.md).
