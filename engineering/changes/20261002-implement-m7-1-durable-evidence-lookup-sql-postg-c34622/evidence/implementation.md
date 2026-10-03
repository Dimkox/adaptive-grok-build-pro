# F durable evidence reconstruction — implementation evidence

Recorded 2026-10-02T23:12:39Z by the sole selected data_implementer in `feat/v211-durable-evidence`, starting from `e5856acfd4bc7a186f40a740b54ec86459462db5`. Product work was reconstructed narrowly from the read-only preserved source, not imported as an aggregate or accompanied by old evidence. The five owner-approved scope files were not changed. The controller owns final-head verification, independent reviews and fingerprint receipts; this report is focused writer evidence, not completion or merge authority.

## Implementation

- Closed M7 contract/schema, default-unavailable source/preflight seam, PostgreSQL registry/outcome/check/context/reader adapters, explicit administrator provisioning, and additive migration 026. No HTTP/provider integration or seeded bindings.
- One domain-separated SHA-256 over exact bounded UTF8 canonical JSON bytes binds stored bodies, derived selector metadata, source binding, responses and replay. SQL does not hash `jsonb::text`. Unsorted/duplicate references are rejected before writes. NFC, UTF8-byte, C0/DEL/C1 and integer/shape contracts are enforced in Python and direct SQL.
- Latest selection uses indexed metadata generated from canonical payloads; the full latest row, canonical payload, selector digest and source binding are validated before use. Corrupt/newest stale/revoked facts do not expose an older green fact. Source binding ambiguity is refused rather than `ORDER BY principal_oid LIMIT 1` selection. Event, revision, advisory-lock and replay identities include repository scope.
- Fixed `pg_catalog,factory,pg_temp` definer search path, schema-qualified relations, revoked PUBLIC/runtime function privileges, isolated NOLOGIN owner and narrow capability grants. Existing producer relations are read-only except the owner's single `tasks.updated_at` column privilege required by PostgreSQL row locking; no product task mutation is added. Source/tenant denial and unsafe role attributes are tested.
- Only the exact abandoned default draft package `20261002-implement-m7-1-durable-evidence-lookup-with-addi-c5a8fb` was removed after checking its placeholder-only files, using apply_patch; no preserved source or other contour was cleaned.

## Fresh RED/GREEN and commands

Commands used `PYTHONPATH=factory/src`, child affinity `taskset -c 12,13`, and an explicitly bound synthetic disposable database where applicable. No credential-store, production database, private key or deployed policy was accessed. The synthetic connection value is intentionally omitted from this report.

- RED: `python3 -m unittest factory.tests.test_m7_integrity -v` initially failed four assertions for the absent boundary. Additional ownership and latest-selector mutation probes failed before their respective repairs. These failures were fresh, not reused historical evidence.
- GREEN: `python3 -m unittest factory.tests.test_m7_integrity factory.tests.test_shadow_lookup -q`: 22 tests. Selected predecessor schema/migration/runner binding tests: 73 passed. Focused installer inventory binding: one passed; a preceding full 35-test installer run exposed the inventory assertion that was repaired.
- GREEN final factory unit discovery: `python3 -m unittest discover -s factory/tests -t . -q`: 1,055 tests in 99.428s, OK, 191 database-dependent skips. A prior discovery exposed closed schema inventories and restart-runner mock port ordering, which were updated without weakening predecessor aggregate checks.
- GREEN PostgreSQL suite: `python3 -m unittest factory.tests.test_shadow_lookup_postgres -q`: 26 tests in 104.030s. Subsequently added complete selector-field/replay corruption test and expanded populated-history EXPLAIN: two tests passed in 23.509s. Updated direct-SQL Unicode/unsorted/duplicate reference probe: one test passed in 5.711s. Thus all 27 current PostgreSQL test names were exercised, but the final 27-name set was not rerun as one invocation; final controller verification remains required.
- Actual upgrade: `M7AMigrationPostgresTests.test_populated_025_upgrade_idempotence_and_checksum_drift_refusal` passed in 9.838s. It installed the actual 001–025 prefix in an owned scratch database, populated an existing intake identity, applied only 026, verified idempotence, preserved all earlier ledger checksums, observed no seeded source bindings, and refused deliberately drifted 026 checksum. Only that owned scratch database was dropped.
- GREEN final current migration restart: `python3 -m factory.tests.m7_postgres_restart_probe`: actual Docker restart, reader in a new Python process, exact old replay, stable digests/cardinality, and latest revoked/expired evidence retained. Output: `PASS: M7 new-process lookup, exact replay, stable record digests/cardinality, revoked/expired evidence`.
- Scoped ruff: all checks passed. `git diff --check`: no errors.

## Disposable database and query plans

Exact owned container ID `0a76078ed16b99e942c3f1f32c99039188030ab415165d76bead44bd6376bbde`, name `adaptive-factory-exit-c34622ec1ccf`, image `postgres:17-alpine`, ownership nonce `f34622ec1ccf20261002223500000000`. Inspect confirmed CPU bound 2.0 and memory 805306368 bytes (768 MiB), loopback-only publication. The restart probe checks exact name/ID/image/nonce, database/login, published port and final postmaster identity before mutation. This owned disposable container is removed after these tests using the same exact binding; no broad Docker cleanup is performed.

`EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON)` on histories of 80 contexts, 40 outcomes and 40 checks used `m7_context_canonical_latest`, `m7_outcome_canonical_latest`, and `m7_check_canonical_latest` index scans respectively. Each returned one row; observed shared hits were 5/2/5 and execution approximately 0.151/0.092/0.104 ms. These are tiny synthetic plan observations, not a production performance guarantee.

Bounds: 1 MiB canonical wire/response; depth 16; object 128 properties; array 1,024 items; string 4,096 UTF8 bytes; signed 64-bit integer range; Python aggregate complexity 50,000 nodes. Source enumeration reads at most 33 bindings per kind and refuses overflow/ambiguity; individual latest indexed reads return at most one row. Store connection timeout is 5 s, statement timeout 10 s and lock timeout 3 s. No unbounded source-history read or network call was introduced. Growth/production cardinalities, real external provenance authenticity, operational qualification, M8 cohort claims and deployed Trust CI behavior remain untested/outside scope.

## Migration checksum binding

Source byte comparison to starting baseline confirms every 001–025 migration unchanged. Tip was reconfirmed 025 before creating additive 026; ledger upgrade/idempotence/drift tests passed. SHA-256:

| Migration | SHA-256 |
| --- | --- |
| 024_factory_v15_result_outbox.sql | 72efd7e17b4d25f89925ff274f35306cba9d335cc9dc5355549283e3bf743bce |
| 025_factory_v15_result_dispatch.sql | 5782e7d8ea86848583b227754b8f2fddedba8ef3a9d7d59bd9934799d8887fd4 |
| 026_m7_durable_evidence.sql | a8f68bcabe2b7b4e28ad7f974b48f9eb9bce7152aee0e159b4b6fb5bbf0fb5ca |

001–023 full hashes were printed by the fresh `hashlib.sha256`/`git show <base>:<path>` comparison; all 25 comparison assertions succeeded. No historic migration bytes or deployed database were modified.

## Subsequent full-gate failure and bounded repair

The controller's full gate on original final HEAD `7bc5eba38329e2e9ae5a2e5409c7f28597c4e541` FAILED. Mandatory architecture ownership and old/new mixed PostgreSQL fixture bindings were missing despite the isolated checks above. See [binding-repair.md](binding-repair.md) for preserved failure identity, fresh reproductions, narrowly approved repairs and remaining code-budget findings. Neither the original focused checks nor these repairs establish a passing full candidate gate.
