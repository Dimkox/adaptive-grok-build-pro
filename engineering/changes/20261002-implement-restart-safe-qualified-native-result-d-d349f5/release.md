# Release plan — Implement restart-safe qualified native result dispatch

## Deployment

Apply migration 025 with the owner role, then provision a distinct dispatcher login. Do not enable
the process until a separately reviewed receiver and qualification/enqueue authority exist.

## Feature flags / staged rollout

FACTORY_RESULT_DISPATCH_ENABLED remains false. This slice has no supported live rollout stage.

## Metrics and alerts

Track phase counts, reason codes, send/observation exhaustion and automatic outbox count (must be 0).

## Go/no-go criteria

Local full verifier, real PostgreSQL restart/contention suite and code/test/data reviews pass.
All qualification channels remain unavailable and no automatic row is present.
