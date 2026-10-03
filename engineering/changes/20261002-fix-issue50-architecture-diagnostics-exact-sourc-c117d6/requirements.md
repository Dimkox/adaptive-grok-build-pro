# Requirements — Fix issue50 architecture diagnostics: exact source locations, malformed path and line-skip rejection, bounded architecture input preflight in verifier.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- AC-001: source paths and schema/syntax failures identify the actual document and known physical line/column.
- AC-002: aliases, traversal, invalid Unicode path shape, symlinks, duplicate normalized paths, missing inputs and resource-bound violations fail closed.
- AC-003: architecture-inputs is mandatory for configured inputs and refusal prevents dependent expensive consumers; absent inputs and not-run checks remain explicit skips.
- AC-004: existing valid loading, digests, generated views and Git trust behavior remain compatible.

## Failure and edge cases

- Repeated bad literals are located by their semantic structural slot, never first textual match. Dangling symlinks count as present invalid inputs, and missing schemas cannot convert configured documents into an absence skip.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: reuse descriptor-relative no-follow reads and forbid raw path aliases before Path normalization.
- Reliability: one first blocking finding; no arbitrary YAML parsing or partial model acceptance.
- Performance: retain existing limits and use no recursive repository inventory during preflight.
- Observability: check status/summary/finding disclose executed, absent, refused and not-run conditions.
