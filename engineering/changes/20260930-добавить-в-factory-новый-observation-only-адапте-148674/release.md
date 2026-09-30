# Release plan — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

## Deployment

Source-only. No deployment or provider call in this change.

## Feature flags / staged rollout

`enabled=False` is the constructor default. Activation requires a later explicit operation with independently supplied credentials.

## Metrics and alerts

- Count `selected`, `exhausted`, `stopped` and `needs_human` terminal evidence by registry digest.
- Alert on any budget overrun, unknown usage, stale claim or authority rejection; never include opaque identifiers or provider text in labels.
- Track cooldown saturation and duplicate-claim rejection. These are observations, not provider-health or zero-cost claims.

## Go/no-go criteria

Focused and full route verification plus all selected reviews; live status remains `NOT_RUN`.
Migration 027 must be integrated strictly after migration 026 and exercised by the integrated PostgreSQL suite.
