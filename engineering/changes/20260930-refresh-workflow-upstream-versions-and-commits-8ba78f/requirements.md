# Requirements — Refresh workflow upstream versions and commits

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Config and README agree on stable tag/version, peeled 40-hex commit, observed main 40-hex SHA, and 2026-09-30 observation date.
- [x] Supported stable pins are Superpowers 6.4.2, BMAD 6.12.0, and Spec Kit 1.0.13.
- [x] Named tests parse exact-revision upstream-shaped samples and preserve old-format parsing.
- [x] BMAD main remains an observation, not a fabricated semver release.
- [x] Imported artifacts remain bounded advisory candidates with no authority effect.

## Failure and edge cases

- Superpowers plan pointers are not followed; missing referenced specs do not grant authority.
- BMAD main ticket shapes without native task rows load without inferred tasks or terminal status.
- The existing 32-character source-version bound remains intact; exact commits live in provenance.

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
