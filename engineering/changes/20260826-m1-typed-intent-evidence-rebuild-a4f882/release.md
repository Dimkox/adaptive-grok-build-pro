# Release plan — M1 Typed Intent Evidence Rebuild

## Deployment

Source is delivered through PR #8 only after local evidence. Trusted policy/holdout/image deployment is a separate operator action outside the PR trust domain.

## Feature flags / staged rollout

Dual-read legacy compatibility and single-write canonical JSON provide the migration boundary. Keep deployed trusted behavior unchanged until a later exact, approved rollout.

## Metrics and alerts

Track spec parse failures, unmapped criterion IDs, stale evidence, holdout failures, and attestation metadata extraction failures without logging spec contents.

## Go/no-go criteria

All route evidence is current, README/roadmap match the tree, no protected trust material changed, and the external App-owned exact-SHA check plus required signed approval scopes are green.
