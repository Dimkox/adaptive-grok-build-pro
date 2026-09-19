# Architecture analysis — issue #118

## Evidence

- `grok-stack/adaptive_grok/python_test_runner.py` (repository path: `.grok-stack/adaptive_grok/python_test_runner.py`) centralizes backend selection in `select_engine(workers, measured)`. `run_core_tests` and `run_trust_tests` both select the backend before running commands.
- `parallel_engine_ready` currently checks only importability of `pytest`, `xdist`, and, for measured runs, `pytest_cov`.
- `_pytest_command` rejects any `os.name != 'posix'` with `RunnerError('parallel process cleanup requires POSIX; use GROK_TEST_WORKERS=0')`. Thus, on Windows with the optional modules importable and a positive explicit worker count, selection claims `pytest-xdist`, then command construction fails instead of selecting the supported serial unittest backend.
- Serial Core PR/release runs still require the pinned `coverage` package and `.coveragerc`; serial Trust CI runs do not require pytest/xdist. Existing reporting uses engine names `unittest`, `unittest-degraded`, and `pytest-xdist`; verification details carry the selected engine and requested/actual worker counts.

## Minimal design

Keep the decision in the shared pre-execution selector, so Core and Trust CI cannot diverge. Treat POSIX process-group cleanup as a prerequisite for the xdist engine, alongside module availability. When a positive worker request cannot be honored because the host lacks that capability, select `workers=0` and the existing disclosed `unittest-degraded` engine; retain strict dependency-version checks whenever the selected engine is xdist. Preserve coverage requirements for measured serial Core runs. Do not catch `_pytest_command` errors and silently retry after execution setup: that would mix capability selection with error recovery and risks disguising unrelated command/configuration defects.

To make this explicit without mutating the global `os.name` module object in tests, expose or factor a narrow platform-capability predicate used by `select_engine`; a Windows-emulated test can patch that predicate while leaving `pathlib`, subprocess execution, and the host interpreter untouched. Exercise the runner end-to-end with requested workers > 0 and installed/importable parallel dependencies, then assert serial execution, successful result, and degraded-engine disclosure. Also retain a selector-level assertion that a POSIX-capable host plus importable dependencies still selects xdist. Existing tests already cover missing modules and strict pin failures.

## Compatibility and risks

- No config/schema or CLI contract changes are needed. The requested worker count remains the request; actual workers become 0 only when the execution capability is unavailable, and the existing `unittest-degraded` report distinguishes this from an explicit serial setting.
- Explicit `workers=0` continues to report `unittest`; `workers='auto'` currently resolves to 0 off POSIX, so it remains ordinary sequential behavior. No downgrade should be added for POSIX environments with importable but wrong/missing pinned versions: those continue to fail before test execution as they do today.
- Serial execution can take longer than requested parallel execution, but is already the supported fallback and remains bounded by the existing test timeout. A regression that ignores the platform restriction would fail later in `_pytest_command`; a broad exception fallback could incorrectly mask malformed configuration or executable errors, hence capability-only selection is preferable.
- This analysis establishes the deterministic source-level cause; it does not claim a native Windows run. The route-requested Windows-emulated regression test is the appropriate local proof.
