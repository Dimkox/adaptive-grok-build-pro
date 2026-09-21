# Runner capacity and fallback evidence analysis

Route: `45e0cc3b5da0`; role: `ai_architect`; 2026-09-21.
Static analysis only: no tests, imports, probes, compilation, lint, Docker, or external operations were run.
The route's AI domain was triggered by `_score` matching the `rag` keyword inside `coverage` (`router.py` lines35,180-184); there is no actual AI data path, model, RAG, provider call, tenant-data transfer, or AI evaluation change.

## Evidence inspected

- Current runner `.grok-stack/adaptive_grok/python_test_runner.py`, verifier `_python` integration, runner tests, `.coveragerc`, change brief, and prior capacity research.
- Retained PR135 source `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8` via its actual Git diff. Its change adds `_parallel_process_cleanup_supported()` and degrades engine selection when cleanup is unsupported, before command construction.
- Source locations below refer to the inspected pre-implementation tree; these findings are not verification receipts or fresh RED evidence.

## Selection and evidence invariants

1. `selected_workers` currently returns `None` without opt-in, zero for an opted-in child, and the explicit integer unchanged; preserve these distinctions (runner lines41-74). Only `auto` should consult the new quota calculation.
2. Linux auto capacity must bound the existing affinity/CPU count and 28-worker cap by known effective quota. A valid positive fractional limit must still choose at least one; unlimited must not mean zero available CPUs. This is a worker budget, not proof of current spare CPU/PID capacity.
3. Missing or malformed quota information needs a documented fallback distinct from an unlimited value. Test the selected result through controlled fixture data, independent of this host's actual cgroups.
4. Preserve PR135's pre-launch platform-capability decision. Existing `_pytest_command` rejects non-POSIX cleanup only after `select_engine` currently chooses xdist; carrying the retained seam fixes that timing without weakening the defensive guard.
5. Engine fallback happens once before execution. Do not retry serially after an assertion, collection error, worker crash, timeout, dependency-pin failure, or incomplete coverage result.
6. Importable parallel dependencies remain pinned on a supported platform. Serial fast mode needs no parallel distribution pins; serial measured mode still requires the pinned coverage package and `.coveragerc` (runner lines183-244).
7. Existing Core observability is correct: verifier line951 substitutes `core.workers` before producing the backend/worker summary, preserves requested count separately, and stores `versions['engine']`. Retain `unittest-degraded` for unavailable parallel capability and `unittest` for an explicit serial request.
8. Trust CLI lines294-304 already disclose requested workers, actual workers, selected engine, timing, and exit. Capacity reduction must not turn an unavailable measurement into a claimed pass or claim xdist ran when only unittest ran.

## Concrete fallback gap: empty discovery can become success

- Core serial execution is plain `unittest discover` (lines241-245), and Trust serial execution follows the same pattern (lines279-285).
- There is no collected/executed-test count check in either path. Unittest's successful empty discovery exit is passed through; verifier lines954-956 classify only by return code.
- Pytest rejects zero collection, so this is an existing semantic difference exposed whenever dependencies or Windows platform capability force the serial path.
- `test_assertion_collection_and_worker_failures_propagate` includes an empty module (tests lines239-249), but does not force unavailable capacity. Its empty-case assurance therefore depends on the installed engine.
- Measured coverage alone is insufficient to close this gap: collection-time imports can execute measured source without a single test method running. Existing coverage checks reject missing data, wrong branch mode, empty file metadata, failed export, unsuccessful tests, and worker data loss; none establishes a positive test count.
- Add deterministic regression cases for empty serial Core and Trust collection, including forced degraded selection; require unsuccessful test status and unsuccessful measured coverage where applicable. This is a static finding awaiting the writer's controlled RED execution.

## Regression assertions independent of scheduling

- For quota selection, use fixed affinity and fixture quota contents: affinity22/quota2 selects2; a positive fraction selects1; unlimited respects affinity and28 cap; invalid/unavailable data follows the chosen documented fallback. Cover configuration and environment opt-in; preserve explicit counts, no opt-in, and child zero.
- Patch the cleanup-capability seam, not global `os.name`, to emulate unsupported platforms without altering pathlib/subprocess behavior. Retain PR135's assertions for actual serial command, workers0, `unittest-degraded`, Core and Trust success, and measured coverage-only dependency checks.
- Prove exact-once execution with the exact expected marker-name set and exclusive `open('x')` writes already used by the fixture. Missing tests omit a marker; repeats fail on an existing marker.
- Do not require every requested worker to execute a tiny fixture method. Current Core PID-cardinality assertion at tests line355 depends on work stealing. Verify requested `-n`/distribution and disclosed engine separately from the exact executed-method set.
- Trust tests should assert all six exact marker names, one PID per test file, and absence of Core markers. Treat the global PID-count equality at tests lines97-98 as engine/scheduling-sensitive; preserving each file on one worker is the semantic requirement.
- Exercise ordinary assertion failure, import/collection failure, empty discovery, and abrupt exit under a forced serial fallback. Assert failure propagates without launching a second test attempt.
- Under measured fallback, assert fresh run-owned coverage, matching branch mode/nonempty files, unchanged parent/prior coverage bytes, and failure for missing/corrupt/below-threshold data. Worker-data-loss assertions remain explicitly xdist-only.
- Keep collection protections unchanged: `test*.py` filename pattern, nested tests, sanitized `PYTEST_*`/coverage environment, and separate Trust imports. Run the same exact-method fixture through selected engines to establish parity.

## Bounded recommendation

Carry retained PR135 product/tests with source attribution; add auto-quota selection and deterministic fixture tests through the single selected writer. Treat the non-vacuous serial result requirement as necessary evidence semantics for expanded fallback. Preserve cleanup ownership and existing coverage validation; introduce no provider, dependency, image, external policy, or service change.
