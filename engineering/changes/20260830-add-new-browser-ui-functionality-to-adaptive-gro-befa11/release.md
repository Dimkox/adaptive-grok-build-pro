# Release plan — Add new browser UI functionality to Adaptive Grok Build Pro: create a one-command local HTTP demo application with a polished responsive dashboard using real repository routing, typed-spec, architecture, governance, and verification-summary logic against bundled sample data; add automated tests and user documentation. Do not perform external writes.

## Deployment

No external deployment in this change. Source identity is `2.1.0`; the local deliverables are `dist/adaptive-grok-build-pro-v2.1.0.zip` and its adjacent SHA-256 checksum. Exact-SHA external Trust CI, signed scopes, merge, tag, GitHub Release publication, and production activation remain separate gates.

## Feature flags / staged rollout

Opt-in through `scripts/grok_demo.py`; never autostarts and binds only to loopback.

## Metrics and alerts

Local readiness and per-panel provenance/status only; no telemetry.

## Go/no-go criteria

Focused UI/API tests, full verifier, independent reviews, package checks, and the five-minute walkthrough must pass on one fingerprint.

## Rollout and rollback

Rollout is opt-in from a complete checkout or local ZIP. Stop the process for immediate rollback; if the feature must be removed, revert it through a normal pull request. No durable demo data, migration, remote configuration, or deployed authority plane is affected.
