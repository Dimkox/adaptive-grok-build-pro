# Release plan — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

## Deployment

None. This is an isolated stacked source-only Trust-CI bugfix; no policy, holdout, runner image, service, migration, external write, push, merge, or deployment is authorized.

## Feature flags / staged rollout

None. The existing bounded workspace cleanup path retains its interface and isolation controls.

## Metrics and alerts

Use existing redacted workspace/runner failure outcomes. Do not add PID, command, environment, SHA, or process-list telemetry.

## Go/no-go criteria

Go only when zombie-only cleanup preserves original stdout/stderr/timeout failures; live or uncertain post-KILL state fails closed; focused tests, diff check, spec validation, verifier, and independent reviews bind to the final tree. The deployed App-owned exact-SHA check remains the merge gate.
