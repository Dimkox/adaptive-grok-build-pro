# Integration boundary: durable M7 observations

Route `18ea639b9d02`; base `64378d2`; read-only design. Reviewed architect/repository reports and ordinary local source. No product edits, tests, network, database, secret or deployed-state access.

## Existing sources and their precise limits

- `trust-ci/src/adaptive_trust_ci/api.py:152` and `:162` expose authenticated read-only job and signed-attestation retrieval. These require an externally configured read capability; they do not authenticate a caller-supplied API base URL or public key.
- `trust-ci/src/adaptive_trust_ci/signing.py:272` verifies Ed25519 signature, payload key ID and canonical signed bytes. It does not establish that the supplied public key is trusted, current or unrevoked; pinning and lifecycle belong to deployment-controlled trust configuration outside the PR domain.
- `trust-ci/src/adaptive_trust_ci/models.py:269` binds repository, PR, base/head, policy, job/attestation identity, result and completion time. Validate the full tuple, successful result and producer schema after signature verification. Signature validity alone is neither freshness nor business acceptance.
- `trust-ci/src/adaptive_trust_ci/lookup.py:9` demonstrates full repository/PR/base/head/policy matching. It is internal Trust CI storage logic, not permission for factory to connect directly to deployed Trust CI PostgreSQL.
- `trust-ci/src/adaptive_trust_ci/runner.py:414` adds a `holdout-bundle-integrity` command result with `output_sha256=verified_holdout_digest`; `:483` includes those results in the signed payload. Thus historical holdout evidence exists indirectly, despite no top-level envelope field. A future adapter must require exactly one successful known result, a valid digest, and trusted producer semantics; do not infer from arbitrary command names or stdout.
- `trust-ci/src/adaptive_trust_ci/policy.py:245` includes holdout configuration in the canonical policy digest; `:268` derives the policy-epoch check name. A repository-local policy file cannot establish which policy/holdout is currently deployed. Mapping that holdout to an M7/M8 digest also needs explicit semantic correspondence.
- `trust-ci/src/adaptive_trust_ci/api.py:201` strips top-level `check_run_id` and `holdout_digest` from public job results. `AttestationPayload` also lacks App ID/check-run ID/check name. These fields must come from an independently authenticated current GitHub observation, not invented envelope fields.
- `trust-ci/src/adaptive_trust_ci/github.py:130` is a mutating check publisher, not a safe observation adapter. Its initial GET must not be reused by calling `ensure_check_run`; that method subsequently PATCHes or POSTs. No existing read-only currentness adapter was found in this inspected client.
- `factory/src/adaptive_factory/store.py:399` reconstructs canonical persisted execution material, supporting task/run/fence/result binding. Existing intake acceptance and caller `human_decision` at `shadow_contracts.py:706` do not authenticate delivered-business acceptance.

## Required independent observation joins

1. Resolve factory repository/task/run/completed result and M7 bundle/outcome digests from their producer/store identities. Never use an intake input SHA to authenticate a different result SHA; a completed run need not retain a live lease.
2. Verify the unchanged signed envelope against deployment-pinned public verification material, then match repository/PR/base/head/policy/job. Preserve original envelope bytes/canonical digest and verification-source/version identity.
3. Independently observe the current PR base/head and the exact completed-success Check Run: expected deployed epoch name, configured GitHub App ID, head SHA, numeric check ID, and external job ID matching the attestation. A check name, merge actor or green generic status alone is insufficient.
4. Obtain a current, authenticated deployed policy/holdout context from its separately operated owner. Compare full policy digest and holdout semantics to the envelope/result and requested M8 profile. A stale signed success or caller-provided expected epoch cannot assert currentness.
5. Obtain an explicit authenticated business outcome bound to the delivered task/run/result/bundle/outcome and decision identity. Trust CI `approved_scopes` proves recorded security-scope validation at the CI run, not human product acceptance or currently valid approvals. No existing source supplies this missing business-outcome authority in the inspected code.
6. Bound the combined observation by server-observed time, source freshness/expiry and revocation/supersession lineage. Reobserve or mark unavailable when base/head/policy/holdout/App configuration changes; historical acceptance may remain a historical fact while current qualification fails.

## Smallest additive initial patch

Add an observation-only lookup/preflight contract and immutable persistence in the existing factory database, using existing completed execution/semantic identities and narrow reader/observer capabilities. Keep raw imported claims distinct from independently verified observations; storing a body or a `verified=true` flag cannot authenticate it.

Define narrow source protocols for signed-CI verification provenance, GitHub current-state observation, deployed-epoch observation and explicit human outcome. Configure every live protocol as unavailable by default. The initial patch may exercise bounded synthetic adapters and persisted replay/restart behavior; real network ingestion, signing/key operations, currentness collection and producer deployment are separate work.

A preflight result should identify resolved bindings, source provenance, observation digest and typed missing/rejected reasons. It must never be accepted as merge authority or converted into a caller-settable availability Boolean. If a trusted source is absent, stale, revoked, unreachable or conflicting, report unavailable; do not fall back to imported claims or cached green status.

Replay identity must bind source plus immutable event identity and canonical body. Exact repeats are idempotent; different bodies with the same identity conflict. Preserve later supersession/revocation as append-only observations. Runtime application writers cannot create acceptance/currentness observations through ordinary task APIs.

Preserve `M7AutonomyBridgeV1` false availability (`factory/src/adaptive_factory/m7_autonomy_bridge.py:168`), blocked V1 bundle serialization, current M8 evaluator/authority ceiling, and M9 rejection/fixed false properties (`delivery/src/adaptive_delivery/m8_boundary.py:174`, `:224`). New preflight coverage cannot silently turn old V1 blocked bundles into ready deliveries.

## Missing prerequisites for a later live adapter

- Deployment-approved, read-only Trust CI/GitHub endpoints and capabilities, configured App identity, pinned CI public-key lifecycle, and authenticated current policy/holdout provenance.
- An independently authenticated explicit business-acceptance producer with exact delivery binding, replay protection and revocation semantics; merge attribution is insufficient.
- Agreed freshness bounds and profile-to-deployed-holdout mapping, plus a versioned producer/consumer contract if promotion is eventually enabled.
- Existing named scope/design approval must be satisfied before product implementation; no source integration, live migration or activation is performed by this analysis.

Memory fact: a Trust CI signature authenticates a historical exact tuple, and its signed command results can bind the verified holdout, but current App/PR/deployed epoch and explicit business acceptance still require separate trusted sources; persistence alone supplies none of that authority.
