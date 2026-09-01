# Code review — M4 durable factory task control plane

## Verdict

**FAIL**

The reviewed implementation has Important correctness defects in lease/capacity cleanup, aggregate budget enforcement, mutation idempotency, and the documented API/CLI control surface. These defects violate AC-002, AC-005, AC-007, and AC-010, so this report must not be recorded as passing evidence.

## Review binding

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `01643c6594947535e690c5722f710081c9b9db9f`
- Reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f`
- Clean reviewed-head fingerprint (repository `tree_fingerprint` algorithm, before review reports appeared): `6831959f1205504b2c10f019a03a95d6143c01c3dc41a0de4cf90df81b7887f5`
- Change package reviewed: `brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, and `tasks.md`

## Findings

### Important — cancelling or superseding a leased task permanently leaks capacity

`factory/src/adaptive_factory/store.py:157-179` changes an active task to `superseded` and clears its current run/fence, while `factory/src/adaptive_factory/store.py:689-701` changes it to `cancelled`; neither path releases the run or its `capacity_allocations` row nor decrements the global/repository counters. Reconciliation cannot recover these allocations because `_lock_grant` requires the task to remain `leased` with the same current run/fence (`factory/src/adaptive_factory/store.py:424-439`). A sequence of leased cancellations or changed-authority submissions can therefore exhaust the 20/10/1 capacity permanently, contradicting atomic supersession and transactionally enforced capacity (AC-002/AC-005). Termination must release/fence the live run and allocation in the same locked transaction, with regression tests for reader and writer counters.

### Important — observed usage can exceed cost/token ceilings when reservations exist, and wall reservations are never bounded

Reservation admission correctly considers reserved plus observed cost/tokens (`factory/src/adaptive_factory/store.py:523-535`), but observation admission later compares only already-observed values (`factory/src/adaptive_factory/store.py:579-593`). For example, a USD 20 reservation followed by USD 10 observed usage is accepted against a USD 25 ceiling. Reservations are never consumed or released, so the code has no coherent accounting invariant. In addition, `wall_seconds` is validated as nonnegative and persisted but never summed or compared to the task's wall ceiling (`factory/src/adaptive_factory/store.py:512-547`). This violates the fail-closed hard ceilings in AC-007. Enforce one aggregate invariant under the task lock, define reservation consumption/release semantics, and test reservation-plus-observation and cumulative wall overflow.

### Important — API mutation idempotency headers are validated but discarded

The claim, heartbeat, proposal/release, and reconcile endpoints parse `Idempotency-Key` but never pass it to the service/store (`factory/src/adaptive_factory/api.py:184-237`, `factory/src/adaptive_factory/api.py:261-279`). Claim has no command identity at all, so retrying a request after a lost response can lease another task; retrying a completed proposal returns a stale-fence conflict rather than the original result. Reconciliation likewise creates a fresh run record for every retry. This does not meet AC-010's idempotency requirement. Persist command keys with request/result digests and return the original result for exact replays while rejecting key reuse with a changed request.

### Important — the shipped CLI generates idempotency keys rejected by cancel and kill storage

The API accepts header IDs matching `HEADER_ID`, and the CLI generates UUID strings (`factory/src/adaptive_factory/cli.py:62-64`). Cancel forwards that raw value into `task_events.idempotency_key`, whose SQL contract requires exactly 64 lowercase hex characters (`factory/src/adaptive_factory/store.py:689-701`, `factory/src/adaptive_factory/resources/001_initial.sql:67-77`), causing a database error. Kill rejects the same UUID before insertion because it explicitly requires `HEX64` (`factory/src/adaptive_factory/store.py:639-647`). Consequently the documented CLI `cancel`, `kill`, and `unkill` flows cannot succeed with their own generated headers, violating AC-010. Normalize command IDs to a canonical digest or make the API and storage contract consistently accept the documented identifier format, then add API-to-real-PostgreSQL tests.

### Important — repository-scoped kill authorization is not enforced at the resource boundary

`FactoryService.set_kill` checks only the `factory:kill` scope and operator kind (`factory/src/adaptive_factory/service.py:104-110`). It never checks a `repository:<id>` kill target against `actor.repositories`, even though tasks, lists, and claims apply that repository boundary. An operator credential restricted to one repository can therefore enable or disable another repository's kill switch. This violates the scoped/resource-isolated API requirement in AC-010. Require wildcard authorization for `global` and repository membership for repository-scoped kills, and cover cross-repository denial.

### Minor — the one-MiB request limit trusts `Content-Length` instead of bounding bytes read

The middleware rejects only when a supplied `Content-Length` exceeds the limit (`factory/src/adaptive_factory/api.py:104-109`). A chunked request or a request without that header is parsed without an actual-byte cap; a malformed length can also raise `ValueError`. This does not reliably implement the architecture's one-MiB body bound. Read at most `MAX_BODY_BYTES + 1` bytes (or use a server-enforced receive limit) before JSON parsing and return a bounded 400/413 response.

## Verification commands and results

- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..01643c6594947535e690c5722f710081c9b9db9f` — PASS.
- `git diff --stat` / `git diff --name-status` for the exact range — inspected 72 changed files and 4,351 insertions/14 deletions.
- `PYTHONPATH=factory/src:. python3 -m unittest discover -s factory/tests -p 'test_*.py' -v` — FAIL in this reviewer environment: 19 passed, five PostgreSQL tests skipped because no `FACTORY_TEST_DATABASE_URL` disposable database was provisioned, and `test_api` could not import the uninstalled `fastapi` dependency. This is not evidence that the committed integration suite passed.
- `python3 scripts/grok_verify.py --mode pr` — FAIL. Git diff, change spec, architecture, governance, secret scan, contract structure, SQL safety, Ruff, Bandit, coverage, and factory-unit checks passed; `python-unittest` failed. `source-stability` also failed because other route reviewers created `evidence/security-review.md` and `evidence/test-review.md` while this verification run was in progress.
- Repository `tree_fingerprint(Path.cwd())` before concurrent report writes — `6831959f1205504b2c10f019a03a95d6143c01c3dc41a0de4cf90df81b7887f5`.

## Required disposition

Return these findings to the single route-selected write owner. After repair, add real disposable-PostgreSQL regressions for leased cancel/supersede cleanup, mixed reserved/observed budgets, wall ceilings, command replay, CLI cancel/kill, and cross-repository kill denial; then rerun the root verifier and all affected independent reviews on one new exact head/fingerprint.
