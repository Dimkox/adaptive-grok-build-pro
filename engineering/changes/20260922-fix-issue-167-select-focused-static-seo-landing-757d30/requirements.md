# Requirements — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given a changed-file inventory containing files only below one directory matching `side-projects/seo-landings/<landing>/**`, plus one explicitly named focused test matching the implemented focused-test contract, when focused mode is run, then it selects `static-seo-landing` and runs that test with bounded diff and source-stability checks.
- [x] Given a second landing directory, a second focused test, or no focused test, when focused mode classifies the inventory, then it fails closed with `full-pr` classification and does not run a landing contract.
- [x] Given any mixed, unknown, invalid, deleted, renamed, copied, showcase, SEO-skill, runtime, contract, Trust CI, package, architecture, or workflow path, when focused mode classifies the inventory, then it fails closed; the operator must run full `--mode pr`.
- [x] Given any invocation of `--mode pr`, including an otherwise eligible landing-only inventory, when verification runs, then it retains the full PR path and never silently downgrades to focused mode.
- [x] Given valid focused workflow metadata, when the task graph validates a verification command, then only the exact focused command (without arbitrary extra flags) is allowlisted.
- [x] The App-owned exact-SHA `adaptive-trust-ci/verified@<policy-sha12>` check remains the merge authority; local focused evidence never substitutes for it.

## Failure and edge cases

- Empty, malformed, unresolved, or ambiguous route/PR range inventory: fail closed.
- Multiple landing directories cannot be associated safely with one focused test: fail closed.
- Change-package bookkeeping may be ignored as workflow evidence only; it does not expand product scope.
- Git status/rename/copy provenance must be trusted for focused classification; missing, malformed, deleted, renamed, or copied status records fail closed before contract execution.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: `AGENTS.md` focused static scope and independent Trust CI authority; `.agents/skills/adaptive-delivery/SKILL.md` focused-mode routing rule.
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no trust boundary or secret handling changes; unknown paths are never treated as safe.
- Reliability: source-stability and Git range integrity remain required in focused mode.
- Performance: no root suite, architecture, governance, factory, or PostgreSQL checks run in focused mode.
- Observability: JSON output reports mode, classification, exact checked files, focused test, skipped broad checks, and status.
