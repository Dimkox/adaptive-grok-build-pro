# Release plan — M7 bounded shadow handoff on exact M6 c6d48ff

## Deployment

No deployment is authorized. This phase creates a repository-local M7 source checkpoint only.

## Feature flags / staged rollout

There is no runtime wiring or feature flag. A pure bundle is contractually `blocked_pending_durable_lookup`, and the proposal has no external capability. Later durable lookup, real-outcome collection, or operator workflow requires a separately designed and authorized phase.

## Metrics and alerts

The pure evaluator exposes deterministic counts, integer-millionth rates, repair percentiles, review-time reduction, containment, sorted failure codes, and a recommendation. No telemetry is emitted.

## Go/no-go criteria

This bounded source checkpoint requires the exact ten-path import, 30 focused shadow tests, affected architecture structure/parity, a clean tree, and state `verifying`. It is not release-, PR-, merge-, or production-ready without the deferred exact-head verifier, independent reviews, receipts, and external trust gates.
