# Code review — repository-scoped immutable policy profiles

Base: `1c06299894279a88b881defa3f19b004fa742223`

Reviewed head: `3db32de705a0cd084d3c7d967b4ff927f2b436de`

Verdict: **PASS**

The implementation was reviewed read-only against the actual diff, source, tests, design/change package, and all preserved round-1/round-2 FAIL reports.

## Findings

No blocking findings.

The previously raised concern about a broad configured root is downgraded to an operational residual risk. The approved design explicitly treats `TRUST_CI_HOLDOUT_PATH` and `TRUST_CI_HOLDOUT_HOST_PATH` as independently configured, server-owned trusted roots outside the pull-request trust domain. The reviewed catalog cannot modify either environment variable. No approved requirement supplies a second in-repository allowlist, and no attacker controlling catalog input can alter the roots without already controlling deployed Trust CI configuration at the same trust tier as the runner image, signing keys, database, and other deployment-owned inputs. Rejecting `/` remains a useful fail-closed guard against accidental filesystem-wide configuration; `/srv` may be an intentional operator-owned root.

## Verified controls

- Filesystem root `/`, empty, and relative trusted-root inputs are rejected before worker dependencies are constructed.
- Catalog local and host holdout paths are canonicalized and must be strict descendants of their configured roots; the root itself, parent traversal, outside-root paths, and unequal relative suffixes are rejected.
- The canonical effective profile data, including holdout paths, contributes to the profile/policy digest.
- API lookup is exact and case-sensitive; unknown repositories are rejected before enqueue and closed-event cancellation.
- Jobs retain the selected policy digest; worker resolution is bound to `(repository, job.policy_digest)` and does not fall back to the current profile.
- Catalog execution tests cover distinct commands, mounts, check epochs, environment values, and attestation digests for two repositories.
- Catalog approval, changed-digest idempotency, removed-profile fail-closed behavior, replay without re-execution, and closed-event isolation are now represented in the reviewed tests.
- Legacy policy parsing, digest/check-name behavior, and legacy runner flow remain covered and are not routed through catalog-only path validation.

## Residual risks

- The worker durably marks an unavailable policy binding as failed but does not publish a corresponding GitHub failure check. If every terminal job must have a visible App-owned check, this remains an observability/reconciliation gap.
- Deployment operators must keep the server-owned roots narrow and correctly mounted. This is outside PR-controlled catalog input and is not a code-review blocker under the approved trust model.
- The route-selected tests and local verification are preflight evidence only; merge still requires the external exact-SHA Trust CI check and required signed approvals.

No deployment, external write, secret access, or code/test modification was performed.
