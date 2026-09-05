# Release plan — Repair L5 current landing source binding

## Deployment

No deployment in this change. Deliver source through a pull request only. A
future release uses a new version and new artifact; published `v2.0.14` is not
rebuilt or replaced.

## Feature flags / staged rollout

The existing unavailable provider and transport-free publisher remain the
fail-closed defaults. There is no activation flag change.

## Metrics and alerts

Local evidence is the exact source tuple, candidate changed paths, 20-member
manifest/provenance, verifier fingerprint, and three review receipts.

## Go/no-go criteria

Go only when focused red-green evidence, one exact-head PR verifier, and all
three selected reviews pass with zero `grok_status` gaps. No-go on source-pin
mismatch, unknown stylesheet surface, changed `index.css`, incomplete artifact,
published-package drift, or any external effect.
