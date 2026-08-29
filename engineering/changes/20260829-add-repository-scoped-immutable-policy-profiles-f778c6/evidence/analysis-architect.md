# Architect analysis: repository-scoped immutable policy profiles

Route: `f778c6ffc84c`
Base HEAD inspected: `1c06299894279a88b881defa3f19b004fa742223`
Scope: read-only architecture analysis; no product code was edited.

## Current contract

The current service loads one frozen `Policy` in both API and worker. Its canonical full-policy SHA-256 is persisted as `trust_ci_jobs.policy_digest`, participates in webhook idempotency, binds approvals and schema-v1 attestations, and produces `adaptive-trust-ci/verified@<digest[:12]>`. The runner creates that Check Run, rejects a job whose stored digest differs from the deployed policy, verifies the external holdout before checkout commands, and then executes one global holdout/command set.

The existing durable fields already contain the minimum trusted profile identity: exact `repository` plus `policy_digest`. The PostgreSQL schema therefore does not need a new profile column if `policy_digest` remains the digest of the effective repository policy.

## Recommendation

Adopt one server-mounted, immutable `PolicyCatalog` that resolves an effective frozen `PolicyProfile` by exact GitHub `repository.full_name` and never by wildcard, case normalization, alias, or default fallback.

Profile identity is the tuple:

```text
(exact repository, full 64-hex effective_profile_digest)
```

The repository is the authoritative profile key; an optional display name must have no trust semantics. For the new profile form, derive the digest from canonical JSON for the complete effective policy: the exact repository, all common execution/security controls, sandbox image and limits, approval rules, selected repository commands, and selected holdout path/digest/commands. A catalog digest may additionally describe the sorted repository-to-profile map for deployment diagnostics, but it must not be stored on jobs or used in Check Run names.

Keep the schema-v1 legacy form valid and unchanged. When `repository_profiles` is absent, parse the existing `allowed_repositories` plus global `commands`/`holdout` through the current normalization path and map every allowed repository to that same legacy policy object, preserving its digest and check name exactly. The new profile form and legacy form must be mutually exclusive so precedence cannot be ambiguous. Old binaries are not forward-compatible with the new form, so binaries must be upgraded while the legacy configuration is still active.

Initially keep the worker execution envelope process-wide—especially `status_context`, pipeline, lease duration, sandbox runtime/image, and trusted holdout roots—and scope only commands and holdout definitions by repository. This matches the current single claim lease, runner image, and mounted holdout-root contracts. Every effective profile digest still includes the common envelope, so a common security-policy change rotates all affected profile epochs.

### Resolution flow

```text
verified webhook
  -> parse exact repository
  -> catalog.resolve(repository), else HTTP 403 and no job
  -> enqueue existing policy_digest = selected profile digest
  -> worker claims job
  -> catalog.resolve_bound(job.repository, job.policy_digest)
  -> reject missing/stale/mismatched binding before token, checkout, or commands
  -> JobRunner(selected profile)
  -> selected holdout integrity + commands
  -> selected repository commands
  -> schema-v1 attestation with existing policy_digest field
```

Retries and attestation replay may continue only while the exact repository/digest binding remains current. A changed or retired profile must produce terminal non-success and require a fresh job; the worker must never substitute the repository's newest profile for an older job. Approval submission must resolve the job-bound profile before checking configured scopes and TTL, while retaining the existing repository/PR/base/head/digest signature bindings.

No database migration is recommended. Existing `repository` and `policy_digest` fields preserve digest-aware idempotency, approvals, attestations, and job reads. `Policy`, approval, attestation, and webhook schema-version-1 meanings remain: `policy_digest` identifies the complete effective server policy applied to that exact repository/job.

### Check naming

Each repository's required check remains:

```text
<status_context>@<selected effective profile digest first 12 hex>
```

Do not put the catalog digest in the name. A change to repository A's commands or holdout must rotate A's check without rotating repository B. Keep `external_id = job_id`. Branch protection and the approval/branch-protection CLI must resolve the profile using the explicit repository and bind the exact resulting check name plus GitHub App ID. A stale job should fail under the currently selected repository epoch when that profile is available; if the repository/profile was removed, absence of a successful required check remains fail-closed.

## Safe alternatives considered

1. **Content-addressed profile artifact registry.** A trusted manifest maps exact repositories to immutable digest-named profile files, and workers load the job's artifact by digest. This gives stronger artifact retention and rolling-deployment options, but needs atomic manifest/artifact distribution, retention and garbage-collection rules, more doctor/CLI/compose work, and an explicit current-assignment check so retired profiles cannot continue running contrary to existing stale-policy invalidation. Prefer only when zero-downtime profile generations become a demonstrated need.

2. **Per-repository API/worker pools.** Each repository retains today's single-policy service and queue/worker deployment. This gives the strongest runtime blast-radius separation and permits different runner images, but multiplies webhook routing, secrets, processes, monitoring, upgrades, and branch-protection operations. It is disproportionate for repositories sharing one trust domain and runner envelope; reserve it for repositories requiring genuinely different isolation or credentials.

A single catalog-wide digest used for every job was rejected as the target design: it remains fail-closed, but an unrelated repository edit rotates every repository's check and does not prove which repository-specific commands and holdout were selected.

## Rollout and rollback

1. Deploy readers that accept both legacy and profile schema-v1 forms while retaining the legacy policy. Prove the current digest and required check are unchanged.
2. Prepare the reviewed server-side catalog and per-repository holdout directories under one trusted root. Validate every profile, exact repository uniqueness, canonical digest, holdout digest, and common runner-image constraint offline.
3. Use the kill switch/drain window to switch API and workers atomically to the same catalog generation; never let an old worker claim jobs emitted from the new profile form.
4. Onboard one repository at a time. Prove its App-owned exact-SHA Check Run and signed attestation before binding that repository's branch protection to its profile epoch.
5. Roll back as one coherent unit: previous reviewed API/worker images, catalog, and holdout artifacts. Preserve PostgreSQL and attestations. If an effective digest changes, enqueue fresh jobs and change branch protection only after the restored App-owned check is observed. Never reuse a digest for changed content.

## Critical risks

- **API/worker catalog skew:** can cause false failures or, if guards are weakened, cross-profile execution. Require the same catalog generation and full digest checks; mismatch is terminal before checkout.
- **Ambiguous compatibility parsing:** accepting legacy and profile fields together could select unintended commands. Reject mixed forms, duplicate repositories, wildcard/default profiles, and case-near-match fallback.
- **Incomplete digest material:** omitting common controls, approval rules, sandbox, command environment, or holdout commands would allow behavior to change without rotating the epoch. Hash the full normalized effective policy.
- **Holdout path confusion:** current deployment has one worker-visible and one Docker-host-visible holdout path. Multi-profile holdouts must be confined beneath paired trusted roots with traversal-safe relative mapping; verify the selected directory digest before checkout.
- **Per-profile runner/lease drift:** the worker currently claims before profile-specific dispatch and pins one runner image. Keep these controls common in schema v1; widening them requires a separate worker-pool/queue design.
- **CLI/health ambiguity:** `policy-digest`, doctor, metrics, approval creation, and branch protection currently assume one digest. Repository-sensitive commands must require an exact repository; unauthenticated health should expose only a catalog generation/count, not repository mappings.
- **Branch-protection sequencing:** changing a profile check name before a successful App-owned replacement exists can block all merges; removing the old requirement too early weakens the gate. Prove replacement first, then switch protection.

## Required architectural tests

At minimum, retain the exact legacy v1 digest/check behavior; prove stable profile digests independent of catalog ordering; exact two-repository selection; unknown/case-variant rejection without enqueue; repository A changes leaving B's digest unchanged; common policy changes rotating all profiles; digest-aware duplicate enqueue; stale/missing binding failure before checkout; selected holdout/command order; schema-v1 approval and attestation binding; and App-owned Check Run replay with the same job/profile/external ID.
