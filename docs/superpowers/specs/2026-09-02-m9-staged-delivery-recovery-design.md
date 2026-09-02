# M9 Staged Delivery and Recovery Design

## Status and authority

Approved architectural design and source-only execution scope under route `e376373492fe`. The 2026-09-02 user ruling permits Tasks 1–4 as pure local source/tests using synthetic opaque exact identities. The branch remains based provisionally on M4 source `9fe779ab9f90719201acfd01160d3452658ff075`; neither fixtures nor observed provisional M4–M8 commits are accepted dependency evidence or deployment authority. The hard deadline is **2026-09-08 00:00 UTC+3**.

## Goal

Build a pure local deterministic M9 evaluator and dry-run controller that binds an exact merged commit and externally verified signed artifact to preview, staging and bounded-canary evidence, fails closed on bad observations, and stops at human-owned production.

## Closed common values

- Git identity: lowercase 40-hex exact merged SHA.
- Content identity: lowercase 64-hex SHA-256.
- IDs: 1–128 ASCII characters from `[A-Za-z0-9._:/-]`.
- Time: UTC RFC3339 with whole seconds and terminal `Z`.
- Exposure: integer basis points from 0 through 10,000; plans contain 1–16 strictly increasing unique values.
- Environment: exactly `preview`, `staging`, `bounded_canary`, `production` in that order.
- Authority reference: opaque tuple `envelope_digest`, `external_verifier_id`, `verified_at`, `expires_at`, `scope`, `resource_digest`. There are no signature bytes, keys, certificates or envelope bodies.
- Every record is immutable, canonical-JSON digestible and closed to unknown fields. A semantic or field change creates V2.

## Contract shapes

### `SignedArtifactRefV1`

| Field | Meaning |
| --- | --- |
| `schema_version` | constant `1` |
| `repository_id` | bounded tenant/resource ID |
| `merged_sha` | exact protected-merge commit |
| `artifact_digest` | artifact SHA-256 |
| `sbom_digest` | exact SBOM SHA-256 |
| `provenance_digest` | exact provenance statement SHA-256 |
| `supply_chain_manifest_digest` | exact manifest SHA-256 |
| `image_digest` | immutable image/material SHA-256 |
| `authority_envelope_digest` | opaque externally verified envelope SHA-256 |
| `authority_verifier_id` | external verifier identity |
| `authority_verified_at` / `authority_expires_at` | validity interval |
| `authority_scope` | constant `signed_artifact_use` |
| `authority_resource_digest` | must equal this artifact reference's canonical resource digest |

### `ExposurePlanV1`

| Field | Meaning |
| --- | --- |
| `schema_version` | constant `1` |
| `plan_id` | stable ID |
| `environment_order` | exact four-value order |
| `preview_basis_points` | fixed tuple, normally `(10000,)` in isolated preview |
| `staging_basis_points` | fixed tuple, normally `(10000,)` in isolated staging |
| `canary_basis_points` | 1–16 strictly increasing values, maximum bounded below production-wide exposure |
| `max_observation_age_seconds` | integer 1–3600 |
| `evaluation_window_seconds` | integer 1–3600 |
| `required_metric_families` | exact set `health,error,latency,security,business` |
| `health_min_basis_points` | 0–10000 |
| `error_max_basis_points` | 0–10000 |
| `latency_p95_max_ms` | positive integer |
| `security_critical_max` | constant `0` |
| `business_min_basis_points` | 0–10000 |
| `allowed_recovery_actions` | subset of `halt,decrease_exposure,restore_previous` |
| `plan_digest` | canonical digest of all preceding plan fields |

### `DeliveryPromotionV1`

| Field | Meaning |
| --- | --- |
| `schema_version`, `promotion_id`, `repository_id` | version and stable resource identity |
| `artifact` / `previous_signed_artifact` | new and exact restoration artifacts; repository must match and artifact digests must differ |
| `m8_profile_digest`, `m8_cohort_digest` | accepted exact profile/cohort bindings |
| `policy_digest`, `holdout_digest`, `runner_image_digest` | external policy/holdout/image bindings |
| `environment_set_digest` | exact authorized nonproduction resource set |
| `exposure_plan` | complete bounded plan |
| `requested_at`, `expires_at` | bounded validity window |
| `authority_envelope_digest`, `authority_verifier_id`, `authority_verified_at`, `authority_expires_at` | opaque external verification reference |
| `authority_scope` | constant `nonproduction_staged_delivery` |
| `authority_resource_digest` | canonical digest of all promotion resources and limits |
| `promotion_digest` | canonical digest of the complete promotion |

### `EnvironmentObservationV1`

| Field | Meaning |
| --- | --- |
| `schema_version`, `observation_id` | closed version and ID |
| `promotion_digest`, `artifact_digest`, `environment_set_digest`, `environment`, `exposure_basis_points`, `policy_digest` | exact evaluated context |
| `captured_at`, `window_started_at`, `window_ended_at` | complete ordered window |
| `health_basis_points`, `error_basis_points`, `latency_p95_ms`, `security_critical_count`, `business_basis_points` | five aggregate families |
| `sample_count` | positive bounded integer |
| `source_snapshot_digest` | opaque aggregate-source identity, not a body |
| `observation_digest` | canonical digest |

One decision accepts exactly one observation per required family snapshot. Duplicate context with different aggregate values is contradictory and denies; identical duplicate IDs are rejected as replay.

### `DeliveryDecisionV1`

Fields: `schema_version`, `decision_id`, `promotion_digest`, `artifact_digest`, `environment`, `exposure_basis_points`, `observation_set_digest`, `evaluation_time`, `outcome`, `reason_codes`, `next_environment`, `next_exposure_basis_points`, `decision_digest`. Outcome is one of `advance`, `hold`, `deny`, `needs_human`. Reason codes are sorted unique closed values. Production always produces `needs_human`, with no next environment/exposure.

### `RecoveryDecisionV1`

Fields: `schema_version`, `recovery_id`, `promotion_digest`, `failed_decision_digest`, `environment`, `current_exposure_basis_points`, `action`, `target_exposure_basis_points`, `restore_artifact_digest`, `reason_codes`, `decision_time`, `recovery_digest`. Action is one of `halt`, `decrease_exposure`, `restore_previous`. A decrease must select an earlier step from the same environment; restore digest must equal `previous_signed_artifact.artifact_digest`; halt has neither target. All actions must be pre-authorized by the plan.

### `DeliveryEvidenceV1`

Fields: `schema_version`, `evidence_id`, `sequence`, `promotion_digest`, `previous_evidence_digest`, `artifact_digest`, `environment`, `exposure_basis_points`, `observation_set_digest`, `delivery_decision_digest`, `recovery_decision_digest`, `dry_run_effect`, `recorded_at`, `reason_codes`, `evidence_digest`. Sequence starts at one, is contiguous and caps at 128. `dry_run_effect` is one of `none,entered_stage,changed_exposure,halted,restored,needs_human`; it never claims a real environment mutation.

## Deterministic evaluation

Validation runs in fixed order: contract shape → authority expiry/scope/resource binding → exact promotion/artifact/environment/exposure bindings → observation cardinality/duplicates → timestamp ordering/freshness → numeric finiteness/ranges → threshold gates. All applicable reason codes are collected, sorted and deduplicated; the same canonical inputs always yield the same decision digest.

Missing, stale, duplicate or contradictory observations always deny. Any health below minimum, error or latency above maximum, security critical count above zero, or business result below minimum denies. Passing preview/staging advances to the next environment at its first exposure. Passing canary advances to its next exposure; passing the last canary step yields `needs_human` for production. Production input always yields `needs_human` even if all metrics pass.

## Dry-run controller

The controller consumes a promotion, the complete current observation and the prior evidence chain. It validates chain continuity and expected current state, evaluates, optionally chooses a narrowing recovery, applies the effect only to an in-memory fake adapter, and appends one evidence record. The adapter exposes preview/staging/canary dry-run methods and recovery methods only. It deliberately has no production, network, shell, provider, credential, signing or connector method.

## Release and recovery boundary

Tasks 1–4 may be implemented and tested locally before factual M8 acceptance because their inputs are synthetic opaque identities and their outputs have no external effect. Source may be accepted or merged only after the factual accepted M8 restack, full route verification/reviews and external Trust CI on the exact PR SHA. Activation additionally needs externally verified signed inputs, a named authorized nonproduction environment and an exercised exact-prior-artifact recovery. Production remains a separate human operation outside this design.

## Non-goals

No real deployment, environment provisioning, workload routing, telemetry collection, signing, verification, secret handling, persistent store, network client, subprocess, system command, connector, production adapter, auto-merge, Trust CI publication or human approval workflow.
