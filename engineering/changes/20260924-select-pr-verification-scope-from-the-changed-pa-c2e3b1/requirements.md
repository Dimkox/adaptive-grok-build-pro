# Requirements — Select PR verification scope from the changed-path inventory (issue 205)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given a release-sync inventory of documentation, dated state, tracked package bytes and the lockstep state tests, when `grok_verify --mode pr` classifies it, then the `docs-state-focused` profile is selected and `coverage run -m unittest discover -s tests` is never executed.
- [x] Given the focused profile ran, when its report and receipt are read, then the profile name, reason code, every admitted path and each omitted check (`coverage`, `factory-postgres-exit`) are named there.
- [x] Given one executed-behavior, non-lockstep-test, schema, contract, architecture-model, Trust CI, factory, pilot, hook, config or tooling path added to an otherwise admissible inventory, when classification runs on the same tree, then full PR discovery is back on the critical path.
- [x] Given an identical documentation-only inventory, when the operator sets `--full-scope` or `GROK_VERIFY_FORCE_FULL=1`, then the full suite runs.
- [x] Given README and AGENTS.md, when the change lands, then the admitted path classes, the fail-closed rejections, the recorded evidence kind and the escape hatch are all documented.
- [x] Given the existing static-SEO-landing focused mode, when `--mode pr` runs, then no landing `verification_scope` is present in the PR report.

## Failure and edge cases

- Empty or unresolvable comparison inventory, absent route, untrusted status-preserving Git inventory, and a lockstep module missing from the checkout each keep the full PR suite; none of them narrows a check.
- Deleted, renamed, copied, unmerged or malformed Git file statuses are rejected even when every path string is allowlisted, so a source file cannot be moved behind a documentation name.
- Absolute, traversal, control-byte, backslash and non-string inventory entries are rejected as invalid paths before any classification.
- A change to `verification.py`, `verification_scope.py` or `scripts/grok_verify.py` is never admissible in the focused profile: the shortcut cannot certify its own modification.
- Editing a lockstep test is admissible because that test re-derives identity, dated state and package digests from the current tree; editing any other test is not, because an edited test can silence a check without touching a product statement.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted; governance checks still run in the focused profile.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: the focused profile does not refresh the full-suite coverage number. Accepted deliberately — an admitted inventory changes no executed product statement, so a fresh measurement would restate the last full run. `--full-scope` re-measures on demand.

## Non-functional requirements

- Security: scope selection is evidence-disclosure only and grants no merge authority; the App-owned exact-SHA Trust CI check is unchanged.
- Reliability: classification is deterministic from the changed-path inventory and its Git statuses, fail-closed on every ambiguity, and reproducible without network or provider access.
- Performance: measured baseline for the gated core suite on this checkout is 629 s serial under coverage; the focused lockstep trio is about 11 s, and the focused profile also skips the bounded 600 s factory PostgreSQL exit run.
- Observability: `docs_state_scope` in every PR/release report and receipt carries `profile`, `evidence_kind`, `reason_code`, admitted path lists, and the skipped-check list.
