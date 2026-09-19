# Test plan — Fix #118: on non-POSIX hosts when pytest extras are installed and workers is an explicit integer, capability-selected grok_verify must degrade to sequential test execution instead of failing; add a Windows-emulated regression test.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Emulated non-POSIX + explicit workers + parallel dependencies available degrades to unittest for Core in measured PR/release mode, preserves coverage, and avoids xdist pin checks. | Focused measured runner test; asserts coverage command/result, engine, workers and coverage-only version lookup. |
| P0 | Same configuration takes sequential Trust CI path without `_pytest_command` refusal. | Focused runner/CLI test; asserts command and disclosed engine. |
| P1 | POSIX + explicit workers + dependencies available still selects xdist and enforces exact pins. | Existing pin/selection tests plus focused regression assertions. |
| P1 | `auto` and zero-worker semantics remain unchanged. | Existing worker-selection tests. |

## Automated checks

- Unit: `python3 -m unittest tests.test_python_test_runner`
- Integration: targeted Core and Trust runner tests with an isolated platform-capability seam.
- Contract: no external contract changed.
- E2E: full `python3 scripts/grok_verify.py --mode pr`.
- Static analysis: route-selected Ruff/Bandit and diff checks.

## Manual checks

- Windows itself is unavailable in this environment; deterministic platform-capability emulation covers branch selection while preserving host pathlib behavior.
