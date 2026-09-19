# Data analysis — issue 152

Route: `814ed9c452cd`; role: `data_architect`; scope: source inspection only.

## Findings and bounded recommendation

- Use the existing `LandingNormalizationOutcome.reason_code` → `LandingJobRecord.reason_code` path for the bounded allowlisted decoder diagnostic. The current attempt-status contract accepts a string of 1–128 characters; it does not enumerate `http_outcome_unusable`.
- `landing_service.py:417` copies rejected outcomes' reason and observation together; `landing_sqlite_store.py:249` atomically updates `reason_code`, `provider_evidence_digest`, and `observation_json` with an optimistic revision check. `_decode_record` restores all three (`:639`); no new persisted field is required.
- Preserve the executor's already-validated `result.response_digest` when draft decoding fails (`landing_http.py:292`). `_terminal` currently replaces it with a digest of generic state/reason (`:324`), even though it retains real counts in the observation. Retain that original digest in evidence before evidence/observation sealing; never recompute it from draft stdout or an exception.
- Keep `needs_human`, observation category `draft`, `dispatched=true`, reported usage counts, and the existing evidence disposition. The explicit draft category remains ineligible for provider fallback.
- `LandingProviderObservation.from_dict` requires exactly the v1 key set and equality with its recomputed digest (`landing_observation.py:60`); the JSON Schema also forbids extra properties. Adding a diagnostic there under v1 can invalidate stored observations and old consumers. A versioned observation upgrade is unnecessary for this fix.
- `attempt_receipt` already includes/seals `reason_code` and the nested observation (`landing_failover_contracts.py:39`); `/v2/landing-jobs/{job_id}/attempt` returns it (`landing_backend_api.py:43`). Legacy v1 job/result views intentionally expose fewer fields and should keep their shapes.

## Exact regression seam

- Extend `factory/tests/test_landing_failover_backend.py`, combining its authenticated submit/read fixture (`:26`) with its SQLite restart fixture (`:65`), rather than constructing a terminal outcome by hand.
- Supply an offline fake executor returning malformed draft bytes, valid usage and a known response digest deliberately distinct from the draft-bytes digest. Submit through `LandingApplicationService`/POST with `SQLiteLandingJobStore`; assert the selected diagnostic, original digest, `needs_human`, draft category, reported usage and absent artifact.
- Close the first client/store, reopen the same temporary SQLite root with a reconstructed service/app, GET the v2 attempt, and run `validate_receipt` on the result. Require the full receipt/observation, all nested digests, diagnostic and revision to equal the pre-restart values; make executor invocation after restart fail the test.
- Assert the v1 submit/job/result shapes remain closed and the tenant/repository identity remains unchanged. A current normalizer-only test would miss service propagation and historical decoding regressions.
- Add a fixed historical v1 observation fixture with the original exact keys, historical generic reason and generic response digest; after reopening and API read, require equal observation JSON and digest, with no invented diagnostic or response digest. Avoid building this fixture solely through the potentially changed observation serializer.
- Retain `test_v1_store_migrates_without_fabricating_historical_observations` (`:87`): old SQLite v1 rows expand to schema v2 with `observation_json=NULL`; absence remains absence. Also retain digest-tamper rejection.

## Data operations and recovery

- Database schema remains version 2, with unchanged columns, indexes, foreign keys, transactions and tenant-scoped primary key. No migration, backfill, table scan, new locks, downtime or volume-dependent work is needed.
- Historical terminal rows are excluded from restart recovery (`landing_sqlite_store.py:393`), so reads must not rewrite old reasons or evidence. Their old generic response digest is an immutable historical fact, not reconstructible provider evidence.
- Rollback is the prior application revision: it already accepts the existing reason string and v1 observation shape. New rows remain readable; no database rollback is required. New evidence/observation/receipt digests legitimately differ because newly captured facts differ.
- Only allowlisted static codes may reach the persisted reason. Keep exception details, draft text, keys, URLs and provider response content outside this metadata; persist only the validated response hash.

No tests, provider calls, production state inspection or application edits were performed by this analysis role. Shared-memory fact for the controller: reuse the existing reason column to preserve strict historical observation receipts without a migration.
