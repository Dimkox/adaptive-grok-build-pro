# Requirements — Publish unverified transport branch for the assembled 2.1.0 release candidate; no merge tag or release

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given the exact candidate, when the full PR verifier runs, then every selected check passes and records a fingerprint-bound receipt.
- [ ] Given U4 is excluded, when the release inventory is reviewed, then no macOS implementation or claim is required.
- [ ] Given U5/U6 are not live-qualified, when their code is exercised, then it remains observation-only, deterministic offline, default-off and fail-closed.
- [ ] Given existing dirty worktrees, when the PR is delivered, then none is reset, deleted or silently merged.
- [ ] Given the candidate branch, when delivery occurs, then a PR is opened without merge, tag or GitHub Release publication.

## Failure and edge cases

- Missing exact-head checks, stale receipts, migration identity drift, misleading qualification claims, package mismatch and dirty-tree mutation are release blockers.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security: no secrets, provider activation, production mutation or bypass of App-owned Trust CI.
- Reliability: restart/migration checks remain selected; rollback is disable/forward-fix with persisted data preserved.
- Performance: use the measured 28-CPU capacity without oversubscribing test workers.
- Observability: bind receipts and external check status to the exact candidate SHA.
