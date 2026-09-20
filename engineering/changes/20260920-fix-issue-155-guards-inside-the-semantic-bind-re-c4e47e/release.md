# Release plan — Fix issue #155: semantic_bind_repair_child guard rejections and PostgreSQL tier determinism

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Deployment

Source-only release on `main` through this pull request. Nothing is deployed by this route: no service, no image, no infrastructure apply, no external write.

Rollout is the ordinary consumer update. A consumer database upgrades itself on the next `PostgresMigrator.apply()`: `021` is discovered as the single pending resource and runs inside one transaction under `pg_advisory_xact_lock` with the runner's own `SET LOCAL lock_timeout='5s'; statement_timeout='5s'`. It is `CREATE OR REPLACE FUNCTION` plus `REVOKE`/`GRANT` on an unchanged signature — no data touch, no index build, no backfill, so there is no window in which rows are half-converted.

Merge eligibility is unchanged by anything in this package: the App-owned policy-epoch check on the exact head SHA (`adaptive-trust-ci/verified@<policy-sha12>`) plus the signed approvals the deployed policy names. Local receipts and this document are evidence, never authority.

## Feature flags / staged rollout

None, deliberately. The behaviour is a diagnostic channel: the guard set is identical, so a deployment either has `021` applied (reasons present) or does not (bare `NULL`, the pre-fix shape). Both states accept and reject exactly the same rows, which is what makes a flag unnecessary and a rollback cheap.

## Metrics and alerts

- `SIG-001` — every `bind_repair_child` refusal names a reason: one of the twelve codes emitted by SQL once `021` is applied, or `store_returned_null` on a schema that has not applied it yet; `invalid_object`/`unknown_fields` stay reserved for malformed payloads. Alert-worthy signal is the *absence* of a named reason in a rejection log line, which would mean a guard returned `NULL` again.
- `SIG-002` — mandatory tier per-attempt duration and host load, with the product-tree fingerprint stamped around the streak; a streak that resets is a defect report, not an environment note.
- Existing store error accounting is untouched: no new error class, `StoreError` keeps its type and its message prefix, only the suffix grows.

## Disclosure accepted by review

The guard set went from one anonymous refusal to twelve named reasons, so a principal holding `EXECUTE` on `factory.semantic_bind_repair_child` can now distinguish *why* a bind was refused (proposal present/pending, child superseded, intent already bound, authority observation present) where before it learned one bit. `security_review` graded this Low and accepted it: digests are `^[0-9a-f]{64}$`, the only reader is the principal legitimately performing binds, no stored value crosses the boundary, and the HTTP edge returns the fixed `store_conflict` body (409) and never echoes it. Recorded here rather than left inside a review file.

## Go/no-go criteria

Go requires all of:

1. Four consecutive mandatory disposable-exit tier passes recorded in `evidence/postgres-evidence.md` §10 against the delivered tree.
2. `python3 scripts/grok_verify.py --mode pr` `RESULT: PASS` on the clean committed tree, with `source-stability` stable.
3. Passing `code_review`, `test_review`, `security_review` and `data_review` receipts bound to that same fingerprint (the route's `required_evidence`).
4. Zero diff under `factory/contracts/`, `schemas/`, `architecture/`, `governance/`, and zero diff in `resources/018_semantic_validation_bridge.sql`.
5. External Trust CI green on the exact head SHA.

No-go / hold: any rejection path that can still reach `invalid_object` without a malformed payload; any tier pass obtained by widening a timeout, a window, or the harness; a streak whose attempts used different product fingerprints.

## Explicitly not claimed

`VERSION` is not bumped and no release/tag/GitHub Release is produced by this route — this is a bugfix commit on `main`, and publication stays a separately delegated action.
