# Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260831-fix-trust-ci-bounded-workspace-process-cleanup-i-fa3ae6`
Created: 2026-08-31T14:21:40+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Fix Trust CI bounded workspace process cleanup in the immutable read-only runner: zombie-only descendants after SIGKILL must not mask the original stdout/stderr/timeout failure, while live or uncertain survivors remain fail-closed. Deliver as an isolated stacked Trust-CI-only bugfix on M2 with regression tests.

## Outcome

The immutable, read-only Trust CI runner reports the useful stdout/stderr/timeout failure after verified zombie-only cleanup, while a live or unknown process remains a fail-closed workspace error.

## Scope

### In scope

- `trust-ci/src/adaptive_trust_ci/workspace.py` and `trust-ci/tests/test_workspace.py`.
- Test-only stabilization in `tests/test_change_receipts.py` for frozen-adoption binding evidence; it does not alter architecture evaluation or policy.
- Active change-package design, test, rollback, and evidence records.

### Out of scope

- Deployed Trust CI policy, holdout, runner images, services, keys, approvals, and external systems.
- Public API/event/schema, M2 architecture authority, and non-Trust-CI production paths.

## Constraints

- Backward compatibility: existing bounded error strings and direct leader-reap behavior remain stable.
- Data/privacy: do not log or persist PIDs, process listings, command output, or environment data.
- Performance: cleanup and procfs classification are finite and bounded.
- Operational: no deployment or external write is authorized.
