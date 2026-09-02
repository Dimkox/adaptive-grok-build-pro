# Requirements — M8 earned autonomy provisional M4 bridge

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Parse only complete closed M8 values and the full exact M7 `4df2516` wire handoff.
- [ ] Recompute M7 bundle/outcome/cohort/aggregate/evaluation digests and predecessor equality chains; bind every M8 task/run/result head/human receipt to the corresponding M7 bundle/outcome.
- [ ] Bind repository, class, agent, validator, explicit provider mapping, model, prompt, policy, runner, holdout, authority ceiling and expiry into one canonical tuple digest without product-SHA or boolean authority claims.
- [ ] Require future durable M7 acceptance/currentness, >=30 distinct human acceptances, complete configured thresholds and >=20% audit with >=1 sample per represented UTC day.
- [ ] Recommend at most one gradual level and never beyond L2; every result authorizes no action.
- [ ] Atomically demote to L0/halted for every closed trigger and prevent stale/materially changed/expired profile reuse.

## Failure and edge cases

- Unknown/missing fields, wrong version, unsupported class/level, duplicate tasks, mixed tuples, unbounded metrics and invalid times fail closed.
- `blocked_pending_durable_lookup`, absent external acceptance/currentness, insufficient evidence or any threshold/audit failure blocks promotion.
- Opaque verification receipt digests are inputs from a future trusted boundary; repository data cannot verify or promote itself.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no key, secret, signer, verifier, credential, network or external-effect capability.
- Reliability: immutable values, deterministic canonical JSON and fixed demotion priority.
- Performance: <=10,000 tasks/wire items; bounded IDs, metrics, cost and latency.
- Forward integration: factual M7 restack deletes the temporary wire reader and replaces it with direct producer contracts plus durable lookups.
- Observability: fixed low-cardinality recommendation/demotion/gate outcomes with no PII.
