# Rollback plan — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

## Trigger conditions

Contract regression, evidence leak, unsafe retry or authority-binding mismatch.

## Application rollback

Keep adapter disabled (the default) and revert the source commit; no persistent runtime state requires migration.

## Data recovery / forward-fix

## Verification after rollback

Run `adaptive-model-rotator status` and require `enabled:false`; verify no new operation
rows appear. Migration 027 data may remain inert for audit/replay safety and must not be
dropped during ordinary rollback. Re-run the pre-existing Factory unit and migration suite.
