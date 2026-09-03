# External Observer / Truth Projection v1 design

## Purpose and authority

The External Observer is a separate operator-owned, nonprivileged, read-only service/domain; it is not part of the adaptive-delivery controller, Factory or Trust CI. It reads one closed operator configuration, bounded typed local claim evidence, and allowlisted public GitHub REST facts; it emits deterministic `PUBLIC_STATUS.v1` JSON and a plain-text rendering derived from those exact bytes. It reports truth but cannot create it: it has no GitHub token, webhook, external-write method, GitHub Actions dependency, Trust CI authority, approval/signing key, Factory edge, or production/deployment authority.

The configured subject is exactly one repository, its default branch, one numbered current-delivery pull request, one required Check Run name and one GitHub App ID. V1 does not enumerate all pull requests to infer delivery. Historical M0-M9 records remain `evidence_claimed` or `historical_evidence_claimed` with their claimed SHA/digest/freshness until a future bounded run explicitly validates each identity.

## Inputs and trust model

The repository ships a closed schema at `engineering/contracts/schemas/external-observer-config.v1.schema.json` and a placeholder-only example at `engineering/external-observer/external-observer.example.json`. The actual repository, branch, candidate PR, expected check name/App ID and bounds are selected in operator-owned deploy configuration; no mutable PR is committed as “current”, and the config contains no credential or arbitrary URL.

`PROJECT_STATE.json`, a future closed typed evidence manifest, and local verification/review receipts are claims, never remote facts or merge authority. Closed adapters normalize typed records; malformed, contradictory, stale, symlinked, oversized or SHA-mismatched claims become `mismatch`, `stale` or `unknown`, never success. Free-form README/START_HERE prose is not parsed as authority; during implementation their mutable current facts are replaced by observer links/run instructions, while any retained digest is informational only. `PROJECT_STATE.json` must label itself a historical claim/snapshot rather than current observation.

All GitHub response strings are untrusted data. They are strict UTF-8 JSON with duplicate-key/non-finite rejection, closed types, bounded arrays/strings/body, normalized fixed errors and no raw-body persistence. Runtime state is ignored, regular-file/no-follow, atomically replaced under one lock, and contains only normalized public metadata, ETags if bounded, and digests.

## Read-only GitHub adapter

The adapter accepts only HTTPS `api.github.com`, fixed repository-derived paths, `GET`, static public headers, no Authorization/cookies/userinfo/proxy, no redirects, no inline retry, 10 seconds per request, 90 seconds total, 1 MiB per body, four annotated-tag hops and at most 100 check runs/candidates. Allowed endpoint shapes are:

- `/repos/{repo}/commits/{main}` and a final repeat of the same read;
- `/repos/{repo}/pulls/{configured_number}` and a final repeat;
- `/repos/{repo}/commits/{exact_pr_head}/check-runs?per_page=100`;
- `/repos/{repo}/releases/latest`, `/git/ref/tags/{encoded_tag}` and `/git/tags/{sha}`;
- `/repos/{repo}/compare/{release_commit}...{main_sha}` and `/compare/{merge_commit}...{main_sha}` when applicable.

The exact PR GET is authoritative for the configured current proposal. Any optional PR list is discovery-only, explicitly partial, and cannot prove absence, delivery or milestone status. Rate limit, 403/404/429/5xx, redirect, timeout, oversize, malformed content or movement during the final reread yields `unknown` on first observation and `stale` after a prior valid observation.

V1 is intentionally anonymous and best-effort, not enterprise-reliable; the shared-IP allowance was observed exhausted at 60/60 during design. A future authenticated adapter is outside V1 and requires separate security review plus a separately provisioned Observer credential/App limited to metadata, contents, pull requests and checks read scopes, mounted outside the repository. It must never reuse Trust CI's checks-write credential or acquire a write scope.

## Freshness and truth semantics

A snapshot is `fresh` only when the opening and closing main SHA and PR identity/head/base facts are identical, its age is within the configured ceiling, every asserted SHA uses lowercase 40-hex, and every positive projection follows exact equality or a validated compare relation. Any moving input invalidates the whole snapshot; partial endpoint success is not mixed into a fresh projection.

- `implemented`: true only when the typed implementation claim SHA equals the configured PR head SHA; otherwise false/unknown with a stable reason.
- `reviewed`: true only when every required local receipt is current for the exact implementation head and tree fingerprint. These receipts remain local evidence, not merge authority.
- `check_verified`: true only for exactly one allowlisted Check Run matching configured name, configured App ID and exact PR head with completed/success conclusion; duplicates or conflicting matches fail closed.
- `delivered`: true only when the exact PR says merged and its exact merge commit is proven identical to or an ancestor of current main by a structurally consistent compare response.
- `released`: true only when the newest qualifying non-draft/non-prerelease release tag resolves through a bounded annotated chain to a commit and that commit equals the delivered/current main identity required by the claim. SHA inequality alone never proves release lag.
- `release_relation`: `current` only for exact equality; `release_behind` only when compare from release commit to main is structurally consistent `ahead`, `behind_by=0`, merge base equals the release commit and the terminal candidate equals main; divergence/rewind/inconsistency is `unknown`/`mismatch`.
- `attestation`: `ATTESTATION_UNOBSERVABLE` unless a separately reviewed, redacted, signed public endpoint and public verification material exist. The observer never follows Check Run `details_url`; the current loopback bearer-protected `/jobs/*` and `/attestations/*` surfaces are `REFERENCED_NOT_VERIFIED`. A Check Run, receipt, README sentence or private Trust CI state never substitutes for signature verification.

Implemented, reviewed, check-verified, delivered and released are independent typed fields; one never implies another. Overall status is `fresh_consistent`, `mismatch`, `stale` or `unavailable`, with stable bounded reason codes and no optimistic fallback.

## Canonical output

`PUBLIC_STATUS.v1` is a closed JSON object planned under `engineering/contracts/schemas/public-status.v1.schema.json`. It contains schema/version, configured subject digest, observation timestamps/age, snapshot status, remote main/PR/check/release identities and relations, typed claim projections, attestation visibility, source freshness, bounded fixed-code findings, and a canonical SHA-256 digest. Keys and arrays are sorted; the digest excludes itself and is computed over UTF-8 canonical JSON. The human renderer consumes the validated JSON object only, prints the digest and every stage independently, and cannot refetch or reinterpret facts.

## Failure, recovery and rollout

The first failed run emits unavailable/unknown; a later failed run preserves the last valid normalized snapshot as stale with its original observation time and a new bounded failure record. Lock contention performs no network or state write. Corrupt state, digest mismatch or unsafe path fails closed and requires operator quarantine/forward-fix; it is never silently reset.

Rollout is source-first and inert: fake transport tests, manual local CLI, then an optional separately reviewed operator service. No scheduler install/enable, PR update, release or deployment is part of this change. Removing/disabling the observer cannot affect delivery, Factory, Trust CI or production because the observer owns no mutation edge.

## Schedule and dependency order

Hard whole-program deadline: `2026-09-04 23:59 UTC+3`. Observer documentation is targeted Sep 3 16:45-18:00, implementation 18:00-21:00, verification/reviews 21:00-23:00 and bounded remediation/freeze 23:00-01:00. Observer exact-SHA evidence closes before accepted M5 work; M4 final acceptance remains M5's predecessor, so accepted integration is Observer + accepted M4 → M5 → M6 → M7 → M8 → M9. Later source-preparation hours are targets only; external Trust CI, M5 isolation, the M8 real-human cohort and M9 signed/human authority cannot be promised by the deadline.
