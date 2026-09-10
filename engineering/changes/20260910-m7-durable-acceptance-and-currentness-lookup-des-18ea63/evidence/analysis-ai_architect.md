# AI architecture: M7 durable lookup and M8 preflight

Route `18ea639b9d02`; base `64378d2`. Read-only design analysis. Scope/design approval is pending; no product edit, test run, migration, or external action is implied.

## Boundary and recommended shape

Retain `ReadyForPrBundleV1.status=blocked_pending_durable_lookup`, both false `M7AutonomyBridgeV1` availability properties, existing `evaluate_autonomy` behavior, M9 unavailability, and `LEVELS=(L0,L1,L2)`. The blocked status participates in the bundle digest. Additive persisted observations and an M8 preflight result must not reinterpret that V1 digest or replace its gates with a success Boolean.

Use separate tagged facts for acceptance resolution, acceptance decision, currentness resolution, and qualification coverage. A resolved rejection is an observed negative decision, not missing evidence; a resolved acceptance is not a currentness pass. A successful preflight lookup means specified evidence was retrieved and bound to the requested subject/context. Its invariant outputs remain `m8_qualification=not_evaluated` and `authority_effect=none`.

Bind the lookup to repository, immutable task/run/fence and execution generation, exact result SHA, canonical bundle digest, semantic result, and the supplied cohort/profile subject where present. Lookup existing canonical producer records instead of trusting repeated caller fields. A completed run may have no active lease. Use immutable completion bindings and detect superseded execution generations separately.

## Acceptance and evidence rules

Keep intake acceptance, technical validation, observed PR merge, business task acceptance, and signed security approval distinct. GitHub actor type, merge state, passing tests, an M0 intake observation, or a local report cannot establish human business acceptance. A human decision must bind the exact delivered subject and have an authenticated independent producer; its digest proves body identity only, not source trust.

The deployment-owned acceptance producer and its observation capability are an explicit design decision still to settle. Until configured and independently authenticated, return acceptance unavailable. The agent environment must never generate, read, request, submit, or emulate human approval private keys. Storing imported claims in PostgreSQL does not authenticate them; keep them outside the trusted acceptance path.

Persist immutable source identity/body digest/decision timestamp/observation timestamp, with explicit revocation or supersession lineage. Identical source replay is idempotent; the same identity with a different body is an integrity conflict. A later rejection or withdrawal must prevent selection of an older favorable decision. A later code/profile change does not erase historical acceptance, but makes that acceptance unsuitable for the changed qualification subject.

Do not fabricate a complete `ShadowOutcomeV1` to register acceptance. That V1 requires quality, repair, budget, latency, review-time, and safety facts which may be unknown. A separate acceptance observation may be durable while outcome/profile coverage remains incomplete; the preflight can show resolved acceptance together with missing outcome bindings. Only a later fully bound qualification contract may consume complete factual M7 outcomes.

## Profile, currentness, and unknown measurements

Exact profile coverage means the complete `AutonomyTupleV1` binding: repository and task/change classes; M7 cohort/provider mapping; agent, validator, provider, model, prompt, policy, runner, holdout, authority digests; ceiling and expiry. Changed revisions create separate subjects. Never recover unknown historical fields from present-day configuration or coalesce distinct profile tuples by repository/model label.

The current supported task class is only `low_risk_text_only`. Durable acceptance of another class remains useful delivery evidence and must remain visible, while preflight reports that class as unsupported for existing M8 qualification. An incomplete profile lists missing fields and cannot acquire a synthetic tuple digest. Profile completeness is coverage, not proof of trust or qualification.

Currentness is a bounded observation relative to exact repository/PR/base/head, authenticated App-owned policy-epoch check provenance, deployed policy/holdout context, revocation state, and trusted evaluation time. An old signed success can remain authentic while becoming stale. Caller-selected time, imported success flags, matching head alone, or missing attestation fields cannot prove currentness. If independent current-context observation is absent, say unavailable; never infer it from a saved envelope.

Unknown interventions, repair, rollback, cost, or latency remain null. Preserve existing history coverage states `unknown`, `partial`, and `complete`; partial counts are lower bounds and complete sessions require sourced start/end/event coverage. No measured sessions means a null autonomy/intervention rate, not zero. Unknown metrics must not prevent storage of an independently authenticated acceptance fact, and must prevent claims that a complete qualifying outcome was established.

## What this slice closes

The slice supplies restart-safe retrieval of immutable producer bindings, separately sourced acceptance/currentness observations, replay protection, and explicit missing/stale/conflicting evidence diagnostics. It makes the next cohort work inspectable and avoids repeated reconstruction from loose reports. With sources unconfigured, fail-closed unavailable remains the truthful operational result.

It does not supply a live collector, a trusted acceptance integration, complete operator-event telemetry, real qualification cohorts, promotion, activation, merge permission, publication, or an L3/L4/L5 contract. Existing M7/M8 sample, observation/baseline, audit, quality, budget, latency, safety, and containment requirements remain for a later approved qualification milestone. Historical records may contribute only when their actual exact bindings and measurements can be established.

## Focused adversarial checks for the later implementation

- Resolved acceptance plus missing metrics/profile returns useful partial preflight coverage without constructing a qualifying outcome.
- Rejection, withdrawal, source revocation, conflicting replay, wrong result SHA, changed base/policy/holdout, and stale generation cannot resolve to a favorable current result.
- Completed-run lookup survives lease clearing and process/database restart, while missing capabilities or database availability return explicit unavailable.
- Imported complete metadata, caller acceptance flags, synthetic metrics, and source digests without trusted origin cannot gain qualification or authority.
- Complete exact evidence still leaves all V1 blocked/false semantics, L2 ceiling, and M9 behavior unchanged.

Memory fact: durable acceptance and currentness are independently resolved observations; incomplete outcome/profile/intervention coverage must stay explicit. The first additive M8 preflight closes evidence retrieval and binding gaps while leaving every existing qualification and authority gate intact.
