# Release plan — Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

## Deployment

Integrate as additive default-off source in the v1.5 candidate; no live activation.

## Feature flags / staged rollout

Native stays default. Exact live profiles require pinned packages/licenses and real
consumer qualification.

## Metrics and alerts

Selection/read/delivery digests, compatibility status, unknown cost and blockers.

## Go/no-go criteria

Deterministic checks and independent reviews pass; no AC114/live claim.
