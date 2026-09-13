# D/E integration preparation against frozen f31406e

Source: `/home/pall/grok-projects/adaptive-grok-build-pro-l5-production`, `f31406e970d67f7cd59694da5de88915adb0fa68`; current B inventory also inspected in `adaptive-grok-build-pro-l5-split-b`. No D worktree existed at inspection, so this checks the planned construction, not an implemented/tested D tree. No repository files or services were changed. Correct deploy inventory is **22 DEPLOY_MEMBERS**; preserve frozen source bytes and do not repeat the earlier 24-member description.

## Construction and remaining future imports

D's partial `factory/src/adaptive_factory/landing_host_config.py` is sufficient with the frozen docstring/future import, `os`, `Path`, `stat`, `SettingsError`, and the exact bodies of `_check_ancestry` (frozen lines 62–72) / `_private_directory` (75–83). No dataclass, FactorySettings import, strict JSON parser or loader is needed. Frozen landing_server imports only those two functions from the module.

E adds the frozen `LandingHostConfig` dataclass (14–18), `load_host_config` (21–59) and their imports; the completed file should match f31406e. E's landing_host imports/re-exports the config names, and its loader globals remain in landing_host_config. This is an actual dependency seam, not delayed dynamic import of a missing host.

A bounded AST import scan covered D's final HTTP, executor, media, SSE, normalizer, intake, SQLite, landing_server, settings, existing server, runtime, PDF-worker sources and the selected live-executor/media/SSE/normalizer/server test files. The only references to the future host, backup, publication CLI, delivery or governance packages were the already-known imports in test_landing_live_executors.py at lines **339, 340, 342 and 343**. Remove the whole final 339–372 tail for D and restore it in G; retain 268–338 and the concluding 373–377 assertions in D. No additional direct future imports were found in this bounded set. This is static import evidence, not a full transitive-isolation or test-pass claim.

Take frozen settings.py, landing_server.py and existing server.py in D together. In pyproject, D takes pypdf plus PDF package-data and uv.lock; E adds only adaptive-landing-server; adaptive-landing-state waits for G. Copy final test_server.py's settings expectations in D. Leave tests/__init__.py's delivery/governance bootstrap addition for F. D's source validator and artifact-builder helper must already be present from B / D respectively, and evidence union readers from C.

## Direct D fixture that does not need E

Prefer a small focused factory test module for landing_server composition, or add the cases to the already touched test_server.py if budget permits. Do not import HostFixture, landing_host or load_host_config. The new test module, if chosen, can be explicitly co-located under existing NODE-FACTORY-LOCAL-API; it does not add a production landing-source inventory entry.

Create TemporaryDirectory root with sibling owned mode-0700 directories `control`, `state`, `blobs`, `scratch`, `artifacts`; leave `source` absent for the default-off case. Construct directly:

```python
settings = FactorySettings(
    database_url="", socket_path=root / "control.sock", actors_file=root / "actors.json",
    landing_state_path=root / "state", landing_quarantine_path=root / "blobs",
    landing_source_path=root / "source", landing_scratch_path=root / "scratch",
    landing_output_path=root / "artifacts",
)
```

Call `compose_server_landing(settings, repository_root=root / "control")`. This API does not load actors or instantiate PostgreSQL. Keep root paths disjoint. A reopen helper creates a real SQLiteLandingJobStore at state with that same repository_root and immediately registers cleanup. Use dataclasses.replace to select `landing_live_enabled=True, landing_provider="qwen-intl"` for opt-in cases; do not use an operator credential file.

The following are the narrow independently testable D guarantees formerly expressed through E's host fixture:

| Case | Exact seam/setup | Required observation |
| --- | --- | --- |
| Default-off real ownership | Leave source/actors/Qwen file absent; call direct composition with `qwen_env_file=root / "absent-key"`. Guard `_trusted_source` and provider key functions against invocation. | Non-None OwnedLandingRuntime with real SQLite store; source/file remain absent. A second store raises LandingServiceError code `store_writer_active`; `owned.close()` twice permits a new owner. |
| Writer acquired before quarantine startup | Hold a real SQLite writer; patch `landing_server.PrivateLandingBlobStore` to raise AssertionError if called; compose default-off. | `store_writer_active`, blob-store constructor never called. This proves a losing owner cannot enter `_sweep_startup_orphans` (landing_intake constructor calls it), without duplicating orphan filename rules in the test. |
| Source validation before Qwen credentials, credentials after writer acquisition | In live settings, patch `landing_server._trusted_source` and `landing_renderer.ExactGitLandingWorkspace.validate_source`; the latter appends `source`. Patch `landing_live_executors.qwen_api_key` with a callback that asserts the supplied synthetic path, attempts a second real store and gets `store_writer_active`, appends `credential`, then raises RuntimeError to stop before HTTP. | Events exactly `['source', 'credential']`; no request is sent; after the expected failure a new real store opens. This ports final host test 265–284 without its loader. |
| Existing writer prevents credential read | Hold real SQLite writer; live source validations patched successful; key callback raises AssertionError if invoked. | `store_writer_active` and key callback not called. This ports host 304–316. Source validation still precedes the attempted writer acquisition in the frozen code. |
| Invalid source and other-provider selection do not read Qwen file | For qwen-intl, source validate raises a sentinel error. For grok-vision, source validation succeeds, generic API-key read returns a synthetic value and compose_landing_live_grok raises a sentinel before HTTP. In both cases guard qwen_api_key. | Exact respective sentinel error, no Qwen read, and any acquired store is released. This ports host 286–302. |
| Failure after ownership releases SQLite | In default-off mode patch `landing_server.PrivateLandingBlobStore` to raise RuntimeError, then KeyboardInterrupt, after store acquisition. | Original exception propagates and a new real store immediately opens. This exercises compose_server_landing's BaseException cleanup, independently of host startup. |

These are case requirements for the writer, not tests run by this read-only analysis. Scope can remain one focused fixture with parameterized failure cases, rather than one large new test hierarchy.

## Existing server's own lifespan wrapper

D changes existing `server.build_app`, so E's host lifespan tests cannot certify that wrapper. A bounded integration test can keep real landing composition/SQLite while patching only the pre-existing PG and actor seams:

- Patch `adaptive_factory.server.PostgresFactoryStore` and `_runtime_readiness` so no PG connection occurs; leave all semantic DSNs None and execution disabled. Patch load_actors with a synthetic Actor/token mapping. Keep real create_app and real compose_server_landing.
- The real build_app uses its own repository_root from `server.__file__`; temporary runtime directories are outside that tree, so the direct fixture paths remain valid. Do not assert its repository_root equals the synthetic control directory.
- Enter/exit the returned application's lifespan and prove the second SQLite owner is refused while active and accepted after normal or exceptional exit. `asyncio.run` with `async with app.router.lifespan_context(app)` permits a sentinel exception in the body without starting a listener or external request.
- Patch create_app to raise a sentinel after composition and prove the acquired writer is released. Keep the frozen regression `test_main_accepts_explicit_composition_before_preparing_socket`, which deliberately uses a plain object application and exercises the guarded app.state lookup.

Do not move E-only tests for dedicated landing routes, host config validation, Unix listener identity or the host's nested cleanup into D; they belong with their actual implementation in E. This report does not broaden the split into a new cleanup redesign.

## Exact D/E module and rule inventory

Current A/B/C inventory has 13 production `landing*.py` sources. D adds these six paths:

- Offline DOGFOOD + FIT-FACTORY-LANDING-DOGFOOD-BOUNDARY: `landing_host_config.py`, `landing_http.py`, `landing_media.py`, `landing_sse.py`, `resources/landing_pdf_worker.py`.
- LOCAL-API + new FIT-FACTORY-LANDING-HOST-BOUNDARY: `landing_server.py`.

D therefore has **19** sources: offline=16, SQLite=1, host=1, live=1. The SQLite owner stays NODE-FACTORY-LANDING-SQLITE while its direct-import rule remains DOGFOOD. Only landing_live_executors keeps LIVE ownership; landing_http remains offline with httpx forbidden.

E's production source delta is exactly **landing_host.py**, so E has **20**: offline=16, SQLite=1, host=2, live=1. Completing functions in the already-present landing_host_config does not add another inventory entry.

E model/test edits:

1. Add `factory/src/adaptive_factory/landing_host.py` to NODE-FACTORY-LOCAL-API.repository_paths and to FIT-FACTORY-LANDING-HOST-BOUNDARY.source_prefixes, retaining landing_server there.
2. Add the same source path to the mandatory core test's host GROUPS set. OWNERS['host'] and RULES['host'] were introduced in D and do not change.
3. Add `factory/tests/test_landing_host.py` to the existing LOCAL-API node's exact test ownership. Keep F's publication CLI and G's backup absent from every production inventory until introduced.
4. If E introduces landing-host.example.json, add its exact runtime path ownership (or the existing final factory/runtime owner prefix) alongside it. If all runtime templates wait for G, defer that owner-path addition too. Template ownership does not affect the landing Python count.
5. Keep A's already-applied exact urllib.parse exception assertion and its overlap fixture based on existing landing_artifact.py; neither needs a D/E update.

Run the inventory's actual-module coverage and synthetic forbidden-import regressions in both slices, alongside full prescribed verification and all budget checks. Module counts here were computed from the frozen source inventory minus E/F/G paths; they are construction acceptance criteria, not evidence that a future D or E branch already passes.
