# Release plan — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

## Deployment

Additive source only; integrate through the parent v1.5 PR. Live provider qualification and activation are separate operations.

## Feature flags / staged rollout

No runtime consumer is enabled. Deterministic fixture qualification is the first stage.

## Metrics and alerts

Report completeness, critical failures, per-mode quality, attempts, latency and known/unknown cost.

## Go/no-go criteria

Focused tests and full PR verification pass; independent code/test reviews pass; no authority or live-status claim is introduced.
