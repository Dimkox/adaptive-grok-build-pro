# Prevent release intent from being masked by pull-request wording (#123)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260917-prevent-release-intent-from-being-masked-by-pull-f55a19`
Risk: high
Complexity: high-risk
Domains: security, api

## Problem

The router treats `pull request` and ` pr ` as review-intent terms and checks review before release. A release task that merely mentions its required delivery mechanism is silently demoted to a medium-risk review route, losing release/security review, release-readiness, required evidence, and human gates.

## Proposed outcome

Delivery-mechanism wording does not classify a task as a review. Explicit review language continues to route as review. A release prompt remains a high-risk release regardless of whether it mentions its pull request.

## Scope

### In scope

- Remove delivery-only `pull request` and ` pr ` tokens from review-intent classification.
- Give release intent precedence over co-occurring review wording while retaining bugfix/incident precedence and standalone review routing.
- Add table-driven paired prompts verifying full route fields for release, explicit review, and release-fix counterexamples.
- Add generic feature-task controls proving bare pull-request/PR delivery wording does not create review intent.
- Preserve the current precedence of incident/bugfix/release and route schema v1.

### Out of scope

- Broad intent-precedence changes outside incident, bugfix, release, and review.
- Changing route serialization or deployed trust/approval policy.
- Treating route gates as independently enforced authorization; that is #126.
- Creating release/tag/push/PR/production effects.

## Constraints

- A true `review` or `review pull request` prompt remains `intent=review`.
- A release prompt remains high risk and retains `production_action_approval`, release/security reviewers, release evidence, and release-readiness workflow skill.
- Bugfix wording must keep bugfix intent even when the task describes a pull request.
- Route field shape remains backward compatible.
