# Code review — round 2

## Verdict

**FAIL**

Round 2 confirms that four of the five prior Important findings are repaired and the prior Minor body-limit finding is repaired. The mutation-idempotency finding remains Important because several accepted mutation outcomes are still not bound to the required command key. AC-010 is therefore not satisfied.

## Review binding

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Round-1 reviewed head: `01643c6594947535e690c5722f710081c9b9db9f`
- Round-2 reviewed head: `9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Product-fix range: `01643c6594947535e690c5722f710081c9b9db9f..9bc51e81dddb8fc02f22171b586eb8c9caa7f304`
- Clean reviewed-head fingerprint before this report rewrite: `bae655f75a7cdb67f3ef7dced1c4f51cd83c2f016b558dbb44384a613335fcf2`
- Note: the requested abbreviation `9bc51e8c` does not resolve; the current intended commit and repository HEAD are the full `9bc51e81...` SHA above.

## Prior-finding disposition

| Round-1 finding | Round-2 disposition | Evidence |
| --- | --- | --- |
| Leased cancel/supersede leaks capacity | **Resolved** | `_close_active_lease` locks and releases the run/allocation and decrements ordered counters; both intake supersession and cancel call it (`factory/src/adaptive_factory/store.py:213-255,526-575,942-960`). Real PostgreSQL regression covers reader cancellation and writer supersession (`factory/tests/test_postgres_integration.py:79-116`). |
| Aggregate cost/token and wall budgets are not enforced | **Resolved** | Tasks persist a wall ceiling; reservations lock the task and check reserved + observed cost/tokens plus cumulative wall; usage settles live reservations before recording observed totals; completion requires usage and no live reservation (`factory/src/adaptive_factory/store.py:637-716,718-872`). PostgreSQL regressions cover exact replay, wall overflow, settlement, and completion gating (`factory/tests/test_postgres_integration.py:118-209`). |
| API mutation idempotency headers are discarded | **Not fully resolved — Important finding below** | Positive sequential replay is implemented for claim/heartbeat/release/kill/reconcile, but null claim outcomes, usage commands, and post-lease budget replay remain outside the durable command-result contract. |
| CLI UUID keys are rejected by cancel/kill storage | **Resolved** | `_command_key` canonicalizes documented header identifiers to 64-hex storage keys and cancel/kill use it (`factory/src/adaptive_factory/api.py:56-63,191-211,319-340`). Real API/PostgreSQL regression exercises a UUID kill key, replay, and changed-command rejection (`factory/tests/test_postgres_integration.py:250-273`). |
| Repository-scoped kill authorization missing | **Resolved** | Repository kills require repository membership and global kills require wildcard authority (`factory/src/adaptive_factory/service.py:129-141`), with cross-repository/global denial tests (`factory/tests/test_service.py:102-134`). |
| One-MiB limit trusts `Content-Length` | **Resolved** | Middleware cumulatively reads and caps streamed bytes and handles invalid lengths (`factory/src/adaptive_factory/api.py:108-126`); tests cover chunked/oversized and malformed-length requests (`factory/tests/test_api.py:90-111`). |

## Findings

### Important — the required mutation idempotency contract still has unrecorded outcomes

The durable command table is consulted at the start of claim, but every no-grant branch returns `None` without recording `{"grant": null}` (`factory/src/adaptive_factory/store.py:397-471`). Reusing the same `Idempotency-Key` after a kill is cleared, capacity frees, or work arrives can therefore lease a task even though the first accepted request returned no grant. This is exactly the lost-response/retry class that AC-010 requires to be stable.

The new usage endpoint also computes `_command_key(idempotency_key)` and discards the result (`factory/src/adaptive_factory/api.py:295-317`); storage deduplicates only by caller-controlled `provider_call_id`. Reusing one command key with a different provider-call ID creates another usage observation instead of rejecting changed command content. Budget reservation has the inverse ordering problem: it calls `_lock_grant` before looking up its idempotency row (`factory/src/adaptive_factory/store.py:718-740`), so an exact replay after release/expiry fails as a stale fence rather than returning the original reservation identity.

The sequential positive regression covers a granted claim and completed proposal, but it does not cover null claim replay, changed usage under one command key, or reservation replay after lease termination (`factory/tests/test_postgres_integration.py:211-273`). Persist all accepted mutation outcomes against command request/result digests before returning, consult command results before mutable lease-state checks where safe, and add those three real-PostgreSQL regressions.

### Minor — the committed full diff fails whitespace validation in stale round-1 evidence

`git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9bc51e81dddb8fc02f22171b586eb8c9caa7f304` reports trailing whitespace in the committed round-1 `evidence/release-review.md:7-9` and `evidence/test-review.md:7-10`. This is evidence-file hygiene rather than a product-code defect, but the exact reviewed range does not pass the repository's standard diff check.

## Verification commands and results

- `git diff --stat 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..HEAD` and `git diff --name-status 01643c6594947535e690c5722f710081c9b9db9f..HEAD` — inspected the 83-file full change and 40-file fix commit.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..HEAD` — **FAIL**, trailing whitespace only in the stale round-1 test/release evidence lines listed above.
- `uv run --project factory python -m unittest factory.tests.test_api factory.tests.test_service factory.tests.test_server factory.tests.test_contracts factory.tests.test_state factory.tests.test_migrations -v` — **PASS**, 30/30.
- `uv run --project factory python factory/tests/run_disposable_exit.py` — **PASS**, 40/40 against a fresh disposable PostgreSQL 17 container; effective-role/API/integration checks passed; actual restart produced one repair, replay no-op, higher fence, and late-holder rejection. The randomized disposable container was removed by the runner.
- Repository `tree_fingerprint(Path.cwd())` before this report rewrite — `bae655f75a7cdb67f3ef7dced1c4f51cd83c2f016b558dbb44384a613335fcf2`.

## Required disposition

Return the remaining idempotency finding to the route's single write owner. After repair, run focused null-claim, usage-key-reuse, and post-release reservation-replay PostgreSQL tests, then rerun final verification and all affected independent reviews against the new exact head/fingerprint.
