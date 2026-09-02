# M6 Provider-Independent Semantic Validation Provisional Design

## Status and boundary

User-approved provisional design for exact M4 base `94fc5ad878e6b15df6418303caada49a3b93bf4c`. M5 `TaskPacket`, `RunManifest`, and `WorkspaceResult` do not exist there. Only provider-independent wire contracts and pure policy are frozen; persistence, API, runtime, lifecycle and restart wait for factual M5.

Canonical package: [`engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/`](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/brief.md). Current topology: [README](../../../README.md) ↔ [roadmap](../../../DARK_FACTORY_ROADMAP.md) ↔ this design ↔ [plan](../plans/2026-09-01-m6-semantic-validation-provisional.md) ↔ [release](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/release.md) / [rollback](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/rollback.md) / [ledger](../../../engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/implementation-ledger.md).

## Contract graph

```text
M4 exact evidence identities
  ↕ (current facts only)
BLOCKED factual M5 bridge: TaskPacket + RunManifest + WorkspaceResult
  ↕ (future versioned adapter, never inferred here)
M6 SemanticSubjectV1
  ↔ SemanticFindingV1 + SemanticCoverageV1
  ↔ deterministic SemanticVerdictV1
  ↔ bounded RepairDirectiveV1 cycles 1..3
  ↕ (later, after full M6 evidence)
M7 PR evidence
```

The graph is bidirectional because later evidence must trace back to exact inputs, while mutations of those inputs invalidate downstream evidence. The provisional code implements only the M6 middle contracts and pure arrows; both outer bridges remain non-runtime documentation.

## Contracts

Five closed Draft 2020-12 schemas mirror immutable Python parsers. `SemanticSubjectV1` binds sorted typed requirements to exact base/head, spec/architecture/authority/diff/deterministic/holdout/review digests, original writer/context, risk and diff policy; its digest is the evidence root. `SemanticFindingV1` binds typed severity/category/rule plus bounded narrative and read-only validator proof; derived recurrence identity excludes prose. `SemanticCoverageV1` has exactly one sorted status per requirement and integer `1_000_000` coverage. `SemanticVerdictV1` is deterministic and reports anomalies without a transition. `RepairDirectiveV1` binds a repair verdict to cycle `1..3`, original writer, fresh context and unresolved identities.

Schemas reject extra fields/version/bounds; parsers also enforce NFC, UTF-8, uniqueness, ordering and cross-field equality. Requirement kinds are acceptance criterion, invariant, forbidden outcome, architecture rule and non-functional requirement.

## Adjudication and separation

Adjudication rejects stale bindings, sorts all inputs and derives duplicates, same-requirement correlations, coverage contradictions and unsupported passes. Precedence is `needs_human > repair > pass`; pass needs exact unanimously evidenced coverage and no unresolved finding. Provider decision/state/capability/writer proposals are never accepted.

Validator proof includes ID, role `semantic_validator`, sorted capabilities and definition/model/context digests. It differs from original writer/context, requires `repository_read` and `semantic_validate`, and forbids `application_write`, `adjudicate`, `external_write`, `network`, `credential_read`. This is structural; OS isolation remains M5 work.

## Repair and staleness

A directive requires verdict `repair`, cycle `1..3`, original writer, unused context, unchanged bindings, non-increased risk, bounded diff, positive deadline/budget and no recurring typed finding. Fourth cycle, recurrence despite paraphrase, wrong writer, reused context, risk/diff/architecture/authority/base/budget/deadline violation returns `needs_human`. Semantic cycles do not reuse M4 infrastructure attempts or `repair_count`.

Any relevant subject mutation changes the digest and invalidates all downstream evidence. A later M5 adapter either consumes exact v1 or introduces v2; it cannot reinterpret v1.

## Verification and claim

TDD covers parser/schema closure, digest stability, permutations/anomalies, precedence and escalation matrix. Structure/architecture tests reject orphan/stale current M6 docs and graph nodes. No provider/database/network/credential/holdout/reviewer/systemd action occurs. Passing proves only this provisional pure layer, not durable/runtime/full M6 or M7.

Planning deadline `2026-09-08T00:00:00+03:00` coordinates parallel development; dependency-ordered merge still requires factual M5 before the runtime bridge.

## Self-review

No placeholder or open semantic choice remains. Types, bounds, precedence, stale-state behavior, security separation, rollback, connectivity, blocked dependencies and claim limits are explicit.
