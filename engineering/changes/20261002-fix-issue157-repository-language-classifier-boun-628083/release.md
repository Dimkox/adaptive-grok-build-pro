# Release plan — Fix issue157 repository language classifier: bounded Swift and other language signal detection, symlink-safe manifests, truncation and unknown reporting without suppressing detected signals.

## Deployment

Source-only contour C for the 2.1.1 recovery programme. Deliver the isolated branch through a PR after coordinator verification/reviews; no deployment, tag, release publication or macOS activation is part of this contour.

## Feature flags / staged rollout

Additive classifier disclosure ships with the installed workflow source. Existing supported routing remains compatible; new source languages other than confirmed Swift remain advisory.

## Metrics and alerts

language_scan exposes incomplete status, exact reasons and counters. swift:profile=base-only explicitly limits the verification implication of Swift classification.

## Go/no-go criteria

Focused regression/router checks, full exact-tree verifier, independent selected reviews, App-owned exact-head Trust CI and required approvals must pass. Local source completion or transport does not establish merge/release authority.
