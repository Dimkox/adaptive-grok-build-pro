# Rollback plan — Factory v1.5 fast working release

## Trigger conditions

Contract regression, unsafe context/result admission, incorrect authority elevation, non-idempotent persistence, or migration failure.

## Application rollback

Disable new v1.5 qualification/context surfaces and return callers to existing native v1/v2 paths. Do not roll back by changing old contract meaning.

## Data recovery / forward-fix

Keep additive append-only records; correct with superseding records and a forward migration. Never rewrite factual history.

## Verification after rollback

Run old-reader contract suites, factory unit/integration tests, and verify no new endpoint or flag remains active by default.
