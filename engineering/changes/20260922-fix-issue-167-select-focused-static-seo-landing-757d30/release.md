# Release plan — Fix issue #167: select focused static SEO landing verification for landing-only changes while retaining full PR verification for runtime, contract, Trust CI, package, architecture, or workflow changes, with regression tests.

## Deployment

No deployment or external write. Deliver through the normal isolated branch and pull request only; this task does not authorize push, PR, merge, or release publication.

## Feature flags / staged rollout

No feature flag. The focused mode is an explicit local verification command selected after scope classification. Mixed or unknown changes use full PR verification.

## Metrics and alerts

Review JSON reports for `mode`, `verification_scope.profile`, `landing_directories`, `focused_tests`, rejected paths, and skipped broad checks. A failed or ambiguous scope is expected fail-closed behavior, not permission to bypass full PR verification.

## Go/no-go criteria

No-go while either active-route review or final fingerprint-bound verification is pending. Go only when targeted tests are GREEN, the current final tree passes full PR verification, the required `code_reviewer` and `test_reviewer` reports pass, docs match the implementation, and the exact App-owned Trust CI check succeeds on the final PR head. Local receipts and focused mode do not replace full verification, route reviews, or Trust CI.
