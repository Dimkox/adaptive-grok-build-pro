# Independent data re-review — L5 F2

Verdict: **PASS**. Blocking finding DATA-F2-001 is fixed on this exact source. The previous FAIL remains archived in `data-review-before-conflict-repair.md` and is not relabeled.

- Reviewer: selected independent read-only `data_reviewer`; implementation owner: `data_implementer`.
- Route: `a15f467e4575`; change: `20260913-l5-split-f-current-base-authorized-publication-a-a15f46`.
- Source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-split-f2`.
- Exact HEAD: `c3f60f09b819c1a246f7af2dcd6664cf3be52dd6`.
- Genuine unchanged route base: `d33e8d8b2aa06a76f32724d08d79a21f3604ce42`.
- Current fingerprint: `aa60705bc8c9bbae34517a480ed842254c8b67db86b8b0a6cd3a119b6740cff5`.
- Full verifier: `/tmp/agbp-sweep/split-f2-full-final.json`; SHA-256 `fd576951dd5cebfc1ab59a0de3d70b22495c235f03731a1db80c6fcd2e3dcdd6`. Route, fingerprint and architecture HEAD match this checkout; all 15 checks PASS, including disposable PostgreSQL and source stability.

## Blocking finding resolved

The earlier validator accepted a STRICT table whose UNIQUE conflict policy was REPLACE or IGNORE because PRAGMA table/column/index metadata does not expose that policy. A plain INSERT could consequently replace an existing request ID's intent or return the wrong collision error.

The actual two-file repair adds comparison of the complete stored CREATE TABLE declaration against the supported v1 declaration after whitespace collapse and case normalization, retaining comments, quotes and additional tokens as differences. Existing logical schema/object/index checks remain. Normal writer and read-only opens now reject the altered conflict policies with `publication_state_schema`. `PublicationStore.prepare` additionally uses explicit `INSERT OR ABORT`, so insertion cannot inherit a replacing/ignoring conflict algorithm.

I inspected the correction against previously reviewed HEAD `5a2ead6e6e1eff5c5df28a8d4bcb91a209975187` and its surrounding implementation/tests. Only `delivery/src/adaptive_delivery/landing_publication.py` and `factory/tests/test_landing_publication_cli.py` changed among product/test/config paths; the other nine F component paths retain their reviewed bytes/modes. Independent AST comparison confirms that the app-created `_SCHEMA` and `APPLICATION_ID` are unchanged. User version remains 1. No migration, authority callback, request/evidence contract, coordinator transition, adapter effect or predecessor source change was introduced.

## Independent reproduction and regression evidence

I repeated the original temporary-database counterexample with UNIQUE ON CONFLICT REPLACE and IGNORE. Both modes now reject each database with `publication_state_schema`. To independently exercise the additional insert defense, a separate disposable check patched only the schema validator within the test process: the real store's explicit INSERT OR ABORT rejected changed-material reuse with `publication_idempotency_conflict`, retained the exact original request and left one original row under both REPLACE and IGNORE. This deliberate test-only bypass is not a supported product path or an operational database action.

Fresh affected-suite execution:

```text
PYTHONPATH=.:factory/src:delivery/src:.grok-stack PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -c /dev/null -p xdist.plugin -p no:cacheprovider --rootdir=. --import-mode=prepend -q -n28 --dist=loadfile --max-worker-restart=0 factory/tests/test_landing_publication_cli.py
```

Result: **20 passed, 88 subtests passed in 8.15 seconds**, exit 0. Coverage includes UNIQUE and PRIMARY KEY REPLACE/IGNORE clauses in writer/read-only mode; block/line comments and quoted/bracketed variants; supported lowercase/indentation; unchanged preseeded intent bytes; standard schema reopen/idempotency; URI special characters and missing-store read-only behavior; committed stage/activation interruption and fresh-store observation without effect replay; and restoration to an earlier release or empty baseline with valid lineage. Final HEAD, clean working tree and fingerprint were rechecked after the disposable tests.

## Data-integrity assessment

F adds a separate private publication intent database; landing job SQL, V1/V2 retained evidence and existing migrations remain unchanged. Its supported schema has immutable request identity, unique request IDs, canonical request bodies and phase/observation/grant bookkeeping. The local cooperative writer lock serializes store writers. A single durable compare-and-swap transition binds request digest, canonical body and expected phase before effects. Exact injected authority is validated before the inflight transition and filesystem mutation; saved-request reads and observation-only bookkeeping can precede authority without repeating effects.

Inflight reconciliation observes the configured filesystem and records success or needs-human ambiguity. It does not automatically repeat a potentially committed stage or pointer change. Restore requests bind an activated predecessor and its observed baseline. The factory reader scopes tenant/repository before reading landing state, opens the database read-only using a correctly escaped URI, and revalidates retained source/artifact bindings and bytes. The separately configured publication state is not a new tenant-wide remote service. Existing keyed lookups remain indexed; there is no backfill, retention sweep or claimed high-volume performance result.

## Compatibility and limits

The supported v1 format is the actual application-created declaration with accepted whitespace/case normalization. Arbitrary hand-authored equivalent SQL with comments, quoting or extra clauses is intentionally rejected; no general SQL equivalence parser or in-place repair is promised. The normal app-created schema and its version remain unchanged.

This review is local source/data evidence, not external Trust CI merge authority or production/HTTP-origin readiness. No operator database, credential, grant store, network endpoint or production directory was accessed. Test grants remain synthetic. The lock is cooperative and local; raw clients that ignore it are outside its coordination boundary. Publication intent and filesystem state are reconciled across separate durability boundaries, preserving ambiguity rather than claiming one atomic distributed transaction. Stop writers before code rollback and retain SQLite/WAL, immutable releases and observed pointers; reverting code does not undo a pointer change, and a later restore requires its own exact current authority.
