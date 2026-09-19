# Fix GitHub issue #122: correct policy.example.json/runbook language so it clearly distinguishes illustrative approval scopes from deployed Trust CI policy and identifies where the active policy epoch is observed. Do not change deployed policy or Trust CI.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260918-fix-github-issue-122-correct-policy-example-json-d4766a`
Created: 2026-09-18T19:50:38+00:00
Risk: medium
Complexity: standard
Domains: frontend, api

## Problem

`trust-ci/config/policy.example.json` contains approval globs that can be mistaken for the active server policy. The rollout guide copies it into a runtime path without an adjacent caveat, while `trust-ci/README.md` already describes a safe authenticated policy handoff and `/health/ready` digest comparison. The dated activation report contains 2026-08-24 values that must not be treated as current.

## Outcome

Operators can distinguish sample configuration and dated observations from live Trust CI facts, and can follow the documented authenticated path to verify the deployed policy epoch and exact GitHub App check for a SHA.

## Scope

### In scope

- Clarify in the rollout instructions that `policy.example.json` is illustrative and does not prove active deployed approval scopes.
- Link the copy/deploy instructions to the existing authenticated deployed-policy handoff and normalized `/health/ready` `policy_digest` verification procedure.
- Label `trust-ci-activation-report.md` as a dated historical snapshot, not current deployment state.
- Add a structural documentation regression test.

### Out of scope

- Changing `policy.example.json` approval globs, Trust CI source behavior, deployed policy, holdout, trust store, branch protection, or external state.
- Claiming which approval scopes are active today without a fresh authenticated policy handoff.

## Constraints

- Backward compatibility: documentation-only; keep the sample valid JSON.
- Data/privacy: do not copy secrets, keys, or the deployed policy into the repository.
- Performance: no runtime effect.
- Operational: distinguish historical report values from live facts; the operator verifies current state externally.
