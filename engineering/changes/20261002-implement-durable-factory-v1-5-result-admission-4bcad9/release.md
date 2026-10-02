# Release plan — Implement durable Factory v1.5 result admission persistence

## Deployment

Apply additive migration 024 before exposing POST/GET through the existing runtime and publish the v2 OpenAPI snapshot alongside byte-stable v1. The migrator verifies contiguous schema 1..24 and least-privilege roles.

## Feature flags / staged rollout

No dispatcher exists and the outbox remains empty, so persistence may be rolled out independently of model handoff.

## Metrics and alerts

Observe admission created/replay/conflict/unavailable outcomes and assert `next_model_request_outbox_v1` cardinality remains zero.

## Go/no-go criteria

Full verifier, actual restart probe, code/test/data reviews and exact-head Trust CI must pass.
