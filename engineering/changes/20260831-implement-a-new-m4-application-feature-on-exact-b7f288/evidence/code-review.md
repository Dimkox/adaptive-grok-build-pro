# Code review — round 5

## Verdict

**PASS**

No Critical or Important findings remain in the exact reviewed tree. Migration 008 closes runtime authority over allocation release state, grant validation now requires a live allocation, and the privilege-compatible locking changes preserve release, cancellation, supersession, fencing, and reconciliation behavior.

## Review binding

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Round-5 delta: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Verified product-head fingerprint before this report rewrite: `e4ac983f20ea22120e98b5eb6597fa6d47486225000a29caf1ab45cadc726b6a`
- Verification receipt: `.grok-stack/runtime/receipts/b7f288f1e81e/verification.json`, status `pass`, bound to the exact head and fingerprint above, created `2026-09-01T10:48:22+00:00`.

## Findings

None.

## Round-5 delta review

- Migration 008 revokes runtime `UPDATE` authority on `factory.capacity_allocations`, removing the inherited column grant that allowed a runtime caller to hide or restore a live allocation outside `capacity_release()` (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). The fresh effective-role regression verifies both release and restoration statements fail with insufficient privilege (`factory/tests/test_postgres_integration.py:614-658`).
- `_lock_grant` now requires `a.released_at IS NULL`, so heartbeat, reservation, usage, and release reject a grant whose allocation is not live (`factory/src/adaptive_factory/store.py:581-598,600-655,691-893`). Exact durable command replay still intentionally precedes live-fence validation and performs no new mutation.
- Runtime can no longer take `FOR UPDATE` locks on allocation rows after migration 008, so close/grant queries lock only the mutable run/task rows (`factory/src/adaptive_factory/store.py:528-575,581-598`). This remains safe: supported allocation mutation is confined to the security-definer release function, release paths acquire ordered capacity locks first, and run/task locks serialize live-grant mutation against run closure (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:56-78,127-158`; `factory/src/adaptive_factory/store.py:523-575,618-677`).
- A privileged corruption regression hides a live allocation and proves heartbeat, release, reservation, and usage all reject the fence; readiness becomes not-ready and reconciliation fails closed. Restoring the projection allows normal usage/release and returns readiness to ready (`factory/tests/test_postgres_integration.py:672-716`).
- Readiness now requires exact schema version 8 as well as counter/allocation agreement (`factory/src/adaptive_factory/store.py:61-85`). Migration discovery and SQL assertions require contiguous migrations 001–008 and the allocation-update revocation (`factory/tests/test_migrations.py:6-51`).
- Root/factory rollout and recovery documentation consistently identifies eight migrations, exact rollout schema 008, and forward recovery via 009+ (`README.md:13`; `factory/README.md:18,32-34`; `engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/architecture.md:31`; `engineering/changes/20260831-implement-a-new-m4-application-feature-on-exact-b7f288/rollback.md:5`).
- The installer payload recursively includes `factory/src`; its regression explicitly asserts migration 008 is transferred (`scripts/install_into.py:20-41`; `tests/test_installer.py:144-176`). The exact-head root verifier also passed the full installer suite.

## Prior-finding closure

| Prior finding | Round-5 result | Evidence |
| --- | --- | --- |
| Runtime could directly hide or restore a capacity allocation | **Resolved** | Migration 008 revokes allocation updates, and effective-role probes deny both directions (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`; `factory/tests/test_postgres_integration.py:637-658`). |
| Hidden allocation did not invalidate every live grant operation | **Resolved** | `_lock_grant` requires a live allocation and the corruption regression covers heartbeat, release, reservation, and usage plus readiness/reconciliation (`factory/src/adaptive_factory/store.py:581-598`; `factory/tests/test_postgres_integration.py:672-716`). |
| Runtime could insert arbitrary capacity ceilings or overwrite active counts | **Resolved** | The canonical constraint, revoked counter DML, and constrained definer functions remain unchanged (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-169`); effective-role and 20/10/1 regressions pass. |
| Cancel/supersede leaked active lease capacity | **Resolved** | All close paths still use ordered capacity locking and `capacity_release()`; PostgreSQL lifecycle regressions pass (`factory/src/adaptive_factory/store.py:523-575,618-677,964-983`). |
| Reserved/observed totals and wall ceilings were incoherent | **Resolved** | Locked accounting aggregates, settlement checks, and budget regressions remain green. |
| Null claims were not durably replayed | **Resolved** | No-grant command results remain durable and replay before capacity/work selection; the PostgreSQL replay regression passes (`factory/src/adaptive_factory/store.py:418-449`). |
| Usage discarded `Idempotency-Key` and correlation | **Resolved** | End-to-end command propagation and durable replay/correlation tests remain green. |
| Reservation replay checked the live fence first | **Resolved** | Exact replay still precedes `_lock_grant`; the released-lease replay regression remains green (`factory/src/adaptive_factory/store.py:691-710`). |
| Concurrent command replays could race | **Resolved** | Transaction advisory serialization remains at `factory/src/adaptive_factory/store.py:109-120`. |
| CLI cancel/kill command keys, kill authorization, and request-body bounding were defective | **Resolved** | The API/service implementations are unchanged by the delta and focused authorization/body/idempotency tests pass. |
| Diff-check whitespace failures | **Resolved** | The full base-to-head diff check is clean. |

## Verification commands and results

- `git diff --stat 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe` — inspected the full 86-file range: 6,801 insertions and 14 deletions.
- `git diff --name-status 9fd2a56c57f834ad39c03a2f748bdbaefc79c91c..f82134de35e531a8b3bbf235ad480254ba40f1fe` — inspected all 20 round-5 migration, store, test, installer, documentation, and evidence files.
- `git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe` — **PASS**.
- `uv run --project factory python -m unittest factory.tests.test_api factory.tests.test_service factory.tests.test_server factory.tests.test_contracts factory.tests.test_state factory.tests.test_migrations -v` — **PASS**, 30/30.
- `uv run --project factory python factory/tests/run_disposable_exit.py` — **PASS**, 43/43 against a fresh disposable PostgreSQL 17 container. Effective-role denial, supported capacity lifecycle, hidden-allocation fencing, fail-closed readiness/reconciliation, replay/correlation, accounting, cancellation/supersession, concurrency, retry, kill, migrations, API, and actual restart/two-pass reconciliation passed; the randomized container was removed.
- Existing exact-head `python3 scripts/grok_verify.py --mode pr` receipt — **PASS** on the exact HEAD/fingerprint above: 485 root tests, 21 focused factory unit tests, 43 disposable PostgreSQL tests, architecture, governance, contracts, SQL safety, Ruff, Bandit, secret scan, coverage, diff check, and source stability all passed.
- `python3 scripts/grok_status.py` — exact verification is present; only the expected round-5 review receipt gaps remain.

## Residual risk

Migration 008 changes a live database privilege and must be applied by the trusted migrator before starting schema-v8 runtime code. Deployment, non-disposable migration, PR/merge, and external Trust CI authority remain separately gated; this local code review authorizes none of them.
