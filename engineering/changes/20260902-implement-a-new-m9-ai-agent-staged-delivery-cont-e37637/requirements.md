# Requirements — M9 Staged Delivery and Recovery

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Contract detail is frozen in the approved [design](../../../docs/superpowers/specs/2026-09-02-m9-staged-delivery-recovery-design.md).

## Acceptance criteria

- [x] `AC-001`: Task 1 implements seven closed frozen V1 record shapes, canonical digests and exact bindings with no cryptographic or external capability.
- [x] `AC-002`: Task 2 implements deterministic fail-closed metric completeness, freshness, consistency and threshold semantics.
- [x] `AC-003`: Tasks 3–4 enforce recovery as a strict subset of the pre-authorized promotion and keep production human-owned.
- [x] `AC-004`: M4→M9 connectivity, blocker owners, deadline, release and rollback are explicit.
- [x] `AC-005`: Tasks 1–4 are authorized as separate strict-TDD commits using only synthetic opaque exact identities and pure local behavior.
- [x] Successor correction removes the two caller-supplied M8 digest claims and binds a typed provisional M8 tuple/cohort/profile/recommendation handoff pinned to `2cee9b93c161b6c76f4fee877e6d19eacee5a271`.

Completed checkboxes prove only the named local source/documentation requirement. They never establish route receipts, accepted M8 evidence, signed inputs, an environment, recovery proof, activation, release or deployment.

## Failure and edge cases

- Reject non-canonical exact SHA/digest forms, unknown fields, duplicate observations, nonfinite numeric values, inverted thresholds and exposure outside the pre-authorized plan.
- Deny on any missing required metric family, observation older than the plan freshness bound, disagreement between repeated bindings, or observation captured after its evaluation deadline.
- Treat any authority envelope as opaque external evidence. Local source validates only bounded shape, expiry and exact resource/scope bindings; it never parses signature bytes or claims cryptographic verification.
- A failed preview, staging or bounded canary evaluation can only halt, decrease exposure within the same environment, or restore the exact `previous_signed_artifact` from the promotion.
- No recovery decision may advance environment, increase exposure, replace policy/cohort/resource bindings, or name a new artifact.
- Every recovery effect carries exactly its one matching closed recovery reason; mixed recovery reasons are invalid evidence.
- Every recovery effect also requires a non-recovery denial reason and forbids `thresholds_passed`.
- The controller accepts only the exact bounded fake-adapter type, binds the reviewed original implementation, and fails closed on instance replacement, subclassing or changed class surfaces.
- The entire evaluate/apply/append section is serialized; concurrent replay can append and apply at most once.
- Observation sequences are capped at 128 before bounded indexed materialization; generators and non-sequences are rejected without consumption.
- Non-empty prior evidence is rejected until Task 5 supplies a trusted checkpoint or complete independently witnessed observation/decision/recovery inputs.
- No effect or evidence is recorded once promotion/current-artifact authority expires; restore also rechecks prior-artifact authority at `recorded_at`.
- Reaching production returns `needs_human`; no adapter method exists for production mutation.
- Reject a changed repository/policy/holdout/runner or any broken provider-mapping/validator/provider, tuple, cohort, profile or recommendation equality chain.
- Recompute accepted/audit/quality/failure/cost/p95/demotion profile aggregates from linked cohort tasks and M7 outcomes; a caller-rehashed aggregate is not producer evidence.
- Reject expired/not-yet-current evidence, halted/demoted profiles and blocked recommendations. Current non-halted L0/L1/L2 profiles remain within the M8 ceiling when their exact recommendation is eligible.

## API/event compatibility

There is no HTTP, webhook, queue or external event in this slice. The future Python API consists of immutable record constructors plus pure evaluator/controller functions. V1 is closed; any field or meaning change requires V2. Evidence represents a completed dry-run transition, never a command to an external environment.

## Authentication and replay

- Authentication and signing happen outside M9. The only accepted representation is a bounded opaque externally verified envelope reference bound to exact digest, verifier identity, verified/expiry timestamps, scope and resource digest.
- `promotion_id`, promotion digest and evidence sequence make in-process re-evaluation idempotent. The controller rejects repeated observation sets and serializes concurrent identical calls; digest-only restart/import is disabled because it has no trusted witness.
- There are no retries in the pure core. A caller may submit a fresh complete observation set, producing a new decision/evidence chain without mutating history.

## AI and tenant boundaries

No model, prompt, retrieval, embedding, vector store or untrusted text participates in evaluation. M8 profile identity binds exact model/prompt/tool/policy context by digest only. Repository and environment identifiers are bounded tenant/resource keys and cannot broaden from the promotion.

## Non-functional requirements

- Security: no key material, credentials, network, process execution or production capability; closed enums and bounded ASCII identifiers. Private slots are only an ordinary in-process mutation defense, not an OS isolation boundary.
- Reliability: pure deterministic evaluation, canonical digests, lock-serialized append-only bounded evidence, disabled unwitnessed restart and explicit stale/contradictory denial.
- Performance: fixed maximum four environment stages, five metric families, sixteen exposure steps, 128 observations, 128 evidence records and 128 fake effects per dry-run.
- Observability: closed counters for decisions/reasons and aggregate observation ages only; never raw bodies, repository source, prompt/reasoning, PII or secrets.

## Source-only execution and blocked exit facts

Tasks 1–4 may use synthetic typed identities in local tests. The temporary M8 boundary always reports `durable_currentness_available=False`; acceptance, Task 5 integration, activation or release cannot claim an exit until all applicable facts are present: accepted M4→M8 exact predecessor chain, server-derived current M8 profile/cohort, external signed artifact/SBOM/provenance and authority envelopes, named nonproduction environment authorization, a trusted clock, a trusted restart/checkpoint witness, and exercised restore of the exact prior signed artifact. All factual rows remain `BLOCKED` in [`ledger.md`](ledger.md).
