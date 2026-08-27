# Bounded unresolved-frontier repair

Approved by the user on 2026-08-27 after the final pivot re-review exposed one new Important defect.

## Root cause

Dependency-work exhaustion is represented only as a boolean. The remaining worklist is discarded, so `_queue_adapter_names()` guesses relevance from module-name tokens rather than resolving reachable local-import candidates. This can hide a real queue export from a neutral module or falsely promote a proven non-queue export from a queue-adjacent module.

## Repair contract

- Preserve the exact bounded unresolved dependency frontier when the worklist exhausts.
- Inspect only local imports whose aliases remain reachable through that frontier, independent of module-name tokens.
- A resolved queue export or unresolved relevant local export yields the existing structured `unsupported` result, scoped evidence, overall failure, `new_queue`, and monotonic risk.
- A resolved non-queue export remains true N/A even when its module name contains queue-adjacent tokens.
- An exhausted graph unrelated to a changed callable/decorator remains true N/A.
- Do not change the public budget, add a dependency, or modify `trust-ci/**` or `.github/workflows/**`.

## TDD acceptance

RED/GREEN exact base/head regressions cover a real queue export from neutral `project.runtime`, a proven non-queue export from queue-adjacent `project.jobs`, and an unrelated exhausted graph. Focused queue/fitness tests, the full suite, exact architecture fitness, PR verification, and all five route reviews must pass on one immutable final head before receipts are recorded.
