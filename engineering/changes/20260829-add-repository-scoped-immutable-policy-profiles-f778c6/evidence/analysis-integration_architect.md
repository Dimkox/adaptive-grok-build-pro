# Integration architecture analysis

Route: `f778c6ffc84c`
Repository: `/home/pall/grok-projects/adaptive-grok-build-pro-trust-ci-repo-profiles`
Scope: read-only analysis of repository-scoped immutable policy-profile selection.

## Current integration contract

- `trust-ci/src/adaptive_trust_ci/api.py:75-109` authenticates the GitHub `pull_request` webhook, parses `repository.full_name`, rejects repositories not in the process-wide `Policy.allowed_repositories`, and calls `Store.enqueue()` with the single active policy digest and max-attempts. Duplicate delivery returns the existing job.
- `trust-ci/src/adaptive_trust_ci/webhooks.py:28-54` produces a `JobRequest` containing repository, PR number, base/head SHA and refs. There is no profile identity in the webhook payload or request model.
- `trust-ci/src/adaptive_trust_ci/models.py:58-89` defines the idempotency key over repository, PR number, head SHA, pipeline and policy digest. Base SHA and refs are deliberately excluded; a same-head delivery with changed metadata is therefore a duplicate.
- `trust-ci/src/adaptive_trust_ci/store.py:297-353` and `trust-ci/sql/001_schema.sql:1-34` persist `repository` and `policy_digest`, with a unique idempotency key. PostgreSQL uses `ON CONFLICT (idempotency_key) DO NOTHING`; the in-memory store mirrors this. The durable job row does not currently persist a profile ID, profile digest separate from policy digest, commands, holdout digest, or Check Run ID.
- `trust-ci/src/adaptive_trust_ci/worker.py:25-48` loads one policy at worker startup and injects it into `JobRunner`.
- `trust-ci/src/adaptive_trust_ci/runner.py:49-70` creates/restarts the Check Run using the worker policy check name, then rejects a job whose stored digest differs from the worker policy digest. Execution commands and holdout are selected from that same worker policy.
- `trust-ci/src/adaptive_trust_ci/github.py:130-184` searches Check Runs by `external_id == job_id` and otherwise creates one. `trust-ci/src/adaptive_trust_ci/runner.py` publishes the final result after execution and records signed attestation before/around publication; the existing runner replay test covers publication failure recovery.

## Required design boundary for profiles

Selection must happen once, at webhook enqueue time, from an immutable server-side mapping keyed by the exact canonical `repository` string. The API must:

1. resolve the profile or reject the event before creating a job;
2. snapshot/bind the profile digest (and the effective command and holdout inputs, directly or through that digest) in durable job state;
3. pass that binding through the Store contract; and
4. return the same job/profile result on duplicate delivery.

The worker must consume the job’s bound profile, not re-resolve the repository against a mutable current mapping. It should fail closed if the digest/profile is unavailable or no longer matches the immutable profile material. A process-wide “current policy” check remains useful as a deployment/configuration safety check, but cannot be the source of repository-specific commands or holdout selection.

The profile digest should be calculated from canonical JSON containing all behavior-affecting fields: check-name prefix/epoch inputs, commands, approval rules, sandbox image and limits, checkout/lease/retry limits, environment allowlist, and external holdout path/digest/commands. The holdout bundle digest must remain independently verified outside the checkout. Do not use a mutable profile filename or repository-controlled configuration as the binding.

## Component-by-component impact

### Webhook producer / API

`parse_pull_request_event()` can remain schema-version-1 compatible because GitHub’s event shape need not change. Add a profile resolver after parsing and before enqueue. Unknown, malformed, or non-canonical repositories must be rejected deterministically (prefer the existing policy rejection class/status rather than silently falling back to the default profile). The response should expose the selected profile digest or stable profile ID only if that is an intentional public contract; never expose commands, secrets, or internal paths.

The closed-event path must resolve authorization consistently: an unknown repository must not be able to cancel jobs by spoofing a repository name, while a previously accepted repository remains cancellable if it is later removed from configuration. This argues for checking the exact repository against the profile registry before `cancel_pr`, but not requiring the profile’s current digest for cancellation.

### Store contract and schema

Extend `Store.enqueue()` with a typed immutable profile binding, rather than making the worker reconstruct it from `repository`. At minimum persist `profile_id`/canonical key and `profile_digest`; preferably persist a canonical profile snapshot or a server-side immutable profile artifact reference whose digest is verified. The job’s `policy_digest` may be renamed only with a compatibility migration; retaining it as an alias during schema-version-1 transition is safer.

The uniqueness rule must remain repository-scoped and digest-scoped: `(repository, PR, head SHA, pipeline, profile digest)` through the canonical idempotency key. A profile change for the same head must produce a new job and a new epoch Check Run, while a replay under the same profile must return the original job. The superseded-head update must continue to be constrained by repository and PR, so repositories cannot cancel each other’s work.

For PostgreSQL, add a versioned migration and update `MemoryStore` in lockstep. Existing rows need a deterministic compatibility value representing the legacy single profile; do not infer a new repository profile for historical jobs after the fact. If a profile snapshot is stored, use JSONB plus a verified digest and document retention/size limits. Avoid adding profile selection to `trust_ci_events` only; event history is not sufficient as worker input.

### Worker consumer

The worker currently has one `Policy` object and one `JobRunner`. It must resolve the bound profile for each claimed job, validate digest equality, then construct/use a runner with that profile. A stale/missing profile is a terminal policy/configuration failure with a non-success Check Run, not a retry loop that could later execute different commands. Profile loading/verification failures should be observable with a stable failure code.

Lease reclaim and retry must preserve the same profile binding. A reclaimed job must not run under the profile currently assigned to the repository if that differs from the job digest. The runner’s existing `job.policy_digest != self.policy.digest` guard is the right invariant, but it must compare against the job-selected profile and include profile identity in the diagnostic result and attestation.

### GitHub Check publisher

The Check Run name must be derived from the bound profile epoch, e.g. the configured prefix plus the bound profile digest prefix. It must not use the worker’s global current profile. Keep `external_id = job_id`; this prevents two profile jobs from sharing a Check Run and preserves exact-job replay.

Because Check Run ID is not persisted, replay after a process crash searches GitHub by repository, head SHA, check name, and external ID. The existing implementation searches by external ID through the Check Runs list, but the profile-aware contract should assert the name and SHA as well before reusing a run. Persisting the Check Run ID is preferable for deterministic PATCH and can be added as nullable state without changing webhook schema.

If the profile digest changes for the same head, the new Check Run name must be different, and the old Check Run must not satisfy the new required check. Branch protection is configured against the epoch check name; rollout must account for multiple repository-specific required contexts and avoid switching protection until the corresponding profile checks are deployed.

## Idempotency, retry, and replay implications

1. Same signed webhook, same repository/head/profile digest: one durable job; second response is `created=false` and the same job ID/profile binding.
2. Same repository/head, different profile digest: distinct job and Check Run; this is intentional re-evaluation under a new immutable epoch. It must not mutate the old job.
3. Same head, different repository: distinct idempotency key and no cross-repository supersession or cancellation.
4. New head on the same repository/PR: old active jobs are cancelled as today; the new head gets a new job and Check Run. A late worker completion must fail lease/ownership or otherwise be prevented from publishing a success for the superseded head.
5. Worker retry or lease reclaim: reuse the exact stored profile digest and commands; do not re-read mutable repository mapping.
6. Check publication failure after attestation: retry publication using the same job/profile/check name, without executing commands again. The existing `test_signed_attestation_is_replayed_after_check_publication_failure` is the characterization test to preserve.
7. Duplicate GitHub delivery during a running/finished job: enqueue idempotency must be durable and race-safe; the API must not create another job or reset a finished result.
8. Unknown repository: reject before enqueue, with no job and no Check Run. A profile resolver must not have wildcard/default fallback.

## Compatibility and replay test matrix

Required tests should cover both `MemoryStore` and PostgreSQL contract behavior where integration infrastructure permits:

- schema-version-1 webhook fixture without profile fields still accepts the legacy configured repository and selects the legacy/default profile deterministically;
- unknown repository, malformed repository, and near-match casing/whitespace are rejected without enqueue;
- two configured repositories select different command sets, holdout digests, check-name epochs, and persisted profile digests;
- same repository/head/profile replay returns one job; concurrent duplicate enqueue returns one job;
- same repository/head with changed profile digest creates a separate job and does not overwrite the first binding;
- new head supersession remains scoped to `(repository, pr_number)`;
- worker reclaim/retry executes the originally bound profile after the registry’s current mapping changes;
- missing/tampered profile or holdout digest fails closed and never executes checkout commands;
- worker publishes the bound profile check name and exact SHA; profile A and B cannot reuse each other’s Check Run;
- Check Run publication retry reuses the same `external_id`, check name, and attestation, with no duplicate command execution;
- old schema-1 jobs can be read and processed using the documented legacy profile binding, or are explicitly migrated before workers are upgraded;
- approval lookup/attestation verification remains bound to repository, exact PR/base/head SHA, and the bound profile digest;
- API response and `/jobs/{id}` expose the binding consistently without exposing command arguments, holdout paths, or secrets.

## Rollout and rollback concerns

Deploy the reader/migration compatibility first, then add immutable profiles and API selection, then enable additional repositories, and finally update per-repository branch protection to the profile epoch check names. During mixed-version operation, old workers must not claim jobs containing an unrecognized binding; use a compatibility representation or gate rollout on worker upgrade. Rollback must preserve old job rows and route them to the legacy profile; never reinterpret a historical digest as a newly edited profile.

## Assessment

The existing system has strong primitives for this change—exact repository/head identity, durable unique idempotency, lease ownership, immutable policy digest checks, epoch Check names, and attestation replay—but the current single-policy architecture makes worker-time repository selection unsafe. The critical acceptance condition is therefore: profile resolution and digest binding are durable at enqueue, and every retry/replay/publish path consumes that stored binding unchanged.
