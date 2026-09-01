# Code review — round 4

## Verdict

**PASS**

No Critical or Important findings remain in the reviewed product tree. The database now owns the capacity ceilings and counter mutations, the runtime store uses only the bounded capacity functions, readiness fails closed on capacity drift, and every earlier code-review finding remains resolved.

## Review binding

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Round-4 fix range: `8435e23458885a48e2d5784f8cd01e84d978c28c..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Verified product-head fingerprint before this report rewrite: `463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4`
- Verification receipt: `.grok-stack/runtime/receipts/b7f288f1e81e/verification.json`, status `pass`, bound to the exact head and fingerprint above, created `2026-09-01T10:14:11+00:00`.

## Findings

None.

## Round-4 capacity-authority review

- The database constraint permits only the canonical global reader/writer rows and bounded repository-reader rows, with immutable policy ceilings 20, 1, and 10 respectively (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-9`). Runtime cannot create an arbitrary scope/ceiling that satisfies this constraint.
- All four capacity entry points are `SECURITY DEFINER`, set a trusted `pg_catalog,factory` search path, use static qualified SQL, validate role and repository identity, and expose bounded operations rather than generic mutation (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-158`). No caller-controlled identifier or dynamic SQL reaches the definer context.
- Allocation verifies that the requested task, repository, role, and leased run agree, locks all applicable counters in deterministic key order, enforces their ceilings, inserts at most one live allocation, and increments only the corresponding canonical rows (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:80-125`).
- Release locks the same counters, requires the run to be closed first, rejects underflow, closes the live allocation, and decrements exactly those counters (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:127-158`).
- `PUBLIC` execution and runtime raw insert/update authority are revoked; runtime receives execution only on the four constrained functions (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:160-169`). The effective-role regression proves runtime cannot insert a counter or update either `ceiling` or `active_count` (`factory/tests/test_postgres_integration.py:614-656`).
- Claim eligibility and allocation now use the database functions (`factory/src/adaptive_factory/store.py:418-521`); close, orphan-repair, release, cancellation, and supersession share the database-owned lock/release path (`factory/src/adaptive_factory/store.py:523-579,617-677,964-983`). The integration lifecycle exercises claim, usage, completion, release, and readiness under the runtime role (`factory/tests/test_postgres_integration.py:657-668`).
- Readiness requires schema version 7 and recomputes every capacity counter from live allocations; metrics also derives active capacity from live allocations rather than mutable projections (`factory/src/adaptive_factory/store.py:61-107`). This makes migration omission or counter/allocation drift visible and not-ready.

## Prior-finding closure

| Prior finding | Round-4 result | Evidence |
| --- | --- | --- |
| Runtime could insert arbitrary repository capacity ceilings or overwrite active counts | **Resolved** | Canonical database constraint, revoked runtime DML, and constrained definer functions are in migration 007 (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-169`); effective-role denial and lifecycle coverage are at `factory/tests/test_postgres_integration.py:614-668`. |
| Cancel/supersede leaked active lease capacity | **Resolved** | All active-lease closure paths now call the locked database release function (`factory/src/adaptive_factory/store.py:523-579,617-677,964-983`), with PostgreSQL regression coverage. |
| Reserved/observed cost, tokens, output, and wall ceilings were incoherent | **Resolved** | Locked reservation/usage aggregates and completion settlement checks remain in place, with PostgreSQL budget/accounting regressions passing. |
| Null claims were not durably replayed | **Resolved** | Claim records every no-grant result and replays it before capacity/work selection (`factory/src/adaptive_factory/store.py:418-449`); the real PostgreSQL/API replay regression passes. |
| Usage discarded `Idempotency-Key` and correlation | **Resolved** | API-to-store propagation and durable result/correlation replay remain in place; the accounting replay regression passes. |
| Reservation replay checked the live fence first | **Resolved** | Command replay still precedes grant/fence locking; the released-lease replay regression passes. |
| Concurrent command replays could race | **Resolved** | Transaction advisory serialization remains at `factory/src/adaptive_factory/store.py:109-120`. |
| CLI cancel/kill UUID keys did not match database keys | **Resolved** | Canonical command-key hashing remains consistently applied; focused API tests pass. |
| Repository/global kill authorization was incomplete | **Resolved** | Repository membership and wildcard global authority remain enforced; focused service denial tests pass. |
| Request body bound trusted only `Content-Length` | **Resolved** | Actual streamed bytes remain cumulatively bounded and malformed/missing lengths are rejected; focused API tests pass. |
| Diff-check whitespace failures | **Resolved** | The full base-to-head `git diff --check` is clean. |

## Verification commands and results

- `git diff --stat 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` — inspected the full 85-file product/change-package range: 6,706 insertions and 14 deletions.
- `git diff --name-status 8435e23458885a48e2d5784f8cd01e84d978c28c..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` — inspected all 21 round-4 repair, test, documentation, and evidence files.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` — **PASS**.
- `uv run --project factory python -m unittest factory.tests.test_api factory.tests.test_service factory.tests.test_server factory.tests.test_contracts factory.tests.test_state factory.tests.test_migrations -v` — **PASS**, 30/30.
- `uv run --project factory python factory/tests/run_disposable_exit.py` — **PASS**, 42/42 against a fresh disposable PostgreSQL 17 container. This covers effective runtime privileges, capacity enforcement/lifecycle, null-claim replay, accounting replay/correlation, reservation-before-fence replay, cancellation/supersession, retry, budget, kill, migration, and API behavior. The actual restart probe also passed: one repair, replay no-op, higher fence, and late-holder rejection; the randomized container was removed.
- Existing exact-head `python3 scripts/grok_verify.py --mode pr` receipt — **PASS** on HEAD `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c` and fingerprint `463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4`; it includes 485 root tests, factory unit and disposable-PostgreSQL exit suites, architecture/governance/contract/SQL-safety checks, Ruff, Bandit, secret scan, coverage, diff check, and source stability.

## Residual risk

Migration 007 changes live database privileges and must be applied by the trusted migration owner before the schema-v7 runtime is started. Deployment, non-disposable migration, PR/merge, and external Trust CI authority remain separately gated; this local code review authorizes none of them.
