# L5 single-operator live MVP local runtime

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260905-l5-single-operator-live-mvp-local-runtime-65b201`
Created: 2026-09-05T11:38:47+00:00
Risk: medium
Complexity: standard
Domains: ai, api, data

## Problem

Implement additive AI landing normalization with exact Codex CLI for text, image, PDF, and DOCX; add a restart-safe SQLite landing job and artifact store; add a transport-injected reversible hosting adapter with deterministic fake-transport tests. Keep voice unsupported for MVP, keep network calls and remote mutation disabled in this task, preserve v2.0.14 bytes and exact source identity, and keep external model access and remote actions behind later exact grants.

## Outcome

Deliver a bounded Stage 3/5 offline technical preview for one local operator. An
authenticated landing submission can be normalized through a trusted, disabled-
by-default native-Codex seam, durably replayed from SQLite, and converted through
the existing renderer, evaluator, and packager into a fully bound local
`SiteArtifactV1`; `live_url` remains `null`.

## Scope

### In scope

- A closed normalizer profile and executor port for strict text, validated image,
  and safe DOCX fixtures; PDF and audio terminate `needs_human` before executor
  invocation.
- A stdlib SQLite store for one operator with private-root enforcement, WAL/FULL
  durability, composite tenant/repository/job identity, durable submit/cancel
  replay, terminal records, and finite fail-closed startup recovery.
- A concrete bridge from the existing provider/coordinator to the existing
  deterministic artifact packager, retaining complete sealed metadata.
- If it remains a small isolated library seam, transport-injected reversible
  publication semantics proven only by deterministic fakes and never wired into
  the server.
- Focused local tests and one later exact-head verifier plus one route-selected
  review wave after the source tree is frozen.

### Out of scope

- Any live Codex/model call, network access, provider credential use, target or
  hosting mutation, GitHub action, publication, deployment, or production claim.
- OCR, PDF extraction, audio transcription, automatic retry/fallback, background
  workers, HA, leases, queues, garbage collection, backup orchestration, UI, and
  PostgreSQL migration `019`.
- A cPanel/LiteSpeed implementation. It is downstream and requires separate
  target-bound authority, credentials, observation, and rollback evidence.

## Constraints

- Backward compatibility: published `v2.0.14` package bytes, the frozen landing
  OpenAPI v1 snapshot, migrations `001`-`018`, exact landing source identity,
  renderer write paths, and existing in-memory/API behavior remain unchanged.
- Data/privacy: raw input, credentials, prompts, model prose, and unrestricted
  stderr are not stored in SQLite evidence or logs; every lookup uses the full
  tenant/repository/job key.
- Performance: one process, bounded input/output/time, at most three existing
  coordinator attempts, short SQLite transactions, and finite startup recovery.
- Operational: the default provider and publisher remain unavailable, no no-tool
  guarantee is claimed without separate conformance evidence, and no current
  evidence may populate a live URL.
