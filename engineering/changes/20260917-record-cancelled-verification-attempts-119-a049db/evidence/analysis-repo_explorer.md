# Repository exploration — issue #119

Base examined: `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217` (route base).

## Reproduction

Reproduced the issue's cancellation path in an isolated temporary root with `.grok-test-runner.json` selecting the sequential engine and a unittest that sleeps. A wrapper process called `adaptive_grok.verification._python(root, 'pr')`; after one second it received SIGTERM. The wrapper exited `143`, emitted empty stdout/stderr, and produced no receipt files. This isolates the stated runner path; the same escape prevents `verify()` from returning to the CLI.

## Trace and stale-evidence consequence

- `scripts/grok_verify.py` calls `verify(...)` directly, prints a report only after the call returns, and has no exception envelope or report-file write. Escaping `SystemExit(143)` therefore terminates before any report output.
- `verification.verify()` dispatches `_python(root, mode)` directly. `_python()` catches `RunnerError` from runner selection, but not `SystemExit`; the test runner's `_cancellation()` restores the SIGTERM handler then raises `SystemExit(143)` when `execute()` unwinds.
- The final report and receipt write are below all check dispatch (`verification.py`, `verify()` tail). A `BaseException` before that point skips both. There is no attempt-start receipt/report and no exception-finally persistence.
- `write_receipt()` replaces a receipt only after a completed report. Nothing invalidates an existing receipt at the beginning of verification. Thus an earlier `pass` receipt on the same unchanged tree remains byte-for-byte present and still validates against the current tree fingerprint after cancellation. If the tree changed, normal fingerprint validation rejects it, but same-tree cancellation leaves the stale-green case described by #119.
- Receipt validation currently accepts only `pass`/`fail`; review CLI likewise exposes those statuses. A third receipt status `cancelled` is not supported without coordinated contract/consumer updates.

## Minimal contract recommendation

Persist an explicit terminal attempt report from a narrow `BaseException` boundary around verification dispatch. For cancellation, return/serialize a distinct report state (`cancelled`) with the interruption kind/signal and the interrupted check name, and exit nonzero. Ensure a prior pass cannot survive: either atomically replace the verification receipt with a non-passing cancelled receipt or invalidate the existing verification receipt before dispatch and write the terminal cancelled record. The simplest backward-compatible receipt contract is to keep receipt `status: fail` (so all current validators fail closed) and add explicit `details.outcome: cancelled` plus signal/check metadata; top-level report status may be `cancelled` only if all report consumers accept it. If choosing `status: cancelled` in the receipt, update the closed receipt status contract and every consumer together. Catching `BaseException` should be narrowly scoped to deliberate cancellation (`SystemExit` from SIGTERM / `KeyboardInterrupt`), not silently converting arbitrary `SystemExit` into a normal check failure. Preserve test child process-group cleanup and the runner's exit semantics.

No product files were edited for this analysis.
