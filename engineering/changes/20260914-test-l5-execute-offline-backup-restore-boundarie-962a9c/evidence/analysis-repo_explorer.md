# Coupling map: factory/tests (2026-09-14, agent repo_explorer)

## 1. Test->test edges (importer:file:line -> module: symbols)
- test_landing_artifact.py:34 -> test_landing_renderer: landing_spec, sealed_target
- test_landing_runtime.py:47 -> test_landing_renderer: landing_spec, sealed_target
- test_landing_coordinator.py:18 -> test_landing_renderer: landing_spec, sealed_target
- test_landing_live.py:30-31 -> test_landing_normalizer: RecordingExecutor, draft; test_landing_renderer: sealed_target
- test_landing_live_executors.py:49-50 -> test_landing_normalizer: draft, source; test_landing_renderer: sealed_target
- test_landing_live_executors.py:399 (in-test) -> test_landing_runtime: BoundProvider, PROFILE_DIGEST
- test_landing_publication_cli.py:26 -> test_landing_artifact: candidate_fixture; :186 (in-test) -> test_landing_renderer: landing_spec
- test_landing_api.py:29-31 -> test_api: FakeService; test_landing_provider: clock, profile
- test_landing_backup.py:18 -> test_landing_host: HostFixture <-- only heavy-sharing edge
- test_api.py:37 -> test_contracts: valid_intake
- test_service.py:17 -> test_contracts: valid_intake
- test_postgres_integration.py:47-49 -> test_contracts: valid_intake; test_execution_contracts: valid_packet; test_execution_service: trusted_registry
- test_execution_persistence_postgres.py:60-70 -> test_contracts: valid_intake; test_api: FakeService; test_brokers: PACKET, RUN, TASK, context; test_execution_contracts: valid_packet; test_execution_service: block; test_postgres_integration: DATABASE_URL, NOW, OPERATOR, WORKER
- test_adapters.py:13 -> test_execution_contracts: valid_packet
- test_execution_service.py:23 -> test_execution_contracts: valid_packet, valid_workspace_result
- test_semantic_bridge.py:17 -> test_execution_contracts: valid_packet
- test_semantic_persistence.py:12 -> test_semantic_bridge: bridge_material
- test_autonomy_schema.py:17 -> test_autonomy: valid_cohort_payload, valid_handoff_payload
- test_semantic_repair.py:6 -> test_semantic_contracts: coverage, finding, subject
- test_semantic_adjudication.py:8 -> test_semantic_contracts: coverage, finding, subject, validator
- test_semantic_service_api.py:17 -> test_semantic_contracts: coverage, finding, subject, validator
- test_semantic_repair_lifecycle.py:16-17 -> test_semantic_contracts; test_semantic_persistence: FakeConnection, FakeCursor
- test_semantic_store_runtime.py:13-14 -> test_semantic_contracts; test_semantic_persistence: FakeConnection, FakeCursor

## 2. Heavyweight dep per importer (F=functional, I=incidental via shared test import)
- No heavy need (importer and imported modules are stdlib/contracts only): test_landing_artifact,
  test_landing_runtime, test_landing_coordinator, test_landing_live, test_landing_publication_cli,
  test_service, test_adapters, test_autonomy_schema, test_execution_service, test_semantic_bridge,
  test_semantic_repair, test_semantic_adjudication, test_contracts, test_execution_contracts,
  test_semantic_contracts, test_brokers, test_autonomy, test_landing_renderer, test_landing_normalizer,
  test_landing_provider.
- fastapi F: test_api.py:12, test_landing_api.py:11, test_semantic_persistence.py:5,
  test_semantic_service_api.py:5, test_execution_persistence_postgres.py:11, test_landing_host.py:17.
- httpx F: test_landing_live_executors.py:19 (16 call sites). test_api additionally pulls httpx via
  adaptive_factory/cli.py:9 (test_api.py:15).
- psycopg F: test_workspace.py:4 (module level); test_postgres_integration /
  test_execution_persistence_postgres import it inside each test.
- pypdf: never module level anywhere; only test_landing_pdf_worker.py:68 inside a test -> zero coupling risk.
- fastapi I: test_semantic_repair_lifecycle and test_semantic_store_runtime (both 0 TestClient mentions)
  via test_semantic_persistence.py:5.
- fastapi I + uvicorn I: test_landing_backup via test_landing_host.py:17,19,29 (details below).

## 3. test_landing_backup.py vs HostFixture
- Used symbols: setUp via super() (:22), write_config (:27), reopen_store (:28,92,104,120,131,173,279),
  and attributes root/config_path/data built in test_landing_host.py:41-62.
  write_config defined at test_landing_host.py:64, reopen_store at :77.
- Never calls build_app (test_landing_host.py:70-76) — the only HostFixture member that touches
  landing_host/TestClient.
- None of the used symbols need adaptive_factory.landing_host, .api, .server, fastapi or uvicorn:
  reopen_store only uses SQLiteLandingJobStore (landing_sqlite_store.py -> sqlite3/fcntl;
  landing_service/landing_artifact have 0 heavy imports).
- landing_backup itself is stdlib-only (landing_backup.py:16-20). The strings "fastapi"/"uvicorn"/
  "httpx"/"psycopg" at test_landing_backup.py:43-46 are the subprocess import-guard's blocklist,
  not real imports.

## 4. Module-level chain that breaks test_landing_backup without fastapi
1. test_landing_backup.py:18 -> test_landing_host.py:17 `from fastapi.testclient import TestClient` (raises at collection).
2. Independently: test_landing_host.py:19 -> landing_host.py:11 `import uvicorn` and landing_host.py:13 -> api.py:14-16 fastapi.
3. Independently: test_landing_host.py:29 -> server.py:10 `import uvicorn` and server.py:12-13 -> api.py / landing_server -> fastapi.

Fix direction: HostFixture's offline subset (setUp/write_config/reopen_store) has no fastapi/uvicorn
surface; only build_app/run_main do.
