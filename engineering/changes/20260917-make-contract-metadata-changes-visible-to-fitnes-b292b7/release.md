# Release plan — Make contract metadata changes visible to fitness (#120)

## Deployment

This is a repository-side compatibility-analysis change. It changes no API runtime, provider behavior, persistent production data, or deployed Trust CI service. Deliver it through the normal branch and pull-request flow with the typed spec, architecture comparator, verifier selector fix, tests, and package documentation together.

## Feature flags / staged rollout

There is no runtime feature flag or live rollout. For local adoption, update to the reviewed source revision and run the selected verification profile. The PR preflight must include `python3 scripts/grok_verify.py --mode pr`, followed by all four required local review receipts: code, test, security, and release. Each receipt must bind to the final tree fingerprint; rerun verification/reviews after any subsequent tree change. The App-owned Trust CI check and any signed human approval scopes remain independent merge requirements.

The analysis change is intentionally limited to registered JSON Schema root `title` and `description`: edits produce `changed_documentation`, distinct from wire-shape incompatibility. Nested annotations remain outside this decision. The contract-structure scanner excludes all YAML under `engineering/changes/`, then classifies remaining YAML by exact API-contract path components or explicit OpenAPI/AsyncAPI filenames, so package content cannot be mistaken for a registered API contract.

## Metrics and alerts

Use the architecture fitness report's `changed_documentation` finding to route root metadata changes for human review. Structural findings retain their existing labels and behavior. A change-package spec file must not appear as an API contract-structure finding. No live metrics or runtime alerting changes are introduced.

## Go/no-go criteria

Go only when root metadata-only, structural-only, combined, both-direction, unchanged, nested-annotation, and YAML-selector regressions pass; the selected verifier passes; and all four local review receipts are present and current for the final tree. Stop on an unsupported comparison, unexpected wire-incompatibility label for metadata-only edits, missing API contract classification, or a false positive on package YAML. Merge still requires the exact-head external Trust CI check and configured signed approvals.
