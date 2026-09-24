# Requirements — Build v2.0.19 artifact child from merged release-sync 3f41be92

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given merged release-sync commit `3f41be92161fef451a2dfa7451eb458ce8f022b3`, when the package command runs twice in private staging, then both ZIPs and their sidecars are byte-identical and the recorded ZIP digest is `4176a872acdca873e840855d0b2c9e379cf8f796c9de69e5560b3e2bf85634b9`.
- [ ] Given the artifact-child tree, when the manifest/package tests inspect it, then both v2.0.19 paths exist, the sidecar names the ZIP, and `PROJECT_STATE` names source parent/tree and both digests.
- [ ] Given the candidate state, when release publication fields are inspected, then `published=false`, `published_at=null`, `external_effect=false`, and `operational_activation=false` remain true/false as appropriate until later exact actions.
- [ ] Given the artifact-child PR, when verification and security/release reviews run, then the exact head is bound to the current route and no deployment or secret boundary is crossed.

## Failure and edge cases

- Reject output creation in an unsafe parent; use private 0700 staging.
- Reject source drift or non-reproducible second build.
- Reject any attempt to tag or publish from the release-sync parent or a stale artifact-child head.

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: release-readiness, exact-SHA Trust CI, PR-only delivery.
- Canonical-example deviations and evidence: none; this follows the v2.0.18 artifact-child pattern.
- Intentional debt created, repaid, or accepted: no new debt; M8/M9 qualification remains historical and separate.

## Non-functional requirements

- Security: no secrets, runtime state, deployed policy or deployment paths enter the diff/archive.
- Reliability: exact parent/tree and reproducible double-build evidence are required.
- Performance: bounded package generation from one tracked source snapshot.
- Observability: record source parent/tree, ZIP/sidecar digests, exact PR head and later external check.
