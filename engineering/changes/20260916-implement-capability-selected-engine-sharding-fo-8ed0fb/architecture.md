# Architecture — capability-selected runner

Components: `.grok-stack/adaptive_grok/python_test_runner.py` (ported: config `selected_workers`, closed-object parse, GROK_TEST_WORKERS override, child guard, bounded `execute` with process-group cleanup; new: `parallel_engine_ready`/`select_engine`, `versions['engine']`); `.grok-stack/adaptive_grok/verification.py` (`_python` delegates to `run_core_tests` only under opt-in config, reports the engine actually used via `core.workers`, legacy no-opt-in path unchanged except private temp COVERAGE_FILE isolation; `_command_check` gains `env=` passthrough, `tempfile` imported); `.grok-stack/config/python-test-requirements.txt` (declarative pins).

Data flow: config/env -> requested workers -> `select_engine` (capability probe via importlib.util.find_spec) -> xdist shard plan or single sequential command -> CheckResult details {backend, workers, versions incl. engine, coverage facts}.

Contracts: none (local evidence tooling; the mandatory external command shape is untouched). Trust boundary: runner output is local evidence only; merge authority remains the App-owned check. Nothing installs, nothing reaches network, nothing external is invoked.

Decisions: degrade pre-execution (never post-failure retry); keep the pin contract strict when the engine is present; make parallel-only assertions conditional instead of weakening coverage — degraded semantics are tested directly (single serial pass, label correctness) The degraded serial semantics are tested directly (single serial pass, label correctness); the xdist-only arms (distribution shape, worker data-loss combine) are mock-pinned here and executed by the App check on a pytest-bearing image; `find_spec` probes importability, so a declared-but-broken xdist install still surfaces as the strict pin failure by design.

Risks: label/claim drift between requested and used engine -> `core.workers`/versions recorded in details and asserted by tests; xdist-only scenarios (worker data loss) -> skipped solely when that engine is absent, and the skip is explicit.
