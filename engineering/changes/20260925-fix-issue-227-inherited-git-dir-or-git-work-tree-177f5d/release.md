# Release plan — Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

## Deployment

Local source repair only in this change. Push, PR update, merge and deployment
require separate exact delegation and current Trust CI evidence.

## Feature flags / staged rollout

No flag. Fail-closed selector denial is a security boundary and must not be
selectively bypassed.

## Metrics and alerts

Track policy denials by selector name only; never log selector values.

## Go/no-go criteria

All P0/P1 tests, `grok_verify --mode pr`, and code/test/security/release reviews
must pass on one exact tree. No external operation is part of local completion.
