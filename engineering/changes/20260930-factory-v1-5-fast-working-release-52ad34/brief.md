# Factory v1.5 fast working release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260930-factory-v1-5-fast-working-release-52ad34`
Created: 2026-09-30T18:29:02+00:00
Risk: medium
Complexity: standard
Domains: api, event

## Problem

Реализовать код фабрики: добавить минимально рабочие U0-U3 и U5-U7 по FACTORY_UNIFIED_UPGRADE_TZ v1.5, исключить U4 macOS решением владельца, добавить версионированные API и event contracts с тестами

## Outcome

A runnable Linux factory candidate exposes a deterministic context manifest, factual decision/accounting records, sanitized pre-model tool-result evidence, observation-only prediction artifacts, and an honest qualification summary. Apple scope is explicitly excluded and optional adapters remain default-off.

## Scope

### In scope

- U0-U3 and U5-U7 minimal vertical implementation.
- Versioned additive contracts and tests.
- BB-01 as a default-off optional execution/observation backend contract with native fallback; no live activation claim.
- Native context path; optional FPF/VibeVM only when exact qualification exists.
- Local verification, independent review, and release-candidate evidence.

### Out of scope

- U4/macOS, Xcode/XCTest, notarization, and Hackintosh (`excluded_by_owner`).
- M8 activation or fabricated 30-task cohort.
- Production deploy, merge, tag, or GitHub Release without separate exact authority.
- A new database, queue, service, or distributed transaction.

## Constraints

- Backward compatibility: closed v1/v2 schemas stay unchanged; use versioned sidecars.
- Data/privacy: reject secrets, absolute/traversal paths, and cross-repository context.
- Performance: every collection and payload is bounded; no unbounded scans.
- Operational: default-off rollout, forward-fix migrations, exact-head evidence.
