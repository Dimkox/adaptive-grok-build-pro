# Rollback plan — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

## Trigger conditions

- Any CLI/server command no longer starts or an approval envelope differs semantically.
- Focused approval/signature/API tests or full verification regress.

## Application rollback

Revert the hotfix commit/PR. The deployed API and worker are not changed by this slice.

## Data recovery / forward-fix

No migration or data write exists. No recovery is required; correct the import mapping
and issue a new commit. Never reuse an approval for a different head or policy epoch.

## Verification after rollback

Run the pre-existing Trust CI suite and confirm the deployed `/health/ready` response
and current App-owned check remain unchanged.
