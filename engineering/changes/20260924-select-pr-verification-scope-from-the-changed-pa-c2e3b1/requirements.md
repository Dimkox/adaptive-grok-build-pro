# Requirements — Select PR verification scope from the changed-path inventory (issue 205)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given a release-sync inventory of documentation, dated state, tracked package bytes and the admitted lockstep/binding state tests, when `grok_verify --mode pr` classifies it, then the `docs-state-focused` profile is selected and `coverage run -m unittest discover -s tests` is never executed.
- [x] Given the focused profile ran, when its report and receipt are read, then the profile name, reason code, every admitted path and each omitted check (the replaced full-discovery runner `python-unittest` — or `pytest` in an install whose runner is pytest —, `coverage`, `factory-postgres-exit`) are named there.
- [x] Given one executed-behavior, non-admitted-test, schema, contract, architecture-model, Trust CI, factory, pilot, hook, config or tooling path added to an otherwise admissible inventory, when classification runs on the same tree, then full PR discovery is back on the critical path.
- [x] Given prose-looking content that is executed or byte-pinned elsewhere — `docs/bitrix-local-AGENTS.md` (installed verbatim as `local/AGENTS.md` into every consumer Bitrix install) and any `**/evidence/historical-*` bundle (pinned to a literal sha256 by `tests/test_history.py`) — when it is the only non-standard path in an otherwise admissible inventory, then it is rejected by its own reason code (`shipped-executed-content`, `immutable-historical-evidence`) rather than by directory membership.
- [x] Given admitted content whose machine binding lives in a test module (README's Workflow-sources table, a delivered package's route record), when the focused profile runs, then that binding module is one of the modules the profile itself executes, so no admitted path is verified by a check that did not run.
- [x] Given `verify()` rather than the pure classifier, when a real repository is classified in `pr` mode, then the report's `docs_state_scope.profile`, the executed checks and the full-discovery marker agree: documentation-only inventory selects and runs the focused profile; one committed source change, an untrusted status channel, or an admitted module missing from the checkout each puts full discovery back.
- [x] Given an identical documentation-only inventory, when the operator sets `--full-scope` or `GROK_VERIFY_FORCE_FULL=1`, then the full suite runs.
- [x] Given README and AGENTS.md, when the change lands, then the admitted content roles, the fail-closed rejections, the recorded evidence kind and the escape hatch are all documented.
- [x] Given the existing static-SEO-landing focused mode, when `--mode pr` runs, then no landing `verification_scope` is present in the PR report.

## Failure and edge cases

- Empty or unresolvable comparison inventory, absent route, an untrusted *or unevaluated* status-preserving Git inventory (`status_inventory_trusted` must be positively `True`), and an admitted module missing from the checkout each keep the full PR suite; none of them narrows a check.
- Deleted, renamed, copied, unmerged or malformed Git file statuses are rejected even when every path string is allowlisted, so a source file cannot be moved behind a documentation name. This is proven on a repository whose *primary* inventory is rename-collapsed (one admitted path) and whose side channel still reports the `D`.
- Untracked paths are covered by that same channel: the side channel collects `ls-files --others --exclude-standard`, so `'??'` is a reachable status rather than a dead entry in the safe set.
- Absolute, traversal, control-byte, backslash and non-string inventory entries are rejected as invalid paths before any classification, and `_classify_path` refuses an unnormalized path (`packages/../../etc/passwd`) even if a future caller forgets that validator, because the allowlist is matched with string prefixes.
- A suffix-glued sibling of an admitted name (`engineering/decisions.md.bak`, `docs/package-status.md.bak`) is not admitted: every documentation prefix is directory-shaped and every other admitted file is named exactly.
- A change to `verification.py`, `verification_scope.py`, `util.py` or `scripts/grok_verify.py` is never admissible in the focused profile: the shortcut cannot certify its own modification.
- Editing one of the five admitted test modules is admissible because each re-derives admitted content (identity, dated state, package bytes, README's Workflow-sources table, a delivered route record); editing any other test reports `test-suite-change` and owes the full suite, because an edited test can silence a check without touching a product statement.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none asserted; governance checks still run in the focused profile.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: the focused profile does not refresh the full-suite coverage number. Accepted deliberately — an admitted inventory changes no executed product statement, so a fresh measurement would restate the last full run. `--full-scope` re-measures on demand.

## Non-functional requirements

- Security: scope selection is evidence-disclosure only and grants no merge authority; the App-owned exact-SHA Trust CI check is unchanged and still runs the whole suite.
- Reliability: classification is deterministic from the changed-path inventory and its Git statuses, fail-closed on every ambiguity, and reproducible without network or provider access. An empty focused-target list is a failed check, never a green zero-test `python -m unittest` run.
- Performance: measured baseline for the gated core suite on this checkout is 629 s serial under coverage; the five admitted modules run in about 14 s, and the focused profile also skips the bounded 600 s factory PostgreSQL exit run.
- Observability: `docs_state_scope` in every PR/release report and receipt carries `profile`, `evidence_kind`, `reason_code`, admitted path lists, and the full skipped-check list including the replaced discovery runner.
