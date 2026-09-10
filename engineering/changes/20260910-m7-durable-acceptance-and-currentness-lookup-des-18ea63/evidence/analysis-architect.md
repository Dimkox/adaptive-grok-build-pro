# Architect: durable M7 acceptance/currentness lookup

Route `18ea639b9d02`; base `64378d2`; analysis only. No product files, tests, secrets, remote state or production systems were changed/read beyond ordinary repository source. The named scope/design gate remains pending.

## Existing contract constraints

- `factory/src/adaptive_factory/shadow_contracts.py:539` and `factory/contracts/jsonschema/ready-for-pr-bundle.v1.schema.json:10` require `ReadyForPrBundleV1.status=blocked_pending_durable_lookup`. Status participates in its domain-separated digest; changing its interpretation is a versioned contract change.
- `factory/src/adaptive_factory/shadow_contracts.py:706` stores a declared `human_decision` and `human_evidence_digest`, but does not authenticate the decision producer or look up durable facts.
- `factory/src/adaptive_factory/m7_autonomy_bridge.py:93` reparses producer bodies and binds bundle/outcome/profile identities. Its availability properties at lines 168 and 172 always return false.
- `factory/src/adaptive_factory/autonomy.py:773` applies metric thresholds, blocked-bundle status, acceptance availability and currentness. `evaluate_autonomy` at line 829 returns recommendations only, with separate activation and no external authority.
- `factory/tests/test_shadow_contracts.py:353` freezes the blocked V1 shape. `factory/tests/test_autonomy.py:357` rejects caller availability flags; its test at line 539 blocks thirty plausible synthetic records.
- `delivery/src/adaptive_delivery/m8_boundary.py:174` explicitly rejects upstream availability, and lines 224–229 fix downstream durable availability false. M9 cannot be enabled as a side effect of this work.

## Alternatives

| Design | Benefit | Cost / boundary | Decision |
| --- | --- | --- | --- |
| JSON ledger or append to generic local receipts | Smallest storage change | Caller-controlled persistence does not authenticate acceptance or establish currentness; duplicates trust bookkeeping | Reject as an authority source; historical inventory remains useful evidence only |
| Additive typed lookup using existing factory PostgreSQL, consumed by an M8 preflight report | Reuses durable execution identities and capability-isolated persistence, supports restart/replay tests, preserves V1 | Needs one additive migration, narrowly scoped reader/writer functions, explicit trusted observation sources | Recommend for this milestone |
| New M7/M8 promotion contracts plus live Trust CI/GitHub collector | Could support qualified recommendations using authenticated fresh external facts | Expands wire formats, network credentials, deployment configuration, downstream compatibility and activation boundary | Defer to a separate approved milestone |

## Recommended bounded design

Add `factory/src/adaptive_factory/shadow_lookup.py` for closed request/result contracts and pure binding validation, and `factory/contracts/jsonschema/m7-durable-lookup.v1.schema.json` for matching producer-owned schema. Add a small capability store class in existing `factory/src/adaptive_factory/store.py` and an additive `factory/src/adaptive_factory/resources/019_m7_durable_evidence.sql` migration; do not alter historical migrations. Data analysis should settle exact relation/index names.

Keep pure M7 contracts under `NODE-FACTORY-SHADOW-HANDOFF`, storage under `NODE-FACTORY-CONTROL` and `NODE-FACTORY-POSTGRES`, and the preflight consumer under `NODE-FACTORY-EARNED-AUTONOMY`; extend existing ownership/contract records in `architecture/system.yaml`. Model the existing control-plane-to-M7 lookup dependency explicitly if introduced. No new service, datastore or network-capable M7 component is needed.

Use the existing isolated-capability pattern from `store.py:236` (`PostgresArtifactAttestationStore`) and `store.py:298` (`PostgresSemanticCoordinatorStore`). The runtime/writer role must not be able to forge accepted evidence. Reader capability receives only bounded lookup functions; a separately configured observation capability may append immutable records through checked functions. Neither obtains arbitrary table writes or authority to alter task execution. Capabilities remain unconfigured by default.

Persist immutable acceptance observations and external-check observations bound to existing canonical factory execution records. Reuse stored task/run/fence, packet, manifest, workspace result, semantic subject/verdict and terminal-proposal bindings rather than copying caller assertions into authoritative columns. `store.py:399` already reconstructs checked execution material; migration 018 supplies semantic FKs and canonical bodies. Preserve provenance/body digests and observed times for audit.

Acceptance records must distinguish authenticated business acceptance from an imported assertion, GitHub merge attribution and Trust CI security approval. Each observation binds repository, task/run identity, bundle/outcome digest, exact result head, decision source identity and decision digest. The actual trusted business-acceptance producer is a deployment integration to specify; no human signing keys are generated, requested, read or submitted by the implementation. Until that source is configured, acceptance lookup is unavailable.

External-check observations bind repository, PR number, exact base/head, configured GitHub App identity, policy-epoch check name, policy digest, external job/attestation identity, observation time and freshness bound. Validate the external signed envelope using trusted externally supplied public verification material only when that capability exists. Raw imported JSON is an observation claim and must never be promoted to authenticated check evidence merely because it was stored.

The existing Trust CI signed schema at `engineering/contracts/schemas/trust-ci-attestation-envelope.v1.json:160` binds repository/PR/base/head/policy/scopes but has no explicit GitHub App ID, check name or holdout digest. Preserve this limitation: currentness requires independently authenticated current deployed epoch/check provenance; do not invent those fields from the envelope. `trust-ci/src/adaptive_trust_ci/policy.py:245` includes holdout in canonical policy material. Any correspondence to an M7 holdout digest must be proved through trusted policy material or remain unavailable.

Do not connect directly to external Trust CI PostgreSQL. Existing read API routes are `/jobs/{job_id}` and `/attestations/{job_id}` (`trust-ci/src/adaptive_trust_ci/api.py:152`); no network collector or deployed Trust CI change is required for this design milestone. `trust-ci/src/adaptive_trust_ci/lookup.py:9` illustrates why repository plus head alone is insufficient: the full PR/base/head/policy tuple must match.

Lookup request binds full repository/task/run/result/bundle/outcome/profile identities and requested evaluation context. Result is a closed tagged union: unavailable with a bounded reason code, or a digest-bound durable observation snapshot with acceptance and currentness provenance separately represented. A success result means the queried facts were resolved under that observation context; it is never merge authority, promotion or activation permission.

Use one transactionally consistent snapshot for multi-table lookup, comparing task generation, accepted intent, execution fence/result and semantic bindings. A terminal completed run need not retain a live lease; validity follows its persisted accepted generation/result chain. Superseded/cancelled task, wrong tenant, changed base/head, replaced policy/holdout context, expired/future observation, corrupt body or absent authenticated source returns unavailable/rejected. Caller-supplied `now` cannot prolong an externally established freshness bound; server-observed database time governs durable lookup.

Deduplicate exact observation replays by source identity plus canonical request digest. Same identity with different contents is an integrity conflict; never last-write-wins. A new currentness observation may supersede a prior observation without rewriting history. Historical acceptance can remain factual after a later code change while current qualification becomes unavailable. Database outage produces explicit unavailable; never silently use a stale cached pass.

Consume lookup through an additive `inspect_m7_durable_evidence(...)` preflight entrypoint in `m7_autonomy_bridge.py` or a small sibling owned by M8. It returns coverage, unresolved binding reasons and a digest-bound observation report; it must not change `M7AutonomyBridgeV1`, `ReadyForPrBundleV1`, `CohortEvidenceV1`, `PromotionRecommendationV1`, `evaluate_autonomy`, the L2 ceiling or M9 behavior. Replacing three V1 gate failures with a lookup Boolean would conceal an unbound contract transition and is outside this milestone.

## Acceptance criteria and checks for later implementation

1. Missing capability/evidence/database remains unavailable by default; existing V1 serialization and gate tests pass unchanged.
2. Authenticated synthetic fixture records survive an actual disposable PostgreSQL restart and resolve the same exact context afterward.
3. Replay is idempotent; conflicting replay, wrong repository/PR/base/head/profile, stale generation/fence and corrupted persisted bodies fail closed.
4. Freshness boundary, policy/holdout replacement, future timestamps, source revocation/unavailability and stale-cache fallback receive meaningful regression coverage.
5. Runtime writer cannot append accepted observations or access observation-only capability functions; reader cannot mutate any evidence or task records.
6. Full lookup evidence produces only M8 preflight coverage. Thirty accepted tasks, perfect metrics and fresh checks still cannot raise the V1 recommendation or authorize delivery in this milestone.
7. Migration is additive, bounded and indexed on exact lookup keys; explain representative query plans and role grants. Do not backfill trust from existing unverified strings.
8. Preserve append-only observations on rollback; disable injected capability and return to unavailable behavior. No destructive reverse migration is necessary.

## Main risks and memory fact

The largest risk is confusing durable storage with authenticated origin. The second is equating an old signed success with current deployed policy/check state. Both require explicit source provenance and conservative unavailable results, not more caller flags.

Memory fact: V1 M7 blocked status and false availability are intentional digest-bound compatibility guarantees shared with M9; durable lookup should first add a separate M8 preflight observation contract, without changing promotion or activation semantics.
