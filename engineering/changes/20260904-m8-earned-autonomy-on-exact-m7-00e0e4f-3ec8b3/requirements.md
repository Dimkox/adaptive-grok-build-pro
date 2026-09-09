# Requirements — M8 earned autonomy on exact M7 00e0e4f

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] The M7 bridge parses actual M7 bundle, outcome, and cohort contracts, recomputes M7 aggregate/evaluation, and rejects any caller-supplied aggregate, eligibility, acceptance, or currentness field.
- [ ] Bundles are sorted and unique, map one-to-one to cohort outcomes, and bind exact M4 task/run, M5 result head, M7 outcome, human receipt, and M8 task evidence identities.
- [ ] The autonomy tuple binds repository, task class, M7 cohort key, explicit provider mapping, separate validator/provider digests, model, prompt, policy, runner, holdout, authority, L2 ceiling, and expiry.
- [ ] Eligibility requires at least 30 real accepted tasks, at least 20% accepted audit sampling on every represented UTC day, zero safety/authorization/duplicate/demotion facts, and bounded quality, cost, latency, time, receipts, and replay.
- [ ] Evaluation recommends at most one level above the current level and never above L2; every recommendation requires a separate activation and authorizes no external action.
- [ ] Expired tuples, replayed cohorts, stale task facts, halted profiles, missing M7 acceptance/currentness, or blocked M7 bundles fail closed at the deterministic reason code.
- [ ] Any supported demotion trigger selects the fixed highest-priority trigger and atomically yields an immutable halted L0 profile and non-operative decision.

## Failure and edge cases

- Duplicate or unordered task/run/head, bundle, or outcome identities fail closed; bundle-to-outcome cardinality is exactly one-to-one.
- Provider and validator identities cannot collapse or drift from the M7 cohort tuple.
- Cohort windows must be closed, timezone-aware, within tuple expiry, and contain every task observation strictly before expiry.
- Synthetic fixtures are algorithm evidence only and cannot satisfy factual acceptance/currentness or activation.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: existing deterministic-evidence, closed-contract, human-authority, no-external-action, and architecture-boundary rules.
- Canonical-example deviations and evidence: the canonical duplicate M7 wire is intentionally replaced by a thin bridge over the actual integrated M7 types and schema references.
- Intentional debt created, repaid, or accepted: durable acceptance/currentness lookup, real cohort evidence, activation, and runtime composition remain explicit later gates.

## Non-functional requirements

- Security: no caller-supplied eligibility/currentness, no automatic authority, separate provider/validator identities, and zero-tolerance safety gates.
- Reliability: closed immutable records, exact content digests, deterministic reason ordering, expiry, replay, and priority-ordered demotion.
- Performance: at most 10,000 tasks and no I/O or floating-point thresholds.
- Observability: profiles and recommendations expose bounded aggregates, exact tuple/cohort digests, one reason code, halt state, and explicit activation/external-action flags.
