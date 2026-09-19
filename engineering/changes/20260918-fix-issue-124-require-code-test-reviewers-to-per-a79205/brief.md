# Fix issue #124: require code/test reviewers to perform mutation testing in a private scratch copy outside the reviewed worktree, preserve the reviewed tree as read-only, and report which claims were executed with commands/output plus reviewed-tree-modified:no and scratch path. Update reviewer briefs/templates and tests.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-issue-124-require-code-test-reviewers-to-per-a79205`
Created: 2026-09-18T17:30:28+00:00
Risk: medium
Complexity: standard
Domains: frontend, api

## Problem

Fix issue #124: require code/test reviewers to perform mutation testing in a private scratch copy outside the reviewed worktree, preserve the reviewed tree as read-only, and report which claims were executed with commands/output plus reviewed-tree-modified:no and scratch path. Update reviewer briefs/templates and tests.

## Outcome

Reviewers can perform mutation/adversarial checks without occupying or altering the implementation worktree. Each review report identifies the exact source snapshot, private scratch directory, executed claims/commands/results, and states `reviewed tree modified: no`.

## Scope

### In scope

- Make code/test reviewer briefs require read-only access to the reviewed worktree and private scratch copies for all mutations and test runs that modify source.
- Bind scratch evidence to the current candidate HEAD and dirty-tree fingerprint; detect candidate changes during/after review and mark results stale.
- Define a required report section with scratch path, source identity, actual commands/output, and explicit no-modification statement.
- Pin reviewer sandbox/report instructions with structural tests while preserving the existing read-only reviewer sandbox.

### Out of scope

- Add a mutation-test runner, new receipt type, or source mutation executor.
- Change reviewer scheduling/locking unless analysis shows read-only instructions and snapshot checks cannot close the race.
- Replace existing role-specific review criteria or require speculative mutant quotas.

## Constraints

- Backward compatibility: preserve current review verdicts/receipt kinds and each role's distinct review checklist.
- Data/privacy:
- Performance:
- Operational:
