# Acceptance

1. Normal toolkit verification distributes each existing Core test once across bounded logical-CPU workers with explicit repository opt-in and configurable serial rollback.
2. Parallel and serial executions preserve the configured measured sources, branch mode and fail_under74; fresh per-run data prevents stale or nested coverage reuse.
3. Assertion, collection, worker, timeout, dependency and configuration failures remain visible failures with no silent successful retry.
4. Generic consumer behavior, existing report identities, other Python suites and exclusive PostgreSQL/restart lanes remain compatible.
5. Pinned development-only tooling ships with the managed stack; a measured full verification and independent code/test reviews precede exact-head external Trust CI.

6. Existing Trust CI test target uses separate cwd/imports and loadfile; all methods of each file stay together, serial0 retains the full suite, and unset disposable DB retains explicit skips. The combined target runs both suites sequentially and preserves either failure.
7. Runner image source pins match required tooling; document independent deployment prerequisite without modifying deployed configuration or claiming an image rollout.

## Delivery split after architecture verification

`FIT-TRUST-CI-SEPARATION` rejects a PR combining local implementation with `trust-ci/**` source mutations. Move the three runner package pins and the existing test_ops pin assertion into a separate bootstrap branch/PR; this acceleration branch has no Trust CI source changes. Its Make target still invokes the existing Trust test suite with loadfile. Companion image deployment remains independently operated, and actual signed scopes come from the external exact-head check.
