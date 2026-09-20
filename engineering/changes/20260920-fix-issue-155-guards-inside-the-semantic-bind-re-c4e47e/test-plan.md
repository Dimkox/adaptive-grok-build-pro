# Test plan — Fix issue #155: semantic_bind_repair_child guard rejections and PostgreSQL tier determinism

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes. Raw run output lives in [`evidence/postgres-evidence.md`](evidence/postgres-evidence.md); rerun rows are appended there, never edited into earlier rows.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | A refused bind reports the guard that refused it, at the SQL boundary and in the `StoreError` text | `factory/tests/test_postgres_integration.py` (scenario asserts on named reasons), `evidence` §4 |
| P0 | A malformed payload keeps `invalid_object`; the envelope is recognised only when it is the exact one-key document | `factory/tests/test_migrations.py` (offline envelope tests) |
| P0 | Shipped history stays immutable: `018` byte-identical, `021` applies over a `001-020` cluster with no drift | `factory/tests/test_migrations.py`, live cluster check in `evidence` §6 |
| P0 | Mandatory disposable-exit tier: four consecutive passes | `factory/tests/run_disposable_exit.py`, `evidence` §10 |
| P1 | Load inside the intake window cannot cross the child deadline | delay-injection probe with a control that flips: `evidence` §3, §4 |
| P1 | Tier length cannot expire an HTTP intake authority | aging-`NOW` control (`stale=0` / `stale=400`), `evidence` §13 |
| P1 | The 300 s authority window is still enforced after the fixture change | the same test asserts 422 `stale_m0` for a 400 s-old proof |
| P2 | Guard clause text of `021` stays equivalent to `018` | clause-level equality test in `test_migrations.py` |

## Automated checks

- Unit (Docker-free): `python3 -m unittest -q factory.tests.test_migrations` — envelope strictness, allowlist folding, SQL↔Python vocabulary equality, applied-prefix counts.
- Integration (disposable PostgreSQL 17): the full mandatory tier `python3 -u factory/tests/run_disposable_exit.py`, which runs `postgres_restart_probe.py --preflight-only`, `unittest discover -s factory/tests -t .` (776 tests) and the actual-restart reconciliation probe.
- Contract: no declared contract changes; `tests/test_architecture_fitness.py` and `tests/test_structure.py` stay green on the delivered tree (`Ran 144 tests OK`).
- E2E: the HTTP intake path is exercised through `TestClient(create_app(...))` inside the integration tier — accepted fresh proof, deduplicated replay, 409 command conflict, superseding replacement, and now a refused expired proof.
- Static analysis: `ruff check factory/src/adaptive_factory/ factory/tests/ tests/` — 6 findings, all pre-existing `F401`; baseline measured by stashing the change, so **zero new findings**. `git diff --check` clean. Note `factory/src/adaptive_grok*` from the route's command does not exist in this tree.

## Manual checks

- Guard enumeration re-read off `018:1335-1525` (56 `RETURN NULL` occurrences in the file, 8 statements + 1 `ELSE NULL` arm inside the function = 9 paths over 48 clauses) — this corrects the issue's "~15 guards" estimate before anything was designed against it.
- Live upgrade on a cluster that already had `001-020` applied, reading `schema_migrations` afterwards (`evidence` §6).
- Rejection reasons read directly from the SQL boundary with `psql` (`evidence` §4).
- Streak hygiene: per-attempt duration and loadavg recorded, product-tree fingerprint stamped before and after the streak, so a mid-streak product edit cannot be hidden (`SIG-002`).
