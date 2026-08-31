# Architecture — Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

The post-KILL group-presence probe treats a zombie as a live survivor and masks the already-classified bounded command error.

## Proposed behavior

Keep the existing session, TERM/KILL, bounded-wait, and leader-reap protocol. Only after KILL grace expires, classify the original PGID from bounded Linux procfs evidence: all observed `Z` members permit the original error; live or uncertain state fails closed.

## Components and boundaries

`workspace.py` remains inside `NODE-ISOLATED-RUNNER` / `TD-TRUST-CI-EXECUTION`; `test_workspace.py` supplies the regression boundary. No node, edge, secret, policy, or public contract changes.
`test_change_receipts.py` is test-only: it continues to prove architecture binding consistency and does not change the active-route architecture gate.

## Data flow

Bounded command failure → TERM grace → KILL grace → bounded read-only PGID classification → original error or controlled containment error → leader reap.

## API and event contracts

Unchanged: no OpenAPI, event, schema, queue, database, policy, holdout, runner image, or deployment change.

## Bitrix-specific impact

- Not applicable; Bitrix is outside this route.

## Decisions

Treat only positively parsed zombie-only remainder as cleanup success; uncertainty is containment failure.

## Risks and mitigations

Restricted or malformed procfs cannot weaken containment because it fails closed; finite entry/read bounds prevent the classifier from becoming a host-wide unbounded scan.
