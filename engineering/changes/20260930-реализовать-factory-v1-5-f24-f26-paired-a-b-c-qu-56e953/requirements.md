# Requirements — Реализовать Factory v1.5 F24 F26 paired A/B/C qualification harness: frozen 12-case corpus, Pump Selector fixtures/oracle, behavior impact selector, immutable baseline, thresholds, budgets and deterministic tests

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Exactly twelve stable Pump Selector cases are loaded from a digest-bound, package-owned corpus.
- [ ] Wrong source document and wrong curve fail even when the response is structurally valid.
- [ ] Unknown head/flow/cost/token facts stay unknown and never become numeric zero.
- [ ] Declared supported units are normalized before domain comparison; unsupported units fail closed.
- [ ] A/B/C share corpus, oracle, snapshots, tools, model and budgets; only declared representation/backend factors may vary.
- [ ] Missing baseline, required case, attempt, cost coverage or provider identity prevents comparative pass.
- [ ] Critical domain/safety failure cannot be offset by latency or cost savings.
- [ ] Behavior-impact selection is deterministic and records changed paths/digests, affected capabilities and reason.

## Failure and edge cases

- Candidate attempts to change corpus/oracle/baseline/thresholds are rejected by digest and identity checks.
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
