# Architecture — cancellation-aware verification reports

`verify()` owns the durable report and fingerprint-bound receipt, so cancellation from a nested test check must be converted at this orchestration boundary before it can bypass finalization. Catch recognized cancellation semantics only: the Python runner's documented `SystemExit(143)` and `KeyboardInterrupt` (with signal details when available). Preserve already collected checks, stop scheduling later checks, add an explicit cancelled outcome/check, write the report and a failed verification receipt, then return cancellation so the CLI exits nonzero.

Keep the closed receipt status set (`pass|fail`) unchanged. A cancellation report/JSON result carries `outcome: cancelled`; the corresponding receipt is `fail` with cancellation details. Since receipt writing replaces the same route/kind record, an old green receipt for the unchanged fingerprint cannot survive as current evidence. Do not catch arbitrary `BaseException` as cancellation or turn programming errors into a green/ordinary failure.

SIGKILL and host power loss cannot be caught and are outside the guarantee. Do not change the runner's process-group cleanup. If report/receipt persistence itself fails, surface that failure and return nonzero; never claim the cancellation was durably recorded.
