# Requirements — Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] AC-001: repository identity, HEAD, changed-file inventory and tree
  fingerprint for root A remain bound to A when ambient `GIT_DIR`,
  `GIT_WORK_TREE`, or both point to repository B.
- [ ] AC-002: a branch/tag push is denied before approval lookup when either
  inherited selector is present, including an empty-string value.
- [ ] AC-003: denial names only `GIT_DIR`/`GIT_WORK_TREE`, explains that the
  selector must be unset, and does not disclose its value.
- [ ] AC-004: a same-HEAD/same-tree foreign repository with an attacker
  `pushurl` cannot turn a valid grant into an allow decision; no push occurs in
  the test.
- [ ] AC-005: clean-environment matching grants still allow their exact action,
  while changed HEAD/tree, action mismatch, expiry and foreign repository
  identity remain denied.
- [ ] AC-006: direct hook integration returns the same fail-closed result as the
  core policy path.

## Failure and edge cases

- Treat variable presence as ambiguous even when its value is empty or resolves
  back to the same repository.
- Scrubbing internal probes without denying the eventual shell action is
  forbidden because it creates split-brain authorization.
- Do not include selector values or foreign paths in receipts, denials or logs.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none beyond the active repository policy and human-gate
  contract.
- Canonical-example deviations and evidence: none; the existing local delegated
  grant boundary remains non-authoritative for Trust CI.
- Intentional debt created, repaid, or accepted: root-local `pushurl` mutation
  remains an explicitly bounded residual for a later issue.

## Non-functional requirements

- Security: authorization identity and execution identity cannot diverge through
  inherited repository selectors.
- Reliability: all Git probe helpers use the same sanitized environment rule.
- Performance: no new subprocesses or network calls.
- Observability: denial is actionable and secret-safe; regression tests expose
  the selected variable name and fail-closed outcome.
