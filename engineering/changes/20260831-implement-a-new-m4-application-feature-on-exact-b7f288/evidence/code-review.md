# Code review — round 3

## Verdict

**PASS**

No Critical or Important findings remain in the reviewed product tree. Every round-1 and round-2 code-review finding is resolved, the targeted repairs are covered by real PostgreSQL regressions, and focused reviewer evidence passes.

## Review binding

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `8435e23458885a48e2d5784f8cd01e84d978c28c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Round-3 fix range: `9bc51e81dddb8fc02f22171b586eb8c9caa7f304..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Verified product-head fingerprint before this report rewrite: `7f5f5a2c7eb5985b7b83643fee8158aba5a5fc4693eba826f58d9e9e1d519f70`
- Verification receipt: `.grok-stack/runtime/receipts/b7f288f1e81e/verification.json`, status `pass`, exact head and fingerprint above, created `2026-09-01T09:47:29+00:00`.

## Findings

None.

## Prior-finding closure

| Prior finding | Round-3 result | Evidence |
| --- | --- | --- |
| Cancel/supersede leaked active lease capacity | **Resolved** | Active run/allocation closure and ordered capacity-counter decrement are shared by cancel and supersession (`factory/src/adaptive_factory/store.py:213-255,540-575,996-1014`); PostgreSQL coverage remains at `factory/tests/test_postgres_integration.py:79-116`. |
| Reserved/observed cost and token totals plus wall ceilings were incoherent | **Resolved** | Reservation admission and usage settlement maintain locked aggregate counters, and completion requires settled accounting (`factory/src/adaptive_factory/store.py:643-722,724-926`); PostgreSQL coverage remains at `factory/tests/test_postgres_integration.py:118-209`. |
| Null claims were not durably replayed | **Resolved** | Command keys are transactionally serialized (`factory/src/adaptive_factory/store.py:89-103`), and every no-grant claim branch records `{"grant": null}` before returning (`factory/src/adaptive_factory/store.py:398-477`). The real API/PostgreSQL regression proves the same key remains null after work arrives and changed content conflicts (`factory/tests/test_postgres_integration.py:275-298`). |
| Usage discarded `Idempotency-Key` and correlation | **Resolved** | API, service, and store now pass command key/correlation end to end (`factory/src/adaptive_factory/api.py:296-320`, `factory/src/adaptive_factory/service.py:115-132`, `factory/src/adaptive_factory/store.py:791-926`). Exact replay returns the original result, changed provider-call content conflicts, and stored correlation is asserted (`factory/tests/test_postgres_integration.py:328-367`). |
| Reservation replay checked the live fence first | **Resolved** | Durable command replay now precedes `_lock_grant` (`factory/src/adaptive_factory/store.py:724-743`) and records the reservation result/correlation (`factory/src/adaptive_factory/store.py:744-789`). The PostgreSQL regression releases the lease, then obtains the original reservation result with the same command key (`factory/tests/test_postgres_integration.py:300-367`). |
| Concurrent command replays could race | **Resolved** | `_command_replay` takes a transaction-scoped advisory lock derived from the command key before reading the result (`factory/src/adaptive_factory/store.py:89-103`), serializing exact and conflicting concurrent commands. |
| CLI cancel/kill UUID keys did not match database keys | **Resolved** | API canonical command-key hashing remains consistently applied to cancel and kill (`factory/src/adaptive_factory/api.py:56-63,191-211,322-343`). |
| Repository/global kill authorization was incomplete | **Resolved** | Repository membership and wildcard global authority remain enforced (`factory/src/adaptive_factory/service.py:134-146`) with denial coverage in `factory/tests/test_service.py:102-134`. |
| Request body bound trusted only `Content-Length` | **Resolved** | Actual streamed bytes are cumulatively bounded and malformed lengths are handled (`factory/src/adaptive_factory/api.py:108-126`; `factory/tests/test_api.py:90-111`). |
| Round-2 diff-check whitespace failures | **Resolved** | The full base-to-head `git diff --check` is clean. |

## Additional surrounding-code review

- Migration `006` narrows runtime updates to `capacity_counters.active_count` and removes runtime update authority from intake identities (`factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`); migration discovery/readiness now require contiguous version 6.
- Intake identity creation uses a stable transaction advisory lock rather than depending on update privilege for row locking (`factory/src/adaptive_factory/store.py:214-226`).
- The final command-result implementation binds actor, action, canonical request digest, correlation, and bounded JSON result; changed content under the same key fails closed.
- No provider execution, shell/repository command, TCP server option, Git/GitHub write, deployment, production mutation, or Trust CI authority was introduced.

## Verification commands and results

- `git diff --stat 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c` — inspected 84 changed files, 6,535 insertions, and 14 deletions.
- `git diff --name-status 9bc51e81dddb8fc02f22171b586eb8c9caa7f304..8435e23458885a48e2d5784f8cd01e84d978c28c` — inspected all 18 round-3 repair/evidence files.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c` — **PASS**.
- `uv run --project factory python -m unittest factory.tests.test_api factory.tests.test_service factory.tests.test_server factory.tests.test_contracts factory.tests.test_state factory.tests.test_migrations -v` — **PASS**, 30/30.
- `uv run --project factory python factory/tests/run_disposable_exit.py` — **PASS**, 42/42 against a fresh disposable PostgreSQL 17 container; null-claim replay, accounting command replay/correlation, capacity, fencing, retry, budget, kill, privilege, API, and migration tests passed. The actual restart probe also passed: one repair, replay no-op, higher fence, and late-holder rejection. The randomized container was removed by the runner.
- Existing exact-head `python3 scripts/grok_verify.py --mode pr` receipt — **PASS**: 485 root tests, factory unit, disposable PostgreSQL exit, architecture, governance, contract, SQL safety, Ruff, Bandit, secret scan, coverage, diff check, and source stability all passed on HEAD `8435e234...` and fingerprint `7f5f5a2c...`.

## Residual risk

The feature remains source-only and local. Deployment, any non-disposable migration, PR/merge, and external Trust CI authority remain separately gated; this code review does not authorize them.
