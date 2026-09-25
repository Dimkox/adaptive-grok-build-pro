# Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260925-fix-issue-227-inherited-git-dir-or-git-work-tree-177f5d`
Created: 2026-09-25T07:57:57+00:00
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

Fix issue 227: inherited GIT_DIR or GIT_WORK_TREE can redirect repository identity and let a valid local grant authorize git push to a foreign pushurl. Add root-bound Git probes and explicit fail-closed denial. Never execute git push or access the network.

## Outcome

Delegated local grants are evaluated against the explicit repository root, never
against ambient Git repository selectors. A production Git push is denied before
grant consumption whenever inherited `GIT_DIR` or `GIT_WORK_TREE` is present, so
policy cannot approve one repository while the shell would push another.

## Scope

### In scope

- Make every internal read-only Git probe used by repository identity, HEAD and
  tree fingerprint ignore ambient `GIT_DIR` and `GIT_WORK_TREE`.
- Deny branch/tag push policy decisions when either selector is present in the
  inherited environment, even when empty or when a matching grant exists.
- Add offline regression coverage using disposable repositories; no push is run.
- Preserve grant schema v2, the `has_valid_approval(...) -> bool` API and current
  clean-environment allow/deny behavior.

### Out of scope

- GitHub writes, branch push, merge, release, deployment and network access.
- Daybreak Program or any other unavailable external program/infrastructure.
- Root-local `remote.origin.pushurl` changes without ambient selectors; that is
  a separate residual risk and follow-up contour.
- Broad filtering of unrelated `GIT_*` variables or refactoring command parsing.

## Constraints

- Backward compatibility: retain grant schema v2, legacy binding-field reads,
  action/resource/TTL checks and the public boolean approval API.
- Data/privacy: denial messages name selector variables only; never print their
  values, filesystem paths, credentials or remote URL secrets.
- Performance: selector scrubbing is a bounded environment copy on existing Git
  probes; no additional network or long-running operation is introduced.
- Operational: local implementation and verification only. External operations
  remain separately delegated, and Trust CI remains the merge authority.
