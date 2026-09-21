# Issue #163: offline RED candidate

Prepared by the selected `data_implementer` on source HEAD
`1eef8ecc1f3cdc5e397f47814cf65de14360e0c1`, route `d2e7e68e7bd5`.
No product implementation or test execution has occurred at this checkpoint.
The coordinator owns the shared CPU lane and must explicitly release a slot.

Proposed command from this worktree:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest factory.tests.test_semantic_repair_lifecycle.SemanticRepairPlanRejectionTests factory.tests.test_migrations.RepairPlanMigrationTests -v
```

Fourteen test methods exercise bounded refusal parsing, malformed wire and
document separation, successful result/request bindings, persisted deadline
result shape, post-transaction classification, unchanged service propagation,
immutable migration identities, exact reversible function text and privileges.
These are offline cases using existing fake database adapters and packaged SQL
reads. They perform no database connection, Docker, external provider or network
operation. Estimated duration is below five seconds; that is an estimate, not a
measurement. Expected RED causes are the absent plan reader/resource022 and the
current corruption classification for refused requests/malformed wire data.
Existing-success, binding and service cases are characterization controls.

Only `factory/tests/test_semantic_repair_lifecycle.py` and
`factory/tests/test_migrations.py` are changed at this checkpoint. Historical
migrations001–021, product modules, bootstrap files, route and Git HEAD remain
unchanged. The proposed PostgreSQL/upgrade tests and their execution are still
pending; no test, verification or implementation completion is claimed.
