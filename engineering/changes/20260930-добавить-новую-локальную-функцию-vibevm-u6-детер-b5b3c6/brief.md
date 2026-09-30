# Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-добавить-новую-локальную-функцию-vibevm-u6-детер-b5b3c6`
Created: 2026-09-30T19:41:01+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Добавить новую локальную функцию VibeVM U6: детерминированный package graph resolver, lock cache offline replay, bounded unpack projection, boot checks, atomic generations, scoped caches, export fallback и тесты

## Outcome

An opt-in local package backend can reproduce an admitted context generation offline, publish it atomically, export it to the native format, and fail closed without affecting the native core.

## Scope

### In scope

- AC83–AC93 package resolution, immutable scoped cache, bounded projection, boot reconciliation, generation publication/recovery, rollback and native export.

### Out of scope

- Live VibeVM installation/qualification, AC94 CLI proof, FPF, registry/network access, activation and production deployment.

## Constraints

- Backward compatibility: additive Python module and schema; no existing contract changes.
- Data/privacy: tenant and repository are path-safe explicit cache namespaces; no credentials are persisted.
- Performance: bounded file count, expanded bytes and path depth; deterministic local traversal only.
- Operational: default-off; callers explicitly admit bytes and explicitly publish/rollback generations.
