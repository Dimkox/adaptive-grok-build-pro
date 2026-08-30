# Final code review — production-only human approvals

## Verdict

**FAIL**

Reviewed route `75aa6daa89b1` on verified tree fingerprint
`c00baee9fdd3ebad087dcb29539bb36ea24a205b18cce8d8d6706bdbdcf8a5ba`.
All findings from the two earlier reports are closed. One separate restart/crash
idempotency defect remains in the final protected-evidence transition.

## Previous finding closure

### CLOSED — production provenance wiring

The configured protected ref now reaches merge webhook admission. Worker
construction receives the protected repository/ref, immutable supply-chain
paths and public verification key. The continuous loop claims durable merge
facts, runs exact-SHA verification and reconciliation, and records protected
evidence.

### CLOSED — incomplete GitHub search watermark

`incomplete_results=true` is rejected before candidate processing and before
any watermark write. The bounded reconciliation regression passes.

### CLOSED — hot-loop attempt exhaustion

Files checked:

- `trust-ci/src/adaptive_trust_ci/worker.py:197-224,311-349`
- `trust-ci/src/adaptive_trust_ci/store.py:389-463,1096-1168`
- `trust-ci/sql/004_production_promotions.sql:228-354`
- `trust-ci/tests/test_merge_provenance.py:215-288`
- `trust-ci/tests/test_store.py:237-280`
- `trust-ci/tests/test_postgres_integration.py:222-263`

Retries now have durable `next_attempt_at` eligibility with bounded exponential
backoff. The worker restores normal polling cadence after failure, provenance
mismatches become permanent denials, and exhausted retryable facts have a
constrained requeue transition. The current tests cover early claim denial,
worker cadence, permanent classification and PostgreSQL restart behavior.

## Finding

### HIGH — crash after evidence commit cannot idempotently finish the merge fact

Files/lines:

- `trust-ci/src/adaptive_trust_ci/worker.py:197-224`
- `trust-ci/src/adaptive_trust_ci/runner.py:172-197`
- `trust-ci/src/adaptive_trust_ci/store.py:1246-1280`
- `trust-ci/sql/004_production_promotions.sql:56-77,429-485`

`process_next_merge_fact` persists protected evidence and completes the merge
fact in two separate database transactions. A crash, lease expiry, or database
response loss after `record_protected_branch_evidence` commits but before
`complete_merge_fact` succeeds leaves a retryable merge fact with valid evidence
already stored.

On retry, `run_protected_branch` generates a fresh random
`source_attestation_id` and a fresh signed envelope. PostgreSQL enforces a unique
exact tuple `(repository, protected_ref, merged_commit_sha, policy_epoch,
artifact_sha256)`, but `trust_ci_record_protected_branch_evidence` handles
conflict only on `source_attestation_id`. The new UUID therefore raises the
exact-tuple unique violation instead of recognizing the already committed
evidence. Every later retry generates another UUID and repeats the conflict
until the fact is exhausted/dead. The in-memory store does not enforce the
tuple uniqueness, so current unit coverage cannot expose this production-only
failure mode.

Impact: a normal crash window can strand a successfully validated merge,
publish a successful Check Run, and leave its durable processing state unable
to reach `completed`. This violates restart safety and the atomic/idempotent
producer-consumer chain required by AC-002/AC-007.

Required repair: make evidence persistence plus fact completion a single
lease-owned database transition, or make exact-tuple evidence insertion
idempotent and return/reuse the existing evidence before completing the fact.
Align `MemoryStore` with PostgreSQL exact-tuple uniqueness. Add a PostgreSQL
regression that commits evidence, simulates failure before completion, reclaims
after backoff/lease recovery, and proves one evidence row plus a completed fact.
Do not publish the final successful protected Check Run before the durable
evidence/completion transition is recoverably committed.

## Verification evidence

Current-tree focused run:

```text
PYTHONPATH=trust-ci/src:trust-ci/tests trust-ci/.venv/bin/python -m unittest -v \
  test_merge_provenance test_store test_api test_promotion_e2e \
  test_migrations test_database_roles
Ran 94 tests in 1.409s — OK
```

Additionally:

- `git diff --check`: pass.
- `python3 -m compileall -q .grok-stack/adaptive_grok scripts trust-ci/src`: pass.

The passing tests validate the prior fixes but do not cover the two-transaction
crash window above.

## Invariant and residual risks

- Development validation, PR delivery and merge remain automatic under
  `approval_rules: []`; no intermediate human signature was reintroduced.
- Exactly one human `promotion:production` signature remains at final
  production go/no-go.
- No private key, receipt, external mutation, merge or deployment action was
  performed in this review.
- A mature repository exceeding the bounded reconciliation window still
  requires an operator-seeded watermark; current behavior fails closed.
- Any repair changes the reviewed tree and requires fresh verification and a
  new independent code review.
