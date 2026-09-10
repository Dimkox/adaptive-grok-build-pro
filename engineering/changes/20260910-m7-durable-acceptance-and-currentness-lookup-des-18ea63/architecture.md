# M7.1 design — additive durable lookup and preflight

Status: proposed for scope/design approval. No product implementation or live source integration is included in this design checkpoint.

## Existing behavior and selected approach

M4–M6 persist canonical task, completed run/result and semantic records. M7 bundles/outcomes are pure values. Their blocked V1 status, both false M8 bridge properties and M9's rejection of true V1 availability are compatibility guarantees.

Compared approaches: a JSON ledger cannot authenticate evidence; a full versioned promotion plus live collector expands scope into deployment and activation. Select a capability-isolated PostgreSQL lookup and separate M8 preflight. It improves retrieval and binding without changing the V1 evaluator.

## Proposed surfaces

- Add `factory/src/adaptive_factory/shadow_lookup.py`: closed lookup/observation/result contracts, canonical hashing and binding validation.
- Add `factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json` with schema parity and bounded tagged states.
- Add a narrow store capability in `store.py` and forward migration `resources/019_m7_durable_evidence.sql`; preserve 001–018.
- Add a sibling preflight consumer under the existing M8 architecture owner, with explicit `m8_qualification=not_evaluated` and `authority_effect=none`.
- Enroll paths/dependencies in existing architecture ownership. No new service, engine, framework, HTTP operation or network client is proposed.

## Stored facts and lookup

Use the five relations proposed by data analysis: canonical bundles, outcome/acceptance observations, check observations, independently observed current contexts, and idempotent command results. An acceptance observation may exist without a complete `ShadowOutcomeV1`; nullable outcome/profile/measurement coverage remains explicit. Resolved rejection differs from unavailable evidence.

Bundle registration cross-checks stored intent, repository, task/run/fence/generation, packet/result, semantic subject/verdict and exact input/result head. Completion clears the active lease pointer: resolve immutable completed-run facts, not current_run_id.

Exact source event/body replay returns one result; same identity with a conflicting body is rejected. Preserve append-only supersession/revocation and authenticated per-source ordering. Never let later database receipt time alone make an older external event current.

Select the latest independently authenticated repository/PR context first, then compare requested base/head/App/check/policy/holdout. Filtering old green checks by the caller's desired policy cannot prove currentness. Return a bounded single-snapshot result with database-observed time and expiry; a successful observation is not a reusable permission token.

Indexes cover bundle/task/run/profile and source stream revision plus repository/PR subject. Use bounded lookups and history pages, no full JSON scans. Validate plans with representative disposable fixtures; no production volume is assumed.

## Trust provenance and unavailable sources

Keep intake acceptance, technical validation, PR merge, business acceptance and signed security approval as separate facts. A digest, database insert, dedicated DB role or caller `verified=true` flag authenticates none of them by itself.

Expose narrow source protocols for independently authenticated human outcome, signed CI verification, current GitHub Check Run/PR/App observation and current deployed policy/holdout observation. Their production bindings remain unavailable. Initial positive tests use explicitly synthetic trusted-source fixtures, never real qualification evidence. Live acquisition and source deployment belong to M7.2.

Trust CI signs repository/PR/base/head/policy/result/time. The signed `command_results` can also bind historical holdout: runner.py records the verified digest as the unique successful `holdout-bundle-integrity.output_sha256`. A future verifier must validate trusted producer semantics and uniqueness. There are no explicit top-level App/check-name fields; current App/PR/deployed epoch requires independent authenticated observation. A supplied public key must not become its own trust anchor.

Business acceptance binds the exact result and authenticated decision source, with revocation. Missing profile/operator/quality metrics remain unknown and do not prevent recording that acceptance; they do prevent a complete qualification claim. Historical evidence is admitted only with actual contemporaneous bindings, never today's profile defaults.

## Capabilities and failure behavior

Use separate registry, outcome-observer, check/context-observer and reader capabilities following existing fixed-search-path SQL functions and denied direct writes. Source/repository scopes derive from configured principals, never the body's source_id. Application runtime receives no observer write capability. No connection to deployed Trust CI PostgreSQL or reading signing/approval keys is proposed.

Missing source/store/record, corrupt binding, conflicting replay, stale task generation, mismatched context, revoked source, future timestamp or expiry yields a precise unavailable/rejected reason. No stale green fallback. Scope-positive source fixtures leave every V1 gate and the L2 ceiling intact.

## Delivery sequence and evidence

1. Contracts/source protocols and adversarial cases.
2. Additive migration/store, cross-binding checks and source/repository capability tests.
3. Snapshot lookup plus preflight, explicit partial evidence and reason codes.
4. Real disposable PostgreSQL/process restart, replay/concurrency/expiry/revocation checks.
5. Full required verifier, independent code/test/security/data/release review as selected by the implementation route, then separately authorized PR and exact-SHA external Trust CI.

Rollback disables new source/reader bindings and preserves immutable evidence; repair forward. No historical backfill or destructive migration.

## Consolidated decisions

The six selected analyses are complete. Their recommendations are reconciled as follows: keep outcome body optional for partial acceptance; use a separate latest-context stream; recognize signed historical holdout in command_results; preserve all V1 semantics. Source acquisition, revocation policy configuration, source ordering and freshness limits are explicitly external prerequisites, not silently invented defaults.

Sources: [repository trace](evidence/analysis-repo_explorer.md), [alternatives](evidence/analysis-architect.md), [data](evidence/analysis-data_architect.md), [AI/profile rules](evidence/analysis-ai_architect.md), [integration](evidence/analysis-integration_architect.md), [milestone plan](evidence/analysis-docs_researcher.md).
