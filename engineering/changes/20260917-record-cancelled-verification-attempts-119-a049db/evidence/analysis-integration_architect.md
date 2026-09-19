# Integration analysis — cancelled verification attempts (#119)

Inspected the route-base implementation at `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`; no product files were changed.

## Persistence and receipt trace

- `scripts/grok_verify.py` calls `verify()` synchronously and emits its text/JSON output only after `verify()` returns. It has no cancellation exception envelope and no separate attempt-report writer. An escaping `SystemExit` or `KeyboardInterrupt` therefore produces no final CLI report.
- In `.grok-stack/adaptive_grok/verification.py`, `verify()` gathers checks (including `_python()`) before constructing its report and conditionally calling `write_receipt()`. An exception during dispatch skips both normal report construction and receipt recording.
- Verification does not invalidate an existing verification receipt at attempt start. `write_receipt()` only replaces it after a completed run. The reproducer in `analysis-repo_explorer.md` shows that SIGTERM exits 143 with no output/receipt; on an unchanged tree, a previously recorded `pass` remains fingerprint-valid. This is a stale-green failure mode.
- `validate_evidence()` in `.grok-stack/adaptive_grok/receipts.py` enforces a closed receipt status set of `pass|fail`, and treats anything other than `pass` as missing evidence. Introducing `cancelled` as a receipt status would require coordinated changes to receipt validation, consumers, CLI/review contracts, and fixtures. It is unnecessary: preserve the receipt schema and record cancellation as `status: fail` with explicit cancellation metadata in `details`.
- The test runner already owns its child process group and stops it on controller interruption (`python_test_runner.execute()` uses `start_new_session` on POSIX and `_stop()` on `BaseException`). The outer verification layer should preserve that unwind/exit behavior while recording the attempt; it must not swallow cancellation and report success.

## Safe integration behavior

Invalidate the current route's prior verification receipt before starting checks, so any abrupt exit cannot leave a trusted green result. On a recognized cancellation only, persist a terminal attempt report with an explicit `outcome: cancelled`, interrupted check (when known), and signal/exception metadata; write a schema-compatible verification receipt with `status: fail` and those details. Return/emit a nonzero outcome (SIGTERM's conventional 143 may be preserved; other cancellations should also be nonzero). Avoid converting unrelated `SystemExit` values or arbitrary `BaseException` into ordinary verification findings. Persistence errors must not be mistaken for a successful cancellation report.

The attempt report can be the receipt's `details` object if the CLI exposes/prints it on cancellation; if a separate durable report file is required, keep it under ignored machine-local `.grok-stack/runtime/` and bind it to route ID and the attempt/tree fingerprint. Do not write cancellation artifacts into tracked product files. Receipt invalidation is the security-critical stale-pass guarantee; the explicit report is the operator-facing diagnostic.

## Bounded test strategy

1. In a temporary fixture with a valid active route and a previously written `pass` receipt, patch the slow check boundary (`_python` or the relevant dispatch function) to raise `SystemExit(143)`; separately test `KeyboardInterrupt`. Assert the attempt returns/exits nonzero, records explicit cancellation metadata, and `validate_evidence()` no longer accepts the old pass. This exercises persistence and stale-receipt semantics without sleeping or launching the full suite.
2. Exercise the CLI envelope with a mocked `verify()` cancellation and capture stdout/JSON; assert a terminal cancellation report is emitted and the process code is nonzero. Keep a narrow integration check for the real runner using a short-lived controlled child and a bounded wait, asserting the owned process group is gone and the signal handler is restored. Reuse the cleanup pattern in `tests/test_python_test_runner.py`; in `finally`, terminate/kill and reap the controller and any recorded child, so a failed assertion cannot leak a 60-second process.
3. Assert normal completed `pass` and `fail` receipts remain accepted under the unchanged `pass|fail` schema, and a cancelled failure receipt remains rejected as passing evidence. Also check `--no-record` semantics explicitly: it must not leave an old pass valid after a cancelled attempt, or the API must document and enforce a different invalidation rule.

No long-running process was started for this analysis.
