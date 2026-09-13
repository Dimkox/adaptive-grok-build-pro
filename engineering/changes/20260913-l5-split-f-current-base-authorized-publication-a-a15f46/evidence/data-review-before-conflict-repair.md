# Independent data review — L5 F2

Verdict: **FAIL**. A supported-schema validation gap permits silent replacement of a durable publication intent when the request ID is reused. Do not record a passing data-review receipt for this source.

- Reviewer: selected independent read-only `data_reviewer`; sole implementer is `data_implementer`.
- Route: `a15f467e4575`; change: `20260913-l5-split-f-current-base-authorized-publication-a-a15f46`.
- Source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f2`.
- Exact HEAD: `5a2ead6e6e1eff5c5df28a8d4bcb91a209975187`.
- Genuine route base: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Tree fingerprint: `939cd5d8b4cf7af62b8a275faef0e791a8645cea3e7e4a1e065aa2a06a2698f5`.
- Full verifier: `/tmp/agbp-sweep/split-f2-full-final.json`; SHA-256 `991a7850b0ac73ca06a802afe962491487f4d22540cfdd48e29bf8b0df7c89ea`; all 15 checks PASS. These checks do not cover the independent counterexample below and therefore do not resolve this finding.

## Blocking finding DATA-F2-001

`delivery/src/adaptive_delivery/landing_publication.py`, `_validate_schema` and `PublicationStore.prepare`: column/table/index metadata establishes strictness and uniqueness but does not reveal SQLite's conflict resolution clause. The validator accepts the expected eight-column STRICT table with the expected application ID/version and both expected unique indexes when `request_id TEXT NOT NULL UNIQUE` is changed to `request_id TEXT NOT NULL UNIQUE ON CONFLICT REPLACE`. `prepare` uses a plain INSERT and relies on `IntegrityError` to enforce durable idempotency. Under this accepted schema SQLite deletes the original intent and inserts the new body instead of raising that error.

The independent security reviewer first identified this surface; I independently reproduced it using only temporary mode-0700 roots and mode-0600 databases. No publication adapter, grant, credential, network or operational state was involved.

Reproduction: create the expected schema with the single conflict-clause addition; stamp application ID `0x4C355055` and user version 1; open `PublicationStore`; prepare a valid stage request with request ID `reused-request`; then prepare a second valid request with the same ID and paired non-null baseline digests, changing its request digest.

| Conflict policy | Store open | Second `prepare` | Persisted outcome |
| --- | --- | --- | --- |
| ABORT control | accepted | `publication_idempotency_conflict` | original intent retained |
| REPLACE | accepted | returns second request | original intent deleted, second intent is the only row |
| IGNORE | accepted | `publication_request_unavailable` | original retained, required idempotency error lost |

For this independent fixture, original digest was `28a7402cac97ed4d78245c395d75c65dde7f088cf4f413dc86b69a208db05970` and changed digest was `75e576a688ec3c294702953bb814883d09c3094ab06046e9e606dc2bf7f11871`. REPLACE left only the changed digest under `reused-request`. The security peer's separate fixture is retained at `/tmp/agbp-sweep/split-f2-security-conflict-policy.json`.

The supported coordinator currently checks `find_id` before calling the store, which limits normal CLI exposure. This reproduction is a concrete store-level data loss and unsupported-schema acceptance defect, not evidence of an authorization bypass or an external filesystem mutation. It contradicts the slice's fail-closed supported-v1 schema and durable request-ID guarantees. Parent explicitly ruled that it must be corrected before delivery.

## Narrow correction and acceptance

Return the finding to the selected sole writer. Extend supported-v1 DDL validation to reject conflict-policy changes in both writer and read-only opens; SQLite PRAGMA column/index signatures alone cannot prove those semantics. Bind validation to the supported definition while preserving the ordinary formatting of valid v1 files; do not attempt to infer semantics by stripping arbitrary quoted SQL text. An explicit `INSERT OR ABORT` can additionally ensure that schema conflict policy cannot silently replace an intent, but by itself it would not establish rejection of unsupported schema.

Add failing regressions for request-ID UNIQUE and request-digest PRIMARY KEY conflict-policy variants, including REPLACE and IGNORE, and prove that changed-material request-ID reuse leaves the original canonical intent intact. Reopen the normal existing v1 schema in both modes, retaining same-request idempotency. Keep application ID, user version, normal CREATE TABLE statement and existing databases unchanged; no migration or production action is required. Rerun full verification and selected independent reviews on the corrected immutable HEAD.

## Other reviewed properties and current evidence

I inspected the genuine base-to-HEAD source diff, the active route/package, publication store/coordinator/contracts, filesystem publisher, factory retained-artifact reader, governance wrapper and tests. All eleven changed product/test/config blob IDs and modes match archived F `517741da6e883c5feacbd2f029d745ffc5e2fec0`; this is provenance, not substituted current verification.

The intended schema is a separate publication database. Landing job SQL, V1/V2 evidence, migrations and predecessor fixes remain unchanged. Writer ownership is cooperative and local; a committed `prepared -> inflight` transition binds request digest, exact body, prior phase and grant digest before filesystem effects. Reconciliation observes inflight effects and never repeats stage/activation. Committed-effect interruption/reopen and restore lineage tests cover this mechanism. Read-only URI construction uses `as_uri()` with `mode=ro` and rejects a missing publication database before creating database or writer-lock files. Tenant/repository artifact scope is checked before reading landing state, and retained artifacts are revalidated.

Fresh independent focused run on this exact HEAD:

```text
PYTHONPATH=.:factory/src:delivery/src:.grok-stack PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 factory/tests/test_landing_publication_cli.py
```

Result: **17 passed, 68 subtests passed in 7.87 seconds**, exit 0. This identifies the missing conflict-policy coverage; it is not a passing overall data verdict. Final HEAD, clean working tree and fingerprint were checked after all disposable tests. Only this counterpart evidence report was written.

## Limits and recovery

This report supplies local review evidence only; it is not external Trust CI merge authority, production activation evidence or a live HTTP-origin check. No operational data or credentials were accessed. The publication store and filesystem pointer do not form one distributed transaction; durable intent plus observation handles uncertainty, preserving ambiguous partial state for human recovery. Stop writers before code rollback, preserve SQLite/WAL and release directories, and obtain exact current authority for a separate pointer restoration. Reverting source alone does not reverse a publication effect. No retention/backfill or high-volume performance guarantee is introduced by this slice.
