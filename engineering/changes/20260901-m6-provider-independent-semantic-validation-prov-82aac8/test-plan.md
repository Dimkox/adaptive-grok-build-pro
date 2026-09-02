# Test Plan — M6 Provisional Slice

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | closed bounded schema/parser parity, canonical digest stability, exact requirement coverage | `factory/tests/test_semantic_contracts.py` |
| P0 | validator separation, stale binding, deterministic anomaly grouping and precedence | `factory/tests/test_semantic_adjudication.py` |
| P0 | same writer/fresh context cycles 1..3; recurrence and cycle four escalation | `factory/tests/test_semantic_repair.py` |
| P1 | risk/diff/architecture/authority/base/budget/deadline/writer escalation matrix | `factory/tests/test_semantic_repair.py` |
| P1 | current M6 docs/contracts stay linked and factual | `tests/test_structure.py`, `tests/test_architecture_model.py` |

Focused command: `cd factory && uv run python -m unittest tests.test_semantic_contracts tests.test_semantic_adjudication tests.test_semantic_repair -v`. Root structure/architecture tests verify README↔roadmap↔spec/plan/package/release/rollback/evidence connectivity and the factual contract graph. No live provider, network, database, credential, holdout, or systemd test is authorized.
