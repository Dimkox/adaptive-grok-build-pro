# Add repository-scoped immutable policy profiles to the Python trust-ci webhook API and worker, selecting commands and holdout by exact repository, binding jobs to the selected profile digest, rejecting unknown repositories, and preserving schema-version-1 behavior with automated tests

Change ID: `20260829-add-repository-scoped-immutable-policy-profiles-f778c6`
Created: 2026-08-29T09:12:58+00:00
Risk: medium
Complexity: standard
Domains: api

## Problem

Trust CI currently loads one global policy and therefore one repository-specific command/holdout set. Although the GitHub App is installed for `Dimkox/ii-tonya-platform`, allowlisting that repository would execute the `adaptive-grok-build-pro` checks against the wrong tree and fail without proving the product.

## Outcome

One Trust CI deployment can verify multiple explicitly configured repositories. Each accepted webhook is bound to the exact immutable profile selected for its repository, and `ii-tonya-platform` can receive its own App-owned exact-SHA check without weakening the existing repository gate.

## Scope

### In scope

- Add an immutable schema-v1 `PolicyCatalog` with exact repository lookup.
- Preserve the legacy single-policy schema and its digest/check-name behavior.
- Bind enqueue, worker execution, approvals, checks, and attestations to the selected effective profile digest.
- Support repository-specific commands and external holdout definitions under one common execution envelope.
- Add policy, API, worker/runner, compatibility, replay, and failure tests.
- Update policy examples, Trust CI README, root README, rollout and rollback documentation.

### Out of scope

- Editing or installing the deployed server policy, holdout bundle, images, secrets, database state, GitHub App, or branch protection.
- Merging, deploying, or enabling `ii-tonya-platform` in production.
- Per-profile runner images, credentials, lease behavior, or worker pools.
- Database schema changes or historical-job reinterpretation.

## Constraints

- Backward compatibility: existing schema-v1 files remain valid and retain their exact canonical digest and Check Run name.
- Data/privacy: repository mappings and command output remain absent from public health/metrics; no new personal data or secrets are stored.
- Performance: profile resolution is an in-memory exact lookup; no database round trip or migration is introduced.
- Operational: API and workers must load the same immutable catalog generation; unknown or stale bindings fail before checkout/commands.
