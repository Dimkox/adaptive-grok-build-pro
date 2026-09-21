# Issue #166 — current-prefix migration evidence

Typed authority: [change-spec.yaml](change-spec.yaml).

User requested all issue work in parallel on 2026-09-21. Route af166ec812f3 has no named human gate. All selected analysis reports are complete under evidence/.

## Outcome and scope

A shipped PostgreSQL regression proves real current-prefix upgrade identity, function preservation and bounded contention recovery.

Tests only: reuse a disposable populated historical fixture, apply real packaged prefix SQL with real ledger rows, then invoke the real migrator for exactly the checkout final resource. Compare full derived identity, prior timestamps and populated rows, function OID/owner/ACL and idempotence. Add observable advisory-lock contention with success after release and bounded server timeout/rollback/retry; do not assume an executing function call blocks CREATE OR REPLACE.

Allowed product/test surface: factory/tests/test_execution_persistence_postgres.py and only necessary checkout-derived expectation assertions in existing test/harness modules. Sole write role: data_implementer.

## Bounded ruling

The issue claim about necessary ACCESS EXCLUSIVE locking of executing function calls is contradicted by the inspected PostgreSQL 17 implementation. Use the real documented migration advisory lock for deterministic contention and clearly distinguish that from live function-call concurrency. Timeout SQLSTATEs 55P03/57014 are both acceptable with equal existing 5-second limits; a client timeout is a test failure.

## Delivery dependency

Base is frozen PR #170 head 1f7aedb8ab32e442fb7a9ee1287222fe5f47fe48, including issue164 clock correction. This independent branch is a successor; retain #170 unchanged. External push/PR/merge requires applicable exact authority; no deployment or provider operation is in scope.
