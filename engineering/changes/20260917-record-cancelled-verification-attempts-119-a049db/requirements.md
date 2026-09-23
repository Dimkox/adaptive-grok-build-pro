# Requirements — cancelled verification evidence (#119)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Acceptance criteria

- [ ] SystemExit(143) from the test-runner cancellation path is reported as cancellation, not an unhandled termination.
- [ ] KeyboardInterrupt is reported as cancellation when caught at the verification boundary.
- [ ] The report is persisted and printed; receipt status stays `fail` with cancellation details.
- [ ] A prior pass receipt for the same route is replaced/invalidated; no stale green remains current.
- [ ] The CLI exits nonzero and exposes a machine-readable cancelled outcome.
- [ ] Ordinary pass, ordinary test failure, and unrelated programming exceptions preserve their semantics.

## Failure and edge cases

- Cancellation occurs after earlier checks completed: keep those results and mark the run cancelled; do not start later checks.
- Cancellation occurs during test runner process-group cleanup: preserve its existing cleanup behavior.
- Persistence fails while recording cancellation: surface the failure and remain nonzero; do not claim durable evidence.
- SIGKILL or host power loss: cannot be caught and is expressly outside the guarantee.

## Governance context

Receipts are local workflow evidence. The deployed Trust CI exact-SHA check and external signed approvals remain independent.

## Non-functional requirements

- Reliability: cancellation remains visible after process termination and invalidates a prior pass receipt.
- Compatibility: receipt status remains `pass|fail`.
- Observability: cancellation reason/signal is visible in report and JSON output.
