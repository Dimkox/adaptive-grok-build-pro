# Architecture — M6 Provider-Independent Semantic Validation Provisional Slice

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This document cannot grant runtime or merge authority.

## Boundary ruling

The exact base is `94fc5ad878e6b15df6418303caada49a3b93bf4c`. Although the route snapshot carries an older program-base identity, the user's approved scope binds this provisional implementation to exact M4. No M5 execution contracts exist here, so this change adds no SQL, store, service, state, API, OpenAPI, migration, provider, systemd, or restart behavior.

## Components and flow

- `semantic_contracts.py`: immutable strict parsers, typed requirements/validator proof and canonical derived digests.
- `semantic_adjudication.py`: pure exact-subject validation and deterministic anomaly grouping. It derives the only verdict; provider decisions are not consumed.
- `semantic_repair.py`: pure policy emitting a directive only for cycles `1..3`, exact original writer, fresh context, unchanged bindings and remaining limits.
- `factory/contracts/jsonschema/*.json`: closed bounded public wire shapes, without implying API/persistence.

Trusted code constructs one `SemanticSubjectV1` from a sorted typed requirement set plus exact base/head, spec, architecture, authority, diff, deterministic, holdout and review digests; original writer/context; risk and diff limit. Findings and exact coverage bind `subject.digest` and validator proof. Adjudication checks bindings, derives typed finding identities excluding prose, reports duplicates/correlations/contradictions/unsupported passes, then applies `needs_human > repair > pass`. Repair either emits a bounded same-writer fresh-context directive or a typed escalation; it never mutates a run or calls a provider.

## Contract and security decisions

Requirement kinds are `acceptance_criterion`, `invariant`, `forbidden_outcome`, `architecture_rule`, and `non_functional_requirement`. Finding identity hashes subject, typed requirement, severity, category and rule identity, not message/reproduction/evidence wording. Coverage is exactly one sorted entry per requirement and `1_000_000` millionths.

Every finding/coverage embeds validator ID, role `semantic_validator`, sorted capabilities, definition/model/context digests. Proof must differ from original writer/context, require `repository_read` and `semantic_validate`, and forbid `application_write`, `adjudicate`, `external_write`, `network`, and `credential_read`. Narrative remains untrusted bounded data.

Any mutation to requirements, exact SHA/digests, writer/context, risk or diff policy changes the subject digest; former findings, coverage, verdicts and directives become stale.

## BLOCKED M5 bridge

TaskPacket input selection, RunManifest validator assignment, WorkspaceResult projection, provider event ingestion, durable stores, SQL fencing/idempotency, lifecycle transitions, repair child runs, cost/duration accounting, API/events, restart recovery and immutable evidence publication cannot be factual until M5. M7 PR evidence is later. Dependency-ordered restack/merge must place the eventual bridge after accepted M5; calendar deadline `2026-09-08T00:00:00+03:00` cannot change that order.

There is no runtime consumer, so rollout is inert. Revert pure-slice commits if M5 requires v2; no data/runtime/external recovery exists.
