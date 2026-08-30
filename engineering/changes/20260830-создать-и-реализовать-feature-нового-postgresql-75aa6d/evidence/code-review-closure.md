# Code review closure — protected evidence crash window

## Verdict

**PASS**

Targeted closure review for route `75aa6daa89b1` on fingerprint
`f8d87aa4d8defd71181014278002624bdb751fd3d7ef06ba8435cbc4bb89ea7f`.
The HIGH finding from `code-review-final.md` is closed. No actionable finding
remains in the reviewed closure scope.

## Closure evidence

### Exact-tuple crash/restart idempotency

Checked:

- `trust-ci/src/adaptive_trust_ci/worker.py:197-225`
- `trust-ci/src/adaptive_trust_ci/store.py:501-533,1306-1334`
- `trust-ci/sql/004_production_promotions.sql:488-550`
- the byte-identical packaged migration mirror

The worker now calls `record_or_get_protected_branch_evidence`. PostgreSQL uses
conflict-safe insertion and selects by the database-unique exact tuple. A retry
with a fresh `source_attestation_id` returns the originally stored signed
envelope when merge fact, repository/ref/SHA, policy/artifact,
runner/holdout/image digests, result and signer key match. Any identity mismatch
raises and fails closed.

This makes the former crash window recoverable: evidence committed before a
crash remains the sole row, a reclaimed fact receives the original durable
identity, and lease-owned completion can proceed. `MemoryStore` now implements
the same exact-tuple reuse/conflict rule rather than accepting a divergent
second row.

Regression coverage:

- `test_store.StoreTests.test_protected_evidence_exact_tuple_reuses_existing_identity_and_rejects_mismatch`
- `test_postgres_integration.PostgresIntegrationTests.test_crash_after_evidence_commit_reuses_exact_tuple_and_completes_after_restart`

The PostgreSQL regression explicitly commits evidence, expires the first lease,
creates a new store and claim, submits fresh signed evidence identity, receives
the original envelope, completes the fact and asserts one evidence row.

### Success publication ordering

Checked:

- `trust-ci/src/adaptive_trust_ci/runner.py:90-218`
- `trust-ci/src/adaptive_trust_ci/worker.py:206-211`
- `trust-ci/tests/test_runner.py:215-237`
- `trust-ci/tests/test_merge_provenance.py:153-220`

`run_protected_branch` no longer publishes success. The worker first persists or
recovers the durable evidence identity, then calls
`publish_protected_success`, then completes the leased fact. The ordering test
proves no success exists after validation alone and success appears only through
the separate publication method. The worker call-order test proves
`run -> record-or-get -> publish -> complete`.

Publishing before the final completion call is recoverable rather than
ambiguous: if completion fails after publication, the next claim retrieves the
same durable envelope and repeats idempotent App Check publication before
completing. No second attestation identity or evidence row is created.

## Verification observed

Locally rerun in this closure review:

```text
PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest -v \
  test_merge_provenance test_runner test_store \
  test_postgres_integration.PostgresIntegrationTests.\
test_crash_after_evidence_commit_reuses_exact_tuple_and_completes_after_restart
Ran 57 tests — OK (1 PostgreSQL test skipped because this review shell had no
TRUST_CI_TEST_DATABASE_URL)
```

The fingerprint-bound implementation evidence records the same PostgreSQL
regression in the disposable real-PostgreSQL suite: **33/33 PASS**. `git diff
--check` also passed in this closure review.

## Residual risks

- This was intentionally limited to the prior HIGH finding; no new scope was
  opened.
- Runtime recovery still depends on the existing lease expiry/backoff and
  immutable mounted supply-chain inputs reviewed in earlier rounds.
- No receipt, private-key access, external write, merge or deployment occurred.
