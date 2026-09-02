# M5 Evidence Index

Navigation: [package](../brief.md) ↔ [schedule](../schedule.md) ↔ [release](../release.md) / [rollback](../rollback.md) ↔ [design](../../../../docs/superpowers/specs/2026-09-01-m5-isolated-provider-execution-design.md) ↔ [plan](../../../../docs/superpowers/plans/2026-09-01-m5-isolated-provider-execution.md).

This directory preserves historical reviews and is reserved for final fingerprint-bound local verification and independent review reports. The implementation owner records focused RED/GREEN command evidence in coherent commits but does not create reviewer receipts. No local evidence is merge authority.

## Active provisional source ledger

- Exact `61db79f07904ae5facb244c34b26c8383504dd88` has two preserved FAIL reviews in [`remediation-review-findings-61db79f.md`](remediation-review-findings-61db79f.md); they are not PASS receipts.
- Trusted selection/role, proposal lifecycle, structured redaction/path/attestation, factual result integrity and attestor least-privilege repairs landed in the exact source sequence `1beb73c`, `3a7e91e`, `64d55d4`, `f0bc065`, `89b0999`. These are source checkpoints, not external acceptance.
- Task 5 checkpoint `161199bb163e0ba84ac1b32010be87f113df5e86` had a fresh disposable PostgreSQL 17 run of 166/166 tests in 98.074 seconds plus an actual restart/reconcile PASS; recovery/systemd focused checks were 5/5. The root suite was 488/489 with the single expected RED being then-undeclared `recovery.py`; Task 6 closes that inventory drift.
- Task 6 began with five intended RED parity failures: missing recovery ownership/edge, only six architecture contracts and unsupported closed-schema keywords, installer omissions, shallow schema/OpenAPI objects and stale current docs. On its frozen pre-commit tree, execution-contract/protocol/API checks passed 32/32 in 1.388 seconds and `tests.test_structure tests.test_architecture_model tests.test_installer` passed 84/84 in 9.149 seconds; earlier factory discovery passed 166/166 in 1.894 seconds with 46 disposable-PostgreSQL cases truthfully skipped for absent `FACTORY_TEST_DATABASE_URL`. Architecture validate/drift/diagram-check and JSON parsing all passed. Task 7 still owns fresh disposable PostgreSQL, full preflight and independent review evidence.

The OS isolation exit is currently `BLOCKED`: this host has no supported rootless sandbox/egress toolchain and unprivileged user namespaces return `EPERM`. A trusted live Git snapshot broker is also unavailable. M6 paused at `5c5c371` uses the old `61db79f` bridge and is `BLOCKED` pending dependency-ordered restack; provider facts are not authority, production remains human-owned, and fixture/fake evidence cannot be recorded as M5 exit evidence.
