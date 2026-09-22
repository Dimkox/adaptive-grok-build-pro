# Requirements — Consolidate repository-owned remaining issue fixes into one bounded batch from current main, preserve external blockers, run one final PR verification and prepare one successor PR

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

## Failure and edge cases

- 

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:

## Bounded source-owned result

- [x] The checked-in Trust CI policy example is marked `illustrative-example-only`; deployed policy remains external.
- [x] Runtime documentation distinguishes operator-attested provider probes from durable artifact jobs.
- [x] Issues whose source seam is absent (#39 and #48) remain external findings and are not closed by a fabricated patch.
