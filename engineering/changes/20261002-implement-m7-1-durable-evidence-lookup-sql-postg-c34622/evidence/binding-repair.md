# Mandatory F architecture and disposable-fixture binding repair

Focused repair 2026-10-02/03; starting exact HEAD `7bc5eba38329e2e9ae5a2e5409c7f28597c4e541`. Controller-refreshed scope gate at 23:49:29Z and local migration-plan gate at 23:51:31Z bind approved scope digest `e00f2001d5e51efa95ec65513ab813eca96590c380e3bb7b0b800b7cab2fcebc`. The writer did not edit the five scope files; their approved requirements/architecture/test-plan additions and human-gates records are committed alongside the bounded repair.

## Preserved failure and root causes

Read actual `.grok-stack/runtime/final-verify.json` before product edits, then archived it using apply_patch as `.grok-stack/runtime/f-repair-original-full-verify.json`. `cmp` succeeded and both SHA-256 values are `5b1169931f15204978f9d34ea46da572ae2c3e98c728ed3b93b696e7f81c35c1`. Its tree fingerprint is `f42b777e9ba3493f0e673e64f40e042ac4bbfd61c3324dd8aeb2c8bc6f3f34e4`; status FAIL. Architecture/governance/root Python tests/coverage/factory-postgres-exit failed; other passing checks remain original-head evidence only, not reused completion.

- Three source modules lacked any architecture owner. Existing architecture seed/drift test failed freshly; new narrow Factory-control ownership expectation also failed before model repair.
- `ExecutionPersistencePostgresTests.setUp` omitted new M7 tables from an explicit old-table TRUNCATE. Fresh real PostgreSQL reproduction failed with `m7_bundles references semantic_verdicts`, matching the original full-gate errors. Explicit six-table inclusion fixes the fixture without CASCADE or altering existing rows outside the owned disposable database.
- The mandatory runner's database/user were correct (`factory_exit`). A legacy test actually restarts Docker and changes its published port, updates the runner environment, but M7's discovery-imported module cached the old DSN. The exact existing disposable guard correctly refused the stale port. A fresh mixed sequence reproduced this before the repair. M7 now validates the refreshed runner environment DSN against the unchanged exact container/name/ID/nonce/user/database/session/postmaster checks before adopting it.
- A final relevant legacy M5 restart probe exposed the same missing-table TRUNCATE in its `_reset_database`; the identical explicit six-table fix was applied only there, reported to the controller as the same authorized synthetic cleanup defect. Its initial failed reset left two synthetic probe login memberships in the owned fixture; the next migrator correctly refused that unsafe residual boundary. Only those two exact inspected probe roles were removed in the bound fixture before retry; no safety check was changed.

## Repair and fresh focused checks

Product changes are only `architecture/system.yaml` (three source paths under existing `NODE-FACTORY-CONTROL`), its additive ownership binding in `tests/test_architecture_model.py`, explicit M7 table inclusion in the two legacy fixture reset lists, and M7 fixture DSN refresh plus real wrong-port/wrong-database denial control. No rules, architecture edges, generated diagram bytes, source/database defaults, production refusal, migration bytes, time budgets or lock budgets changed.

All Python checks used child affinity 12,13 and `PYTHONPATH=factory/src:.`; one exact disposable PostgreSQL fixture used the mandatory runner identity rather than an alternate database/user. No full individual suite, subagent, push or review was performed under this repair assignment.

| Focused command/control | Observed result |
| --- | --- |
| `python3 -m unittest tests.test_architecture_model -q` | 82 tests, 2.068 s, OK |
| `python3 scripts/grok_architecture.py drift --json` | no findings, OK |
| `python3 scripts/grok_architecture.py diagram --check --json` | no mismatches; all five original generated-view digests unchanged |
| Mixed real PostgreSQL invocation: legacy noncanonical-packet refusal, legacy result-dispatch actual restart/no second POST, M7 invalid-DSN refresh denial, migration relations, M7 exact replay/conflicting-body | 5 tests, 9.867 s, OK; modules were imported before the legacy restart, reproducing discovery ordering |
| Real PostgreSQL invocation: legacy exact four-kind replay sequence/capability limits/cross-route corrupt marker, populated 025→026 upgrade/idempotence/drift, definer ownership, repository/source scope before replay, corrupt latest-selector refusal, Unicode/unsorted/duplicate SQL denial, repository-qualified event/replay keys, complete metadata/replay-body binding | 10 tests, 26.105 s, OK |
| `python3 -m unittest factory.tests.test_migrations -q` | 31 tests, 0.071 s, OK; existing exact disposable guard controls retained |
| `python3 -m factory.tests.m7_postgres_restart_probe` | actual restart/new-process reader/exact replay/stable cardinality/revoked-expired evidence, PASS |
| `python3 -m factory.tests.postgres_restart_probe` | two actual restarts, exact runtime/attestor roles, cancelled/orphaned recovery, cleanup replay, no fabricated facts, higher fence, PASS after explicit reset repair |
| Scoped ruff and `git diff --check` | clean |
| Source comparison of 001–026 to original final HEAD | every migration byte unchanged; 026 SHA-256 still `a8f68bcabe2b7b4e28ad7f974b48f9eb9bce7152aee0e159b4b6fb5bbf0fb5ca` |

Exact disposable fixture: ID `640cfb4bdb39d16bad7074511d4c73e12b2a9935413e1d4a3b414c172f07a9fd`, name `adaptive-factory-exit-f34622ec1ccf`, image `postgres:17-alpine`, nonce `f34622ec1ccf20261002235200000000`; inspect confirmed two CPUs and 805306368 memory bytes, loopback-only publication. The exact bound container is removed after evidence collection; no broad cleanup or host/production mutation is performed. Published ports changing across restart are expected and are not permanently pinned as current evidence.

## Remaining gate limitation

The focused architecture fitness diagnostic still FAILS unchanged code-budget policy: full changed-file sizes charge the large existing legacy fixture, exceeding governed/Factory/test byte limits and the test AST limit. Before the final legacy restart-list addition, observed values were governed 1,395,651 > 1,300,000 bytes; Factory 1,249,636 > 1,150,000; tests 863,972 > 800,000; test AST 669 > 600. The additional reset-list file increases that inventory, so those observations are not asserted as final-candidate totals. No budget/rule was weakened. This finding was sent to the controller for explicit aggregate policy handling.

The original full gate remains preserved FAILED; repair-focused success is not a new full gate. Per the user-approved single aggregate source-PR topology, the controller owns fresh aggregate full verification, selected independent reviews, final fingerprint-bound receipts and external exact-head Trust CI/approvals. No local completion, merge, release, production qualification or operational authority is claimed by this handoff.
