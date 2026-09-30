# Release plan — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

## Deployment

Source-only. No deployment or provider call in this change.

## Feature flags / staged rollout

`enabled=False` is the constructor default. Activation requires a later explicit operation with independently supplied credentials.

## Metrics and alerts

## Go/no-go criteria

Focused and full route verification plus all selected reviews; live status remains `NOT_RUN`.
