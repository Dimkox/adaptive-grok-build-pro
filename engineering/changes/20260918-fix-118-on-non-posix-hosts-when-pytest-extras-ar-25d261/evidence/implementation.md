# Implementation evidence — issue #118

## Change

- Added `_parallel_process_cleanup_supported()` as a narrow platform capability seam.
- `select_engine()` now selects `unittest-degraded` for positive worker requests when either xdist dependencies are unavailable or safe POSIX process cleanup is unavailable.
- `_pytest_command()` and its POSIX refusal remain unchanged as a defensive invariant. POSIX engine selection and pin validation are unchanged.
- Added a Windows-capability-emulated test that exercises both Core and Trust CI sequential execution while parallel dependencies are reported available. A measured PR-mode Core case confirms unittest runs under coverage, coverage qualifies, actual workers/engine are reported correctly, and only the coverage pin is consulted. Added a POSIX-capability selector assertion; the existing wrong/missing pin test continues to cover strict validation.

## Verification

- Regression-first: the new Windows-emulated Core/Trust test failed before the implementation because selection returned `(2, 'pytest-xdist')` instead of `(0, 'unittest-degraded')`.
- `python3 -m unittest tests.test_python_test_runner`: PASS, 22 tests, 1 skipped (Linux-only process-group assertion).
- `python3 -m unittest tests.test_python_test_runner.PythonTestRunnerTests.test_non_posix_measured_core_degrades_with_coverage_without_xdist_pins`: PASS.
- Focused selection, platform fallback, pin, `auto`, and zero-worker tests: PASS, 5 tests.
- `python3 -m py_compile .grok-stack/adaptive_grok/python_test_runner.py tests/test_python_test_runner.py`: PASS.
- `git diff --check`: PASS.

## Limit

This is a deterministic Windows-capability emulation on POSIX, not a native Windows run. Full PR verification and independent reviews are not part of this implementation task.
