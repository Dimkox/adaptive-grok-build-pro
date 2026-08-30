# Code review rerun — production-only human approvals

## Verdict

**FAIL**

Reviewed route `75aa6daa89b1` on verified tree fingerprint
`dcdee2548ec1f47e4620ea1b895421c58b3ad8b6a704464380bf405e4c97a8ec`.
Both findings from the first review are closed, but the newly connected runtime
worker can irreversibly exhaust a merge fact during a short dependency outage.

## Previous finding closure

### CLOSED — production provenance composition

Checked:

- `trust-ci/src/adaptive_trust_ci/api.py:53-70,153-170`
- `trust-ci/src/adaptive_trust_ci/settings.py:88-168,170-243`
- `trust-ci/src/adaptive_trust_ci/worker.py:209-289,291-346`
- `trust-ci/compose.yaml` and API/worker environment examples

The API now resolves a validated server-owned protected ref from runtime
settings. Worker construction receives the protected repository/ref, exact
supply-chain bundle and artifact, mounted public verification key and
reconciliation interval. The continuous worker loop now claims durable merge
facts, builds an exact protected request, corroborates it, runs exact-SHA
verification, persists protected evidence, and periodically runs reconciliation.
This closes the former disconnected-entrypoint blocker.

### CLOSED — incomplete GitHub search watermark safety

Checked:

- `trust-ci/src/adaptive_trust_ci/github_app.py:194-224`
- `trust-ci/src/adaptive_trust_ci/worker.py:40-64,87-116`
- `trust-ci/tests/test_merge_provenance.py:470-490`

`incomplete_results=true` now raises `IncompleteGitHubSearch`, which is converted
to `ReconciliationIncomplete` before candidate processing. The regression test
confirms no watermark write occurs.

## New finding

### HIGH — transient dependency failure burns all merge-fact attempts in a hot loop

Files/lines:

- `trust-ci/src/adaptive_trust_ci/worker.py:191-207,291-328`
- `trust-ci/src/adaptive_trust_ci/store.py:1058-1086`
- `trust-ci/sql/004_production_promotions.sql:227-305`

When GitHub corroboration, supply-chain verification, the exact runner, or
evidence persistence raises, `process_next_merge_fact` immediately calls
`retry_merge_fact`. The SQL transition returns the row directly to `pending`.
`Worker.run` catches the error, sets `did_work=True`, and deliberately skips its
poll wait when no legacy PR job exists. The same oldest row is therefore claimed
again immediately. After 20 rapid iterations the SQL retry function marks it
`dead`.

This turns a short GitHub 5xx/rate-limit window, mounted-bundle transition, or
temporary runner outage into permanent loss of the only merge provenance job.
Reconciliation cannot revive it: re-recording the deterministic existing merge
fact is idempotent and leaves its `dead` processing state unchanged. The result
is a permanently missing protected attestation and an unusable promotion gate
for that merge, contrary to the bounded-retry and missed-webhook recovery
requirements.

Required repair: make retry eligibility durable and time-based (for example a
`next_attempt_at` with bounded exponential backoff), or at minimum wait after a
failed claim and distinguish retryable dependency failures from permanent
provenance denials. Provide an explicit dead-letter recovery/requeue path that
does not mutate immutable fact identity, and add a `Worker.run` regression test
showing a transient failure consumes one attempt, does not spin, and remains
recoverable after the dependency returns.

## Regression review

- The automated `approval_rules: []` development/PR/merge path remains free of
  human signatures.
- The only human signature remains the exact, short-lived
  `promotion:production` envelope at final production go/no-go.
- API admission, signature/provenance binding, idempotency, replay rejection,
  consume-once and terminal-event behavior were inspected for accidental
  widening; no additional correctness finding was identified.
- No human private key, external mutation, merge, deployment or receipt action
  was performed.

## Verification evidence

Focused current-tree run:

```text
PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest -v \
  test_merge_provenance test_api test_promotion_e2e
Ran 59 tests in 1.362s — OK
```

The passing tests confirm the two former findings are covered at component
level. They do not exercise the failure cadence of the continuous
`Worker.run()` loop identified above.

## Residual risks

- A mature repository with more results than the bounded reconciliation page
  cap requires an externally seeded/advanced watermark; current behavior fails
  closed rather than skipping results.
- The runtime supply-chain verifier is tied to the mounted immutable bundle and
  public key. Bundle rotation must remain atomic and observable to avoid
  triggering the retry defect above.
- Any product-code repair invalidates this review and requires fresh route
  verification plus another independent code review.
