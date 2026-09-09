# M6 bounded semantic validation on exact M5 85cd434

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-m6-bounded-semantic-validation-on-exact-m5-85cd4-e323f2`
Created: 2026-09-04T02:20:38+00:00
Risk: medium
Complexity: standard
Domains: data, ai, api

## Problem

Integrate the existing M6 provider-independent AI semantic validation source onto exact M5 head 85cd4343143915ce9342634e7fe81886b6394871. Preserve all M5 control and execution behavior; add typed criterion verdicts, deterministic contradiction handling, at most three correction cycles, fourth-cycle needs_human, exact SHA evidence regeneration, and PostgreSQL database migration 018. Repository-local source only; no live provider calls or operational actions.

## Outcome

Provide a disabled-by-default, provider-independent semantic validation layer that converts exact M5 workspace results into typed evidence, deterministic verdicts, and bounded repair directives. The checkpoint is repository-local source; it does not authorize live models, application mutation, shared database changes, service activation, delivery, or production use.

## Scope

### In scope

- Seven closed semantic JSON Schemas and six additive authenticated control-plane operations.
- Exact M5 result-to-subject binding, independent validator assignments, typed findings and coverage, deterministic adjudication, and append-only persistence.
- Repair cycles one through three through the reserved M5 broker identity; cycle four and unsafe, stale, recurrent, contradictory, or unproven cases terminate as `needs_human`.
- Additive migration `018_semantic_validation_bridge.sql`, byte-identical to the canonical final SQL body, on unchanged M5 migrations `001`-`017`.
- Focused pure, seam, and disposable PostgreSQL 17 evidence only.

### Out of scope

- Live provider/model invocation, provider-specific verdict logic, application-write authority, public repair endpoints, automatic recovery daemons, and production activation.
- Shared or persistent database mutation, network or credential access, systemd activation, push, pull request, merge, tag, release, deployment, or external write.
- General hardening or exploratory edge-case expansion outside the finite acceptance boundary.

## Constraints

- Backward compatibility: all current M4/M5 contracts, operations, lifecycle behavior, and migrations `001`-`017` remain unchanged.
- Data/privacy: provider content is untrusted typed evidence and cannot originate authority; no secrets, private reasoning, or customer data leave the repository-local boundary.
- Performance: all collections, payloads, repair cycles, database calls, and indexes are bounded by the closed contracts and migration.
- Operational: semantic composition remains disabled unless all three disjoint capabilities and dependencies are explicitly injected and ready.
