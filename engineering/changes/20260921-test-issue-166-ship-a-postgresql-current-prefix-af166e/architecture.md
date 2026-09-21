# Architecture

Tests only: reuse a disposable populated historical fixture, apply real packaged prefix SQL with real ledger rows, then invoke the real migrator for exactly the checkout final resource. Compare full derived identity, prior timestamps and populated rows, function OID/owner/ACL and idempotence. Add observable advisory-lock contention with success after release and bounded server timeout/rollback/retry; do not assume an executing function call blocks CREATE OR REPLACE.

The issue claim about necessary ACCESS EXCLUSIVE locking of executing function calls is contradicted by the inspected PostgreSQL 17 implementation. Use the real documented migration advisory lock for deterministic contention and clearly distinguish that from live function-call concurrency. Timeout SQLSTATEs 55P03/57014 are both acceptable with equal existing 5-second limits; a client timeout is a test failure.

No new service, dependency or production-state change.
