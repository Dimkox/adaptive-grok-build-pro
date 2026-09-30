# Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-добавить-в-factory-новый-observation-only-адапте-148674`
Created: 2026-09-30T22:02:46+00:00
Risk: high
Complexity: high-risk
Domains: api

## Problem

Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

## Outcome

Factory can deterministically observe bounded free-model fallback without mutating Qwen settings or granting the adapter execution authority.

## Scope

### In scope

- versioned Qwen/OpenRouter registry and deterministic selection;
- pre-response-only retry, cooldown, fatal limits and usage evidence;
- full Factory authority binding and default-off operation.

### Out of scope

- live provider qualification, credential provisioning and activation;
- proxy/service installation or edits to user settings/home;
- release publication.

## Constraints

- Backward compatibility:
- Data/privacy:
- Performance:
- Operational:
