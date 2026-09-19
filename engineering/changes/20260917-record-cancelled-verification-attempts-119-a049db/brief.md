# Record cancelled verification attempts (#119)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260917-record-cancelled-verification-attempts-119-a049db`
Risk: medium
Complexity: standard
Domains: api

## Problem

Cancellation during the capability-selected Python test engine escapes `verify()` as `SystemExit(143)`. The CLI writes no report or receipt, and an earlier passing receipt for the unchanged tree can remain valid.

## Outcome

Recognized cancellation produces an explicit cancelled report/result, persists a failing verification receipt so a previous pass cannot survive, and exits nonzero with cancellation semantics intact.

## Scope

### In scope

- Catch only recognized cancellation paths at the verification orchestration boundary.
- Persist and print an explicit cancelled outcome with signal/reason evidence.
- Overwrite/invalidate a same-route passing verification receipt with a `fail` receipt carrying cancellation details.
- Add tests for report, exit, receipt replacement, and normal failure/pass compatibility.

### Out of scope

- Treating SIGKILL or host power loss as catchable.
- Changing child process-group cleanup already handled by the test runner.
- Adding a new receipt enum value or changing Stop-hook evidence semantics.

## Constraints

- Receipt schema remains `pass|fail`; cancellation is represented in the report/details while the receipt is `fail`.
- A cancelled command remains nonzero and distinguishable from an ordinary test failure.
- Persistence failure must not be misreported as a successful or completed verification.
