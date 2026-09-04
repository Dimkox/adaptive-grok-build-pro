# M7 bounded shadow handoff on exact M6 c6d48ff

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260904-m7-bounded-shadow-handoff-on-exact-m6-c6d48ff-03b8e2`
Created: 2026-09-04T03:01:40+00:00
Risk: medium
Complexity: standard
Domains: ai, api

## Problem

Implement the M7 AI agent shadow handoff feature on exact M6 head c6d48ffd8594b3baab1a575021452ea5dfa2a98b: immutable ready-for-human bundle, canonical M4-M6 producer bindings, deterministic shadow cohort evaluation, bounded failure and staleness handling, and an operator-owned proposal that carries no operational capability. Preserve all predecessor source and migrations. Repository-local implementation only; no live provider, remote action, delivery, or external write.

## Outcome

The exact M6 source gains a repository-local, provider-independent M7 contract layer that can assemble an immutable handoff bundle from canonical M4-M6 facts and evaluate a bounded shadow cohort deterministically. The output is evidence for an operator decision only: it cannot create a pull request, merge, invoke a provider, use a credential, or perform any external action.

## Scope

### In scope

- Six closed version-1 JSON Schemas for predecessor bridges, task evidence, the blocked handoff bundle, the operator proposal, outcomes, and cohorts.
- Pure Python contracts that independently recompute identities and bind separate M4 legacy intent, M5 task packet, input-head, result-head, and M6 semantic evidence facts.
- Pure deterministic cohort aggregation and threshold evaluation that may recommend only human level-2 review.
- Additive architecture ownership, two focused test modules, and formal repository-local evidence.

### Out of scope

- Database persistence, migrations, HTTP operations, queues, background workers, service activation, provider calls, credentials, and network access.
- Durable lookup or publication of a ready bundle; the source-only bundle remains `blocked_pending_durable_lookup`.
- Real human-outcome collection, an M8-qualified cohort, automatic approval, pull-request creation, merge, release, deployment, or production mutation.
- Modification of any M4-M6 source, contract, migration, history, or runtime behavior.

## Constraints

- Backward compatibility: the implementation is add-only on exact M6 `c6d48ffd8594b3baab1a575021452ea5dfa2a98b`; canonical M7 `4df2516b` is semantic source material, not lineage authority.
- Data/privacy: closed outcome schemas accept digests and bounded counters only; prompt bodies, reasoning traces, personal data, commands, URLs, and credentials are not fields.
- Performance: cohort and baseline inputs are bounded to 10,000 items and use deterministic integer arithmetic with no I/O.
- Operational: no capability is injected or exposed; all delivery, review, packaging, and external gates remain separate.
