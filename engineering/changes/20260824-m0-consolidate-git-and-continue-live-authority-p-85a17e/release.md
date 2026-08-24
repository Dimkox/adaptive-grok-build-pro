# Release plan — M0 consolidate git and continue live authority proof

## Deployment

No product release. Local commit on `milestone/m0-live-trust-authority` only. Do not tag, do not GitHub Release, do not push, do not merge PR #5.

## Feature flags / staged rollout

None.

## Metrics and alerts

Live kill-switch gauge `adaptive_trust_ci_kill_switch` must return to 0 before the slice ends.

## Go/no-go criteria

Go: invariants + `grok_verify --mode pr` green; kill-switch off; no secrets; remote unchanged.
No-go: API left 503; PEM in tree; push; forged check; `compose down -v`.
