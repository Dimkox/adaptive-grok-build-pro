# Requirements — Resolve issue #186 owner mapping and issue #36 exit-status disposition

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] Given audited commit `130ce4a42d9f9bbd1b56772d40b19ae530283205`, when the current tree and reachable history are searched with the recorded commands, then no repository-owned exit-status recorder is found.
- [x] Given the absent owner, when #186 is dispositioned, then the repository records “no local owner / no speculative fix” and maps #35/#36/#39/#48 without conflating their scopes.
- [x] Given #36 has no supplied upstream owner link, when this change completes, then it remains external/misrouted with no closure claim and an explicit residual blocker.
- [x] Given current Python and Trust CI result handling, when nonzero commands are characterized, then their exit codes remain preserved and no verifier or deployed Trust CI behavior changes.

## Failure and edge cases

- Failure/edge case: a future authoritative external owner link must start a separate change against that source; this package must not invent one.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: repository AGENTS.md external-ownership and Trust CI boundary rules.
- Canonical-example deviations and evidence: none; absence is supported by the four analysis reports and owner-mapping.md.
- Intentional debt created, repaid, or accepted: #36 remains blocked on external owner/path/reproduction evidence.

## Non-functional requirements

- Security: no secrets or external systems accessed.
- Reliability: no runtime behavior changed.
- Performance: no runtime behavior changed.
- Observability: exact commands, SHA, tree, and source paths are recorded.
