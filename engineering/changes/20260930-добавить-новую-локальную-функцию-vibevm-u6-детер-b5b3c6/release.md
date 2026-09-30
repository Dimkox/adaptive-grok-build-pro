# Release plan — Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

## Deployment

Additive source only; remains disabled unless a caller explicitly selects the local adapter.

## Feature flags / staged rollout

No default activation. Live VibeVM qualification and AC94 remain separate external work.

## Metrics and alerts

Record generation identity/status and stable rejection code at the caller boundary.

## Go/no-go criteria

Focused tests, full route verification and independent code/test review pass on the exact tree. No claim of live adapter qualification.
