# Requirements — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Exactly four Pump Selector, four factory, and four cross-component/rule-conflict cases emit exact corpus, baseline, closed-oracle and profile identities for out-of-process qualification; local code and caller objects can never emit pass.
- [ ] Wrong source document and wrong curve fail even when the response is structurally valid.
- [ ] Unknown head/flow/cost/token facts stay unknown and never become numeric zero.
- [ ] Declared supported units are normalized before domain comparison; unsupported units fail closed.
- [ ] A/B/C share corpus, oracle, snapshots, tools, model and budgets; only declared representation/backend factors may vary.
- [ ] Missing baseline, required case, attempt, cost coverage or provider identity prevents comparative pass.
- [ ] Critical domain/safety failure cannot be offset by latency or cost savings.
- [ ] Qualification requires strict improvement in the predeclared benefit metric and reports unique/total/reread bytes, preparation/update cost, cold/warm cache totals, corrections, criterion coverage, and p50/p95 latency.
- [ ] Prompt, context, model, tools, tool responses, resources and sanitizer identities are bound and checked on every attempt.
- [ ] Behavior-impact selection is deterministic and records changed paths/digests, affected capabilities and reason.
- [ ] Selector recomputes SHA-256 from supplied before/after bytes; a claimed digest or typo label cannot suppress F26.
- [ ] BB/native observers reuse the closed comparator profile and emit candidate evidence only; BB remains disabled and externally unqualified.

## Failure and edge cases

- Candidate success is only `ready_for_external_qualification`; any failed/blocked gate is `not_qualified`. External Trust CI/holdout is recorded `NOT_RUN`, never simulated locally.
- Factory and cross-component domain results use closed exact schemas; extra fields fail.
- Every declared negative control is executed and must be killed by its expected oracle failure.
- Infra failure is distinct from property failure; neither counts as pass.
- A proven documentation typo selects deterministic checks without a live provider run.
- Unknown impact selects the mandatory bounded set, never automatic skip.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: synthetic fixtures only; no provider, production or external write authority.
- Reliability: closed contracts, deterministic ordering and fail-closed completeness gates.
- Performance: finite attempts, latency and cost ceilings fixed before evaluation.
- Observability: every attempt and gate result is included in a canonical immutable report.
