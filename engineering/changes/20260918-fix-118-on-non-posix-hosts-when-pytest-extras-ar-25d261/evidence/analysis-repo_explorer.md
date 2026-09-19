# Repository analysis — issue #118

## Reproduction

In `/tmp/adaptive-fix-windows-engine`, I exercised `adaptive_grok.verification._python` against a temporary opt-in project with `.grok-test-runner.json` set to `{"schema_version": 1, "workers": 2}` and one unittest. The harness emulated Windows by giving `adaptive_grok.python_test_runner` an `os` proxy with `name="nt"`, forced `parallel_engine_ready(...)` to `True` (the pytest/xdist extras are importable), and supplied the runner's pinned package versions. Result: `python-unittest fail parallel process cleanup requires POSIX; use GROK_TEST_WORKERS=0`. The unrelated ruff check also failed in this harness because its temporary project has no ruff configuration; that does not affect the reproduced runner failure.

## Call path and root cause

1. [`verification.py`](../../../../.grok-stack/adaptive_grok/verification.py#L941) sends an opted-in unittest project through `selected_workers()` and `run_core_tests()`; a direct pytest project takes a different branch at lines 933–940.
2. [`selected_workers()`](../../../../.grok-stack/adaptive_grok/python_test_runner.py#L72) returns `0` for `workers="auto"` on non-POSIX, but returns a configured explicit integer unchanged at line 74.
3. [`select_engine()`](../../../../.grok-stack/adaptive_grok/python_test_runner.py#L201) checks whether pytest, xdist, and (for measured runs) pytest-cov can be imported. If available, it preserves the positive worker count without considering host process-cleanup capability.
4. [`run_core_tests()`](../../../../.grok-stack/adaptive_grok/python_test_runner.py#L224) selects the pytest branch for positive workers. [`_pytest_command()`](../../../../.grok-stack/adaptive_grok/python_test_runner.py#L216) then raises `RunnerError` on non-POSIX, explaining the failing `python-unittest` result (and `coverage` failure in `pr`/`release` mode).

The gap is specifically the interaction of an explicit positive integer, an importable parallel engine, and a non-POSIX host. Existing coverage tests the `auto` selection and missing-engine degradation (`tests/test_python_test_runner.py:129–145`), but not this combination. `run_trust_tests()` shares the same positive-workers-to-`_pytest_command()` path and is affected when called with that combination too.

## Evidence boundary

This is a Windows capability emulation on the current host, not a native Windows run. It establishes the control-flow defect without claiming native Windows process behavior. No product code was changed.
