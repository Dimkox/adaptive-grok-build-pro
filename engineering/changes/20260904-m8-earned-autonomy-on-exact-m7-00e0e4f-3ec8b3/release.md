# Release plan — M8 earned autonomy on exact M7 00e0e4f

## Deployment

No deployment is authorized. This phase creates a repository-local M8 source checkpoint only.

## Feature flags / staged rollout

There is no runtime wiring or feature flag. Recommendations require separate activation and cannot perform external actions; M7 acceptance/currentness remain unavailable. A real cohort and activation mechanism require separate design, evidence, and authorization.

## Metrics and alerts

Pure outputs expose accepted/audited counts, minimum quality, safety totals, maximum cost, p95 latency, demotion totals, expiry, halt state, and deterministic recommendation reason. No metric is emitted externally.

## Go/no-go criteria

This source checkpoint requires the focused M8 tests, actual-M7 bridge/schema parity, predecessor preservation, architecture parity, clean Git state, and status `verifying`. It is not activation-, release-, or production-ready.
