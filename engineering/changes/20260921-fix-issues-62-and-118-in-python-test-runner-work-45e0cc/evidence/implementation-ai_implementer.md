# Runner capacity/platform implementation evidence

Route: `45e0cc3b5da0`; sole source/test writer: `ai_implementer`.
Base: `839d3aa26bc90417424d814ee48d8b5cd3be367e`.
Retained PR135 source: `7a7851af5d11e8ce5c3af23ab46214ae7ae4cdc8`.

## Current-source RED

Before source changes, four deterministic selectors ran under the coordinator's
exclusive CPU allocation:

```text
python3 -m unittest -v
  tests.test_python_test_runner.PythonTestCapacityTests.test_auto_applies_nested_v2_quota_and_tighter_visible_ancestors
  tests.test_python_test_runner.PythonTestRunnerTests.test_non_posix_cleanup_capability_degrades_core_and_trust_before_launch
  tests.test_python_test_runner.PythonTestRunnerTests.test_empty_serial_core_and_trust_collection_cannot_pass
  tests.test_python_test_runner.PythonTestRunnerTests.test_empty_measured_serial_collection_cannot_qualify_import_coverage
```

The shell set `PYTHONDONTWRITEBYTECODE=1`; `/usr/bin/time` recorded wall time and
exit status. [Lossless raw output and timing](red-initial.json) preserve the
original `.log`/`.time` bytes as base64 with their SHA-256 digests; the raw files
also remain unchanged locally. This avoids losing RED evidence to repository
log ignores or whitespace gates.
Result: 4 tests, 1.563 seconds of unittest time, 1.84 seconds wall time, exit 1,
8 assertion failures and no errors. Linux selection returned 22 for finite
quotas requiring 2, 3, or 1; the known-unlimited case also showed no metadata
reads. Unsupported cleanup selected `(2, 'pytest-xdist')` instead of
`(0, 'unittest-degraded')`. These are current behavior failures, not missing
helper/mock/import failures.

Baseline SHA-256 values:

- `python_test_runner.py`: `2a490bbf80f07b96e5b0c7b7663362ae17a7cfce08d1f8ee95707f503919e63b`
- `tests/test_python_test_runner.py`: `5063142378b5636e1259b0e9778302076eb1d24eafef9d548d62a6208da220f2`

## Bounded ruling on empty serial discovery

The explicit and degraded Core/Trust empty-run regressions passed, including
measured collection that imports covered source but executes no tests. The host
uses `/usr/bin/python3`, whose symlink resolves to `python3.12`; that unittest
source rejects an empty run with exit 5. Separately installed Python 3.14 source
has the same rule, but was not executed. This contradicts
the analysis's unqualified claim that unittest empty discovery necessarily
succeeds; it does not establish older-Python behavior. The coordinator approved
preserving serial commands/accounting and retaining diagnostic regression
assertions, without an older-interpreter probe or an unproven production fix.
The added assertions require the child to report `Ran 0 tests`, so unrelated
startup/import failures cannot satisfy the empty-run checks. No claim is made
about every historically supported Python version.

## Source and regression scope

The private `_cpu_capacity.py` reader bounds proc inputs to 1 MiB, controls to
4096 bytes, metadata to 4096 lines, paths to 4096 characters/256 components,
matching mounts to 64, and quota reads to 1024. It resolves exact v1 `cpu`
membership (including hybrid/combined-controller hosts) or v2 membership against
mount roots and decoded mountpoints, checks every visible applicable ancestor,
and never guesses hidden namespace prefixes. Valid finite quotas use
`max(1, quota // period)`; absent v2 controls do not stop parent inspection.
Unknown evidence returns one worker. Affinity/count, explicit requests,
default-off, child suppression and non-Linux boundaries remain in the runner.

The platform capability predicate/selection change is the exact retained PR135
product hunk. Its three regressions were carried forward with provenance and
stronger exact-marker assertions. The measured fallback still checks coverage
pins only; supported xdist retains strict pins. Additional regression fixtures
cover finite/unlimited/absent/invalid quotas, parent limits, multiple mounts,
mapping escapes, prefix collisions, hybrid controllers, traversal rejection,
bounded metadata, no-read compatibility paths, and affinity failure.

Tiny suites no longer require every requested worker to receive a test, because
that assertion depends on xdist scheduling. Exact exclusive marker names,
per-file Trust process grouping, requested command arguments, actual engine
disclosure and no-retry assertions preserve the intended collection contract.
Existing cleanup and current-run coverage failure checks remain intact.

Source implementation followed meaningful RED. Current focused GREEN and
scoped Ruff passed on the unchanged source/test hashes below. Complete route
verification and independent reviews remain the coordinator's next gates;
neither historical PR135 receipts nor this report replaces them.

Prepared source/test SHA-256 values before focused GREEN:

- `_cpu_capacity.py`: `30a5997a93cffa1e54496806402df4e8989467699ea2a58c11184086af42f453`
- `python_test_runner.py`: `5efcc71bc50d447e60ba2626886cb8895ec2808882139cecaef375faf53fbcc0`
- `tests/test_python_test_runner.py`: `c8154aaeef74fcac8985dd476f2d16197ed4a6a8366a39abef5a55fa4f2890f5`

## Allocated focused GREEN and source freeze

Both commands ran only after the coordinator granted the next exclusive CPU
slot, against HEAD `839d3aa26bc90417424d814ee48d8b5cd3be367e` and the exact
three hashes above:

1. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v tests.test_python_test_runner`
   passed all 38 tests with exit 0: 20.148 seconds unittest time and
   20.441919 seconds wall time. [Complete output](green-runner-attempt-1.json).
2. `ruff check .grok-stack/adaptive_grok/_cpu_capacity.py .grok-stack/adaptive_grok/python_test_runner.py tests/test_python_test_runner.py`
   passed with exit 0 in 0.023660 seconds.
   [Complete output](ruff-attempt-1.json).

Both were first attempts; no repair, selector retry, skipped test, full-suite
command, compile or container run was needed. Each record includes its exact
command, HEAD, source hashes, actual exit/duration and separate lossless base64
stdout/stderr. Subprocess controllers completed and were reaped before the CPU
lane was released. Source/test files are frozen at these hashes; only evidence
was written after release.
