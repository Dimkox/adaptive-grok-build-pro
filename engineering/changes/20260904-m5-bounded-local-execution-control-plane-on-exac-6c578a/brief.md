# M5 bounded local execution control plane on exact M4 67dc4dd

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-m5-bounded-local-execution-control-plane-on-exac-6c578a`
Created: 2026-09-04T01:25:19+00:00
Risk: high
Complexity: high-risk
Domains: data, security, ai, api

## Problem

Implement the M5 bounded local AI execution control plane on exact M4 head 67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4. Preserve all M4 control behavior; add PostgreSQL database migrations 014-017, immutable execution packets, provider-neutral API contracts, fenced durable recovery, offline conformance adapters, authorization, and tenant isolation. Repository-local implementation only; no live provider calls or operational actions. Defer non-critical hardening extensions outside the defined milestone acceptance boundary.

## Outcome

Provide a repository-local, disabled-by-default execution control plane that can turn an authenticated M4 lease grant into immutable execution material, bounded canonical proposals, a trusted workspace result, and factual restart recovery without granting authority to provider output. The result is an additive M5 source checkpoint; it is not live-provider, deployment, delivery, or production evidence.

## Scope

### In scope

- Preserve exact M4 predecessor `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` and all migrations `001`-`013`.
- Semantically port the final reviewed M5 behavior from reference `3940267ac5754ad07a047894102015d33eb759b1`; exact M4 wins every overlap.
- Add unpublished forward migrations `014`-`017`, immutable packet/manifest/result identities, closed execution v1/v2 contracts, offline exact-version adapters, server-owned authorization, proposal/finalization, tenant isolation, and bounded recovery.
- Use only fixture adapters, deterministic brokers, and isolated disposable PostgreSQL 17 for local evidence.

### Out of scope

- Live provider invocation, provider SDKs, credentials, subprocesses, network egress, real workspace or Git mutation, provider fallback, and host-isolation qualification.
- Shared or persistent database mutation, service installation/activation, M6 behavior, push, pull request, merge, tag, release, deployment, external write, or production action.
- Additional provider versions, fleet/HA tuning, retention automation, and non-blocking hardening beyond the finite acceptance criteria.

## Constraints

- Backward compatibility: M4 control OpenAPI remains the unchanged 17-operation authority; M5 contracts and routes are additive and capability-gated.
- Data/privacy: repository-scoped tenancy, closed canonical records, no secrets, raw provider streams, prompts, environment values, or private reasoning in durable output.
- Performance: recovery is indexed, keyset-paged, bounded to 2-100 candidates and a 30-second call budget; fixed-cardinality metrics only.
- Operational: execution is disabled by default and startup fails closed before socket exposure if any trusted execution dependency is incomplete.

## Lineage and authority

Route base `78ad2f679d38dc3244e716c586332417e610089c` is the delivery-comparison base selected by the router. Exact integration predecessor `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` is the sole source base for this M5 branch. User approval covers repository-local source, authoring additive unpublished migrations `014`-`017`, and disposable local PostgreSQL; it grants no operational or external authority.
