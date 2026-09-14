# Analysis — extract offline HostFixture (agent architect)

## Summary
1. New file `factory/tests/landing_host_fixture.py` — flat helper next to `postgres_restart_probe.py`,
   imported `from factory.tests import ...`.
2. Move `ROOT_FIELDS`, `PATH_FIELDS`, and `HostFixture` minus `build_app`
   (setUp/write_config/reopen_store only).
3. Keep in `test_landing_host.py`: `build_app`, TestClient/landing_host/prepare_unix_socket/uvicorn usage
   — the web-stack half.
4. `test_landing_host.py` keeps its ~20 tests with zero body edits by `class HostFixture(BaseHostFixture)`
   re-adding only `build_app`; `test_landing_backup.py` changes one import line.
5. No fitness rule trips: FIT-BOUNDED-FACTORY-SOURCE-CHANGE covers `factory/src` only; `factory/tests`
   budget (7500 lines) is untouched at ~50 moved lines.
6. No registration required in .coveragerc, bandit.yaml, ruff, discovery, inventory, or install_into manifest.

## 1. Path & naming (decided: `factory/tests/landing_host_fixture.py`)
- Precedent for non-test helpers flat under `factory/tests/`: `postgres_restart_probe.py`,
  `run_disposable_exit.py`, imported as `from factory.tests import postgres_restart_probe, run_disposable_exit`
  (`factory/tests/test_migrations.py:7`).
- `factory/tests/__init__.py` exists (9 lines) and injects `factory/src`, `delivery/src`, `.grok-stack`
  into `sys.path`, so helper imports work without installation.
- Name mirrors `factory/tests/fixtures/landing_provider_fixture.py`; not a `test_*.py`, so unittest
  discovery ignores it.

## 2. Symbol split
- Move: `ROOT_FIELDS` (`test_landing_host.py:33-36`), `PATH_FIELDS` (`:38`), `HostFixture` (`:40-82`)
  = `setUp` (`:41-60`), `write_config` (`:62-66`), `reopen_store` (`:77-82`). Their deps are offline-safe:
  `json/Path/tempfile/uuid4`, `Actor` (`adaptive_factory.models`), `SQLiteLandingJobStore`
  (`landing_sqlite_store`), `TARGET_REPOSITORY_ID` (`landing_renderer`) — none of those modules import
  fastapi/httpx/uvicorn (grep: zero matches).
- Must stay: `build_app` (`:70-75`, calls `landing_host.load_host_config`/`build_landing_app`, patches
  `landing_host.load_actors`); TestClient (`:17, :218`), `prepare_unix_socket`/`ServerError` (`:29`,
  `LandingHostMainTests` `:365+`), `landing_host.uvicorn` patch (`:373`), `ExitStack/SimpleNamespace/
  socket/stat/asyncio` (`:4,12,8,9,3`).
- This is exactly what makes the backup guard viable: it blocks `fastapi`, `landing_host`, `server`,
  `httpx`, `uvicorn` at import (`test_landing_backup.py:36-41`), and backup uses only `setUp`-state,
  `write_config`, `reopen_store` (`test_landing_backup.py:26-29,92,120,131` — no `build_app`).

## 3. Compatibility of test_landing_host.py (import-and-subclass, not rename)
- `from factory.tests.landing_host_fixture import HostFixture as LandingHostFixture` + re-import
  `ROOT_FIELDS, PATH_FIELDS`; local `class HostFixture(LandingHostFixture):` containing only the moved
  `build_app`.
- Test classes `LandingHostConfigTests` (`:85`), `LandingHostCompositionTests` (`:204`),
  `LandingHostMainTests` (`:365`) keep resolving `HostFixture` inside the module -> ~20 test bodies unchanged.
- `test_landing_backup.py:18` becomes `from factory.tests.landing_host_fixture import HostFixture`
  (single-line diff).

## 4. Fitness / budget / registration — nothing trips
- `FIT-BOUNDED-FACTORY-SOURCE-CHANGE` path_prefixes = `["factory/src"]` (`architecture/rules.yaml:86-93`)
  -> `factory/tests/**` does not count against it. Applicable budget: `FIT-BOUNDED-FACTORY-TEST-CHANGE`
  = 7500 lines/775000 bytes/AST 600 (`rules.yaml:106-114`) and `FIT-BOUNDED-FACTORY-CHANGE` (`:76-83`);
  a ~50+10-line move is far under (compare enforcement cases in `tests/test_architecture_fitness.py:3536-3588`).
- `.coveragerc`: source is only `.grok-stack/adaptive_grok` + `scripts`, `omit = tests/*` -> no change.
  `bandit.yaml` excludes tests dirs, skips B101 -> no change. `ruff.toml`: not excluded, but only
  E4/E7/E9/F, line-length 120 — helper is already compliant style.
- Inventory: `NODE-FACTORY-LOCAL-API.repository_paths` lists `factory/tests/test_landing_host.py`
  (`architecture/system.yaml:1383`) but is an ownership list, not exhaustive — `test_landing_backup.py`,
  `postgres_restart_probe.py` are unlisted and pass; no "every file registered" check exists in
  `tests/test_architecture_fitness.py:616-894`. Precedent ruling: new test modules are co-located under
  the existing node without new inventory entries
  (`engineering/changes/20260913-l5-split-d-bounded-http-models-and-durable-runti-bec1fc/evidence/split-de-integration.md:17`).
- `scripts/install_into.py:32-41` MANAGED_FILES registers only legacy web-stack tests (no `test_landing_*`)
  -> no registration needed; adding a path there would require installer test updates for no benefit.
