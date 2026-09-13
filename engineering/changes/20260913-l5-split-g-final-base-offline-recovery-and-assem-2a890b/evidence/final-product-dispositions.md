# Frozen-reference product deviations

Final G must compare every committed Git tree entry and mode against f31406e970d67f7cd59694da5de88915adb0fa68, including unrelated inherited base files. The preserved full manifest and audit script enumerate the entire union. Exactly these ten product paths have intended differences; no other source/schema/package/runtime delta is authorized by reconstruction:

- architecture/system.yaml: exact LOCAL-API owner for the new independent D test_landing_server.py.
- delivery/src/adaptive_delivery/landing_publication.py: F strict SQLite schema/table/index and full supported CREATE TABLE validation, with explicit INSERT OR ABORT; unchanged supported schema identity.
- factory/src/adaptive_factory/landing_backup.py: G known second-pass I/O budget preflight before root creation, same caps/deadline.
- factory/src/adaptive_factory/landing_sqlite_store.py: D interrupted-constructor/close ownership cleanup.
- factory/src/adaptive_factory/server.py: D independent listener/runtime/socket cleanup attempts.
- factory/src/adaptive_factory/settings.py: D shared double-slash path-anchor rejection before I/O.
- factory/tests/test_landing_backup.py: G reduced-budget, active writer, committed WAL and populated publication-state proofs.
- factory/tests/test_landing_publication_cli.py: F unsupported schema and committed-effect/restart/restoration lineage regressions.
- factory/tests/test_landing_runtime.py: C independent mixed v1/v2 real SQLite reopen/tamper proof.
- factory/tests/test_landing_server.py: D direct entrypoint ownership, source/key ordering, aliases and cleanup tests.

Nine shared documents are reconciled explicitly to current capabilities, 22 deploy members, historical model observations and pending exact-head evidence. The old 97-file monolith evidence package remains in the immutable frozen reference; seven new packages retain original analysis provenance and fresh source-bound evidence. This separation is intentional and does not waive source equality. Final source/head audit result is generated after commit in the separate evidence checkout.
