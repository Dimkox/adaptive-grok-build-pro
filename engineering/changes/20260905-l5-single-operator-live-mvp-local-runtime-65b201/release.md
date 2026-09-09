# Release plan — L5 single-operator live MVP local runtime

## Deployment

None in this route. The output is an unreleased repository-local Stage 3/5 source
candidate. Published `v2.0.14` artifacts remain immutable and no new package is
built during implementation.

## Feature flags / staged rollout

The native executor profile and any publisher remain absent/unavailable by
default. SQLite is used only when an operator explicitly supplies a valid local
private runtime root; no server-wide fallback enables it.

## Metrics and alerts

Local state/reason/revision counts and bounded recovery outcomes are observable
without content or credentials. No production alerting or live-service claim is
made.

## Go/no-go criteria

Focused source tests and architecture checks pass; after the final tracked source
checkpoint is clean and frozen-file identity is rechecked, run one exact-head
verifier and one code/test/security/data review wave.
cPanel, live model use, hosting, PR/release, and deployment are separate no-go
boundaries pending new authority and evidence.
