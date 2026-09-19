# Release plan — Prevent release intent from being masked by pull-request wording (#123)

## Deployment

This changes local prompt classification only. It does not publish, deploy, create a PR, tag, or alter external Trust CI. Deliver through the usual reviewed branch and pull-request workflow. Release intent takes precedence over co-occurring review wording so release controls remain selected; bugfix and incident retain their stronger precedence, and standalone review remains review.

## Feature flags / staged rollout

No runtime flag or operational rollout is involved. Adopt the reviewed router revision locally, then verify the full intent matrix: release alone, release with bare PR wording, release plus “review the rollout,” standalone explicit review, and release-installer bugfix. Confirm full route fields, including risk, human gates, reviewers, required evidence, workflow skills, and write owner.

## Metrics and alerts

## Go/no-go criteria

Proceed only when focused router tests and the selected PR verifier pass on the same tree and required independent review receipts are current. Stop if mixed release/review wording selects review, standalone review selects release, or a release-installer bugfix loses bugfix intent. Merge still requires the exact-head App-owned Trust CI check and configured signed approvals; this routing change supplies neither.
