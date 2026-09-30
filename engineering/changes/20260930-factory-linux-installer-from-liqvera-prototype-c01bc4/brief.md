# Factory Linux installer from Liqvera prototype

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-factory-linux-installer-from-liqvera-prototype-c01bc4`
Created: 2026-09-30T19:08:10+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Реализовать Linux setup manager фабрики по прототипу Dimkox liqvera: строгая проверка архива и manifest, preflight до мутаций, atomic version switch, data-preserving removal и lifecycle проверки

## Outcome

A stdlib-only Linux setup manager verifies a packaged factory release before mutation, prepares immutable releases, atomically switches the active pointer only after health evidence, exposes bounded lifecycle commands, and preserves data by default on removal.

## Scope

### In scope

- Selective adaptation from `Dimkox/liqvera@e3df6833e8916d01f55028e63d4db1632a805a75` installer lifecycle.
- Archive/manifest verification, safe preflight, confined immutable releases, atomic pointer switch.
- `status`, bounded `logs`, idempotent `start`/`stop`, update/reversal with compatibility checks, data-preserving removal.
- Focused installer tests and explicit provenance.

### Out of scope

- Liqvera product services/configuration and its Compose/Caddy payload.
- Silent dependency installation, host hardening, firewall changes, secrets, production activation, push/tag/publication.
- Down migrations or a successful update claim without backup/migration evidence.

## Constraints

- Backward compatibility: existing `install_into.py` absent-target materialization remains unchanged.
- Data/privacy: state/logs expose no secrets; removal preserves config/data unless an exact confirmation token is supplied.
- Performance: archive, manifest, logs, and waits are bounded.
- Operational: deployment/activation remains an explicit operator action.
