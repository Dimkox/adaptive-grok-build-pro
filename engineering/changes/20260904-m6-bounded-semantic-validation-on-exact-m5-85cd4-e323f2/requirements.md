# Requirements — M6 bounded semantic validation on exact M5 85cd434

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: Seven closed schemas accept only bounded canonical semantic subjects, bindings, inputs, findings, coverage, verdicts, and repair directives bound to one exact M5 result and requirement set.
- [ ] AC-002: Deterministic adjudication is permutation-invariant; contradiction, unsupported proof, authority/security findings, duplicate correlation, or unrepairable evidence yields `needs_human`; incomplete repairable evidence yields `repair`; exact supported coverage yields `pass`.
- [ ] AC-003: Validators are independent of the original writer and have repository-read plus semantic-validation authority only; coordinator, validator, and adjudicator capabilities are mutually disjoint and have no direct table DML or application-write authority.
- [ ] AC-004: Semantic persistence is append-only and exact-replay safe across subjects, assignments, evidence, verdicts, directives, repair proposals, child bindings, escalations, recovery facts, and metrics.
- [ ] AC-005: Repair cycles one through three preserve exact lineage, writer, context freshness, risk, diff and budget bounds; cycle four or any stale/recurrent/policy-invalid attempt records `needs_human` and creates no child.
- [ ] AC-006: Migration `018` applies transactionally after byte-identical migrations `001`-`017`, preserves existing M5 rows and digests, and rolls back to schema 17 on failure.
- [ ] AC-007: The six separately contracted semantic operations are additive to the current M4/M5 surfaces, require authenticated repository-scoped semantic authority, and do not expose a live provider, repair-write, network, credential, or production path.

## Failure and edge cases

- Changed subject or evidence digests invalidate prior derived artifacts.
- Conflicting replay, cross-repository access, writer/validator identity overlap, stale M5 lineage, duplicate verdicts, and broker identity mismatch fail closed.
- Empty or oversized requirement/evidence collections and a fourth correction cycle cannot produce a pass or child proposal.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: current architecture contract, data ownership, API compatibility, AI trust-boundary, and migration immutability rules.
- Canonical-example deviations and evidence: canonical migration filename `014` becomes `018`; SQL bytes remain unchanged because M5 owns `014`-`017`.
- Intentional debt created, repaid, or accepted: live provider and operational isolation remain outside this source checkpoint; no acceptance claim is made.

## Non-functional requirements

- Security: authority is derived only from persisted M5 and trusted actor/capability facts; provider output is data.
- Reliability: deterministic canonical digests, append-only facts, exact replay, and explicit escalation preserve restart-safe outcomes.
- Performance: bounded arrays and indexed exact-digest lookups; no unbounded scan or retry loop.
- Observability: fixed low-cardinality semantic publication, verdict, repair, escalation, and recovery counters.
