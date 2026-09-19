# Architect analysis — issue #119 cancelled verification attempts

## Scope and observed behavior

Read-only review of `verify()` in `.grok-stack/adaptive_grok/verification.py`, the CLI `scripts/grok_verify.py`, the capability-selected runner, and receipt validation/writing. The runner's `_cancellation()` installs a temporary SIGTERM handler, lets the owned test process group stop, then raises `SystemExit(143)`. SIGINT normally arrives as `KeyboardInterrupt`. `verify()` currently has no outer interruption envelope; it only constructs and records its report after the sequential check dispatch returns. Thus interruption during a check bypasses report construction and receipt writing. Existing receipt validation accepts only `pass`/`fail`, and only `pass` satisfies required evidence.

## Recommended result semantics

Keep *execution outcome* distinct from *quality result*. The invocation/report should represent `cancelled` explicitly, identify the interrupted check and interruption class/signal, and preserve results already obtained; checks not reached should be marked skipped/not-run. Cancellation must never be represented as a successful verification. The CLI should retain a nonzero cancellation exit (normally 130 for SIGINT and 143 for the runner's SIGTERM path) after durable recording.

For compatibility and fail-closed behavior, the fingerprint-bound verification receipt can remain `status: fail` (the receipt envelope and `validate_evidence()` deliberately recognize only `pass` and `fail`), while its details/report carry an explicit cancellation outcome. This makes the evidence unusable as a pass and avoids widening the receipt status protocol, hooks, workflow validators, and trust-facing consumers just to add a third receipt status. If a future contract needs `cancelled` as a receipt status, it must update every closed-set validator and consumer together; it must still never satisfy required evidence.

## Stale-pass safety and durability

On a recognized cancellation, the current route's verification receipt must be replaced with a failure receipt, fingerprint-bound to the observed tree, rather than leaving an earlier same-route green receipt in place. The existing same-route receipt path supports that invalidation. A report-only file without invalidating the receipt is insufficient: a still-current old pass would continue satisfying the gate. Recording should use the normal safe receipt writer and preserve its expected-fingerprint check. If the tree changed during the interrupted run, report source stability as failed and bind only to a freshly observed fingerprint; do not claim that the checks cover that tree. If the receipt cannot be safely written, propagate/report that persistence failure and ensure no caller treats the run as pass; the design must not silently fall back to the old green receipt.

## Exception boundary

An outer orchestration boundary is appropriate so cancellation during any dispatched check (not only the Python runner) can be recorded with already collected results. Catching `BaseException` indiscriminately and returning success or swallowing it is unsafe. Classify `KeyboardInterrupt` and the runner's documented cancellation `SystemExit` code (143; optionally the conventional 130 only where an explicit cancellation path uses it) as cancellation. Preserve their nonzero process outcome after recording. Other `SystemExit` values are not automatically cancellation: record a failed/interrupted execution with safe exception metadata or re-raise after recording, so unrelated deliberate exits and programming failures do not get mislabeled. Avoid persisting traceback/local-variable content; exception type, bounded message, active check name and signal/code are enough.

SIGTERM can terminate a process without Python-level cleanup unless some active code has installed a handler. The currently observed runner does install one only while it owns the Python child. Therefore guarantees should be scoped to interruptions delivered through that handler and Python `KeyboardInterrupt` (plus any explicit CLI-level handler added by implementation); do not claim that arbitrary SIGKILL or host termination can produce a report. The implementation should preserve child-process cleanup and not add a handler that interferes with runner cleanup or previous signal-handler restoration.

## Architectural constraints

- Keep receipt status compatibility (`pass`/`fail`) and make cancellation metadata explicit in report details.
- Ensure the exception path uses the same route, tree-fingerprint, architecture/governance bindings and receipt writer as the normal path; no manually forged/unbound receipt.
- Never allow cancellation to produce `status: pass`, even if earlier checks all passed.
- If report persistence fails, the caller must remain nonzero and the limitation must be visible; no stale receipt may be represented as refreshed evidence.
- Tests should cover SIGTERM→`SystemExit(143)`, `KeyboardInterrupt`, unrelated `SystemExit` codes, cancellation at a non-final check, prior same-route pass replacement, changed-tree handling, and receipt-write failure. Verify both the CLI outcome and `validate_evidence()` fail-closed result.

No product files were edited.
