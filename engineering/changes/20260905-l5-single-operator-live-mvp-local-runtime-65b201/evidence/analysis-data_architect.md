# Data architecture analysis — restart-safe local landing runtime

## Ruling and scope

This analysis is bound to route `65b2018b786d` and exact predecessor commit
`f3f8d7375a153393ffba3906165e8d625e45d4a1` (tree
`a8f8d71a745e69b12f630d73ba11e1cdca262c5e`). The minimum safe MVP is a
host-local SQLite metadata store plus a private filesystem content-addressed
artifact store (CAS). It is additive to the landing vertical and must not use,
renumber, or introduce repository PostgreSQL migration `019`.

The SQLite database is an operational projection for one local operator. It is
not a replacement for the existing PostgreSQL control-plane store and is not a
production or external database operation. Its schema starts at independent
`PRAGMA user_version = 1` and should be created only inside the configured local
runtime directory.

## Schema before the change

- `InMemoryLandingJobStore` retains `LandingJobRecord` objects in a process-local
  dictionary keyed by `(tenant_id, repository_id, job_id)` and permits
  unconditional replacement. Restart loses every job, result, provider evidence
  reference, and idempotency decision.
- `LandingApplicationService` serializes only the current process with an
  `RLock`, writes `accepted`, performs all work synchronously, and then writes a
  terminal record. There is no durable stage boundary, compare-and-swap revision,
  lease, or fencing token.
- Submission idempotency is inferred from `job_id` and the in-memory
  `LandingInputV1`. Cancellation discards its `Idempotency-Key`, can overwrite an
  already-ready result, and clears the artifact reference.
- `PrivateLandingBlobStore` writes private, fsynced, digest-bound blob files, but
  its job-to-blob index is in memory. On construction its startup sweep removes
  matching private `.blob` files. Consequently, pending inputs cannot survive a
  restart unless startup reconciliation is changed to use durable references.
- `LandingArtifactPackager` already creates deterministic ZIP and SHA-256
  sidecar files with no-replace/retry behavior. The artifact contract and
  manifest bytes are returned to the caller, but no durable job-to-artifact
  index or complete CAS bundle exists.

## Schema after the change

Use one SQLite file and one CAS root under the same private runtime root. Store
canonical JSON as UTF-8 bytes/text and validate it through the existing typed
contracts on every read. Do not store raw upload bytes in SQLite.

### `landing_jobs`

Primary key: `(tenant_id, repository_id, job_id)`.

Required immutable columns:

- `tenant_id`, `repository_id`, `job_id`;
- `input_digest`, `input_json`, `content_sha256`, `quarantine_ref_digest`, and
  `blob_relpath`;
- `exact_base_sha`, `exact_base_tree`, `site_id`, `media_kind`, `media_type`,
  `byte_length`, `received_at`, and `expires_at`;
- `created_at`.

Required mutable projection columns:

- `state` constrained to the existing `LANDING_STATES` values;
- `revision INTEGER NOT NULL DEFAULT 0`;
- `lease_owner`, `lease_fence INTEGER NOT NULL DEFAULT 0`, and
  `lease_expires_at`;
- `provider_evidence_digest`, `artifact_digest`, `failure_code`;
- `input_purged_at`, `updated_at`, and `terminal_at`.

All SHA/digest columns must be lowercase hexadecimal with exact lengths. A
ready row requires an artifact digest; non-ready API views must never disclose
one. The immutable input/source columns must be protected either by a narrow
update method plus an immutable-column trigger, or by a replacement prohibition.
Every mutable update uses `WHERE revision = ? AND lease_fence = ?` and increments
`revision`; zero updated rows means a stale worker and must fail closed.

### `landing_stage_results`

Primary key: `(tenant_id, repository_id, job_id, stage, ordinal)`, with a foreign
key to `landing_jobs` and a unique result digest within the job. Store only
validated canonical contracts needed to resume: normalization request/evidence
and `StaticLandingSpecV1`, candidate/attempt data, and evaluation data. Columns:
`stage`, `ordinal`, `result_digest`, `result_json`, `created_at`.

This table is essential: after a stage result commits, recovery can resume the
next stage without rerunning an already-completed model or renderer call. Raw
provider transcripts, environment, prompts containing secrets, and arbitrary
stdout/stderr do not belong in this table.

### `landing_artifacts`

Primary key: `artifact_digest`. Required immutable columns are
`artifact_json`, `manifest_json`, `manifest_digest`, `zip_sha256`,
`sidecar_sha256`, the exact relative bundle/file names, `member_count`,
`byte_length`, `source_sha`, `source_tree`, `candidate_sha`, `candidate_tree`,
`input_digest`, `spec_digest`, `profile_digest`, `attempt_digest`,
`evaluation_digest`, and `created_at`. Add an operational `availability`
constraint with `committed`, `missing`, or `quarantined`; only `committed` may be
served.

`artifact_json` must round-trip through `SiteArtifactV1.from_dict`, and its
rederived `artifact_digest` must equal the row key. The manifest digest, ZIP
digest, sidecar digest, and every binding already enforced by
`LandingApplicationService._validate_artifact` remain mandatory.

### `landing_job_artifacts`

Primary key: `(tenant_id, repository_id, job_id)`, with foreign keys to the job
and artifact. This immutable link records `artifact_digest`, `linked_revision`,
and `linked_at`. Cancellation may hide the artifact from the public result but
must not delete this audit/recovery link or the CAS bytes.

### `landing_commands`

Primary key: `(tenant_id, repository_id, operation, idempotency_key)`. Store
`request_digest`, `job_id`, `created_at`, and `completed_revision`. Submission
uses the API idempotency key/job ID and binds the full accepted-input identity;
cancellation binds its own header key plus the target job. The same key and same
request digest is an exact replay. The same key with a different digest or job is
`409 idempotency_conflict`. Command insertion and the corresponding job mutation
must commit in one transaction.

### `landing_job_events`

Use `event_id INTEGER PRIMARY KEY`, plus the full tenant/repository/job key,
`revision`, `event_kind`, `from_state`, `to_state`, `detail_code`, and
`created_at`. Enforce `UNIQUE (tenant_id, repository_id, job_id, revision)`.
Events are append-only audit evidence; they are not a second mutable projection.

Recommended indexes are limited to operational access paths:

- `(state, lease_expires_at, updated_at, tenant_id, repository_id, job_id)` for
  bounded recovery claims;
- `(artifact_digest)` on `landing_job_artifacts` for reference/retention checks;
- `(tenant_id, repository_id, created_at)` for operator listing and retention.

## State and idempotency invariants

The transition graph is explicit rather than inferred from arbitrary string
updates:

1. `accepted -> normalizing -> generating -> evaluating -> artifact_ready`;
2. `accepted|normalizing -> provider_unavailable|rejected|needs_human` where the
   current contract permits the outcome;
3. `generating|evaluating -> needs_human` on bounded internal failure;
4. any non-cancelled state may move to the absorbing `cancelled` state to retain
   the current API behavior, but cancellation preserves stage results and any
   artifact link;
5. no state may return to an earlier processing stage, and no state may leave
   `cancelled`.

A lease renewal or crash claim may keep the same visible state, but it must
increase `lease_fence` and `revision`; it is not a new state event. Persist the
stage result and advance the job state in the same transaction. A stale worker
must not write after cancellation or after another recovery claim.

`provider_unavailable` remains a result state for this MVP, matching current
behavior. An exact submission replay returns that same job; an operator retry
requires a new idempotency key/job ID. This avoids an implicit retry loop and
unbounded model calls.

## SQLite durability, transactions, and locking

Initialization must create a `0700` runtime directory and `0600` database/CAS
files under a restrictive umask. The path must be absolute, owned by the current
effective user, outside the repository, local to the host, and neither a symlink
nor a network filesystem.

For every connection enable and verify:

- `PRAGMA foreign_keys = ON`;
- `PRAGMA busy_timeout = 5000` (or a lower configured bound);
- `PRAGMA synchronous = FULL`.

At database creation select and verify `PRAGMA journal_mode = WAL`, set a fixed
application identifier and `PRAGMA user_version = 1`, and reject unknown/newer
versions. A failure to obtain WAL is a startup failure, not a silent fallback.
Use a modest `wal_autocheckpoint` (for example 1,000 pages) and bounded passive
checkpoints during idle/clean shutdown; do not truncate a WAL while readers are
active.

Use one serialized writer connection/process. Readers may use short independent
connections and read transactions. Never retain a SQLite transaction while
reading an upload, invoking Codex/provider logic, rendering, evaluating, hashing,
or writing artifacts. Claims and state commits use short `BEGIN IMMEDIATE`
transactions. A busy timeout expiry is observable `store_busy`, not an unbounded
retry.

## Artifact CAS commit protocol

The CAS bundle key is `artifact_digest`, for example
`sha256/<first-two>/<artifact_digest>/`. Preserve the existing digest-bearing ZIP
filename and its exact sidecar text. Include `manifest.json` and canonical
`site-artifact.v1.json` in the same private bundle so an index can be validated
or rebuilt without trusting a filename.

The only safe commit order is:

1. Claim the job with a durable fence; release the database transaction.
2. Build into a `0700` staging directory on the same filesystem as the CAS under
   umask `077`.
3. Revalidate the typed artifact and all source/input/spec/profile/attempt/
   evaluation bindings. Rehash the ZIP, sidecar, manifest, and artifact JSON.
4. Fsync every staged file and directory, then install the entire immutable
   bundle with no-replace semantics and fsync its parent. If the key already
   exists, require byte-for-byte/digest equality and reuse it; a mismatch is a
   collision/integrity failure.
5. In one `BEGIN IMMEDIATE` transaction, recheck job state, revision, tenant key,
   and lease fence; insert/reuse `landing_artifacts`, insert the immutable job
   link, append the event, and transition to `artifact_ready`. Then commit.

Filesystem durability therefore precedes the database reference. A crash before
step 4 leaves only staging material; a crash between steps 4 and 5 leaves a valid
unreferenced bundle that recovery can link or later garbage-collect. The design
must never commit `artifact_ready` before durable CAS installation.

## Restart reconciliation

Startup reconciliation is bounded and deterministic; it does not start a
permanent retry loop.

- Run a bounded `quick_check`, verify schema/application IDs and required
  PRAGMAs, then process at most a configured batch (recommended 100 jobs) ordered
  by expiry/update time and composite key.
- Claim only non-final work whose lease is absent or expired. Increment the fence
  atomically and resume the same stage from its last committed
  `landing_stage_results` record. A stage is rerun only when no committed result
  exists, and each invocation is subject to the existing bounded timeout/attempt
  policy.
- Replace `PrivateLandingBlobStore`'s unconditional startup blob sweep with
  reconciliation against active `landing_jobs`. Temporary files may be removed;
  a `.blob` may be removed only if it has no durable reference and exceeds the
  orphan grace period. A referenced blob must match byte length and
  `content_sha256` before use.
- Commit normalization output before purging the input blob. Then purge and
  record `input_purged_at`; a crash in between is harmless. Missing/corrupt input
  with no committed normalization result becomes `needs_human` with a stable
  integrity reason, not a retry loop.
- Remove stale staging directories after a grace period. For an unreferenced
  complete CAS bundle, validate it and link it only when all expected job/stage
  bindings match; otherwise retain it through the grace period and delete it in
  a bounded GC batch.
- If a committed artifact row points to absent or corrupt bytes, set artifact
  availability to `missing` or `quarantined`, emit an integrity event, fail the
  result read closed, and require operator recovery. Do not silently rebuild and
  claim equivalence, and do not rewrite immutable job history.

## Tenant and security boundary

Every lookup, command, update, stage result, event, and job-artifact link carries
the complete `(tenant_id, repository_id, job_id)` key. `job_id` or
`artifact_digest` alone is never authorization. The current single-operator
mapping of tenant ID to authenticated actor ID may remain for MVP, but it must be
resolved from the authenticated `Actor`, never accepted from request content.
CAS deduplication may be global because artifacts are immutable, but access is
granted only through a tenant-bound job link.

The database, WAL/SHM files, quarantine, staging, and CAS remain host-private.
Persist no bearer token, credential, environment dump, unrestricted provider
transcript, or raw command output. Log only stable reason codes, composite-key
digests, revisions, fences, durations, and byte counts.

## Retention, capacity, backup, and rebuild

- Preserve the current 24-hour maximum input expiry. Purge raw input immediately
  after a durable normalization result or a terminal rejection/cancellation.
- Retain job, command, event, and stage metadata by default for the MVP. Retain
  every referenced CAS bundle. Do not introduce automatic deletion of audit
  records in this change.
- Garbage collection is explicit, dry-run capable, limited to at most 100 items
  per invocation, and deletes only unreferenced staging/orphan CAS data older
  than a configured grace period. Recheck references inside `BEGIN IMMEDIATE`
  immediately before deletion.
- Enforce configurable metadata/job and CAS byte high-water marks. At capacity,
  reject new submissions with a stable capacity error while reads,
  cancellations, cleanup, and recovery continue.
- Use SQLite's online backup API (or a clean stopped copy of DB, WAL, and SHM as a
  unit) plus a filesystem snapshot/copy of the CAS. Copying only the `.sqlite`
  file while WAL is active is not a backup.
- The CAS index can be rebuilt by scanning bounded bundle directories and
  revalidating `site-artifact.v1.json`, manifest, ZIP, and sidecar digests. Full
  job/idempotency history cannot be reconstructed from artifacts; it requires a
  SQLite backup. Re-rendering from source is recovery of last resort and must not
  be described as byte recovery unless the exact source and all bound stage
  contracts are available and the rederived digest matches.

## MVP performance assumptions

The design is valid for one operator/process, one serialized writer, at most
10,000 retained jobs, at most 100 recoverable/in-flight jobs, and metadata-only
SQLite rows. ZIP/input bytes remain outside SQLite; the existing per-artifact
100 MiB contract limit applies. State transactions should remain below 50 ms on
local storage. Provider, Git, ZIP, and hash latency are outside transactions.

This is not a multi-host queue. A second process may read, but a second worker
must not be enabled without an explicit owner/lease compatibility exercise and
load evidence. Metrics should expose queue depth by state, oldest recoverable
age, claim conflicts, busy failures, reconciliation outcomes, input/CAS bytes,
and integrity failures.

## Focused PostgreSQL-free test set

The implementer should run only local temporary-directory SQLite/CAS tests for
this slice before the route verifier:

1. `test_sqlite_store_initializes_private_wal_schema_v1_and_rejects_unknown_version`
2. `test_duplicate_submit_same_digest_replays_and_changed_digest_conflicts_after_restart`
3. `test_composite_tenant_repository_job_key_prevents_cross_tenant_reads_and_commands`
4. `test_state_edges_are_monotonic_cancel_is_absorbing_and_stale_fence_cannot_commit`
5. `test_cancel_idempotency_survives_restart_and_preserves_existing_artifact_link`
6. `test_restart_rehydrates_referenced_quarantine_blob_instead_of_startup_deleting_it`
7. `test_normalization_commit_before_blob_purge_resumes_without_second_provider_call`
8. `test_expired_lease_resumes_from_each_committed_stage_once_with_bounded_batch`
9. `test_crash_before_cas_install_removes_staging_and_leaves_job_recoverable`
10. `test_crash_after_cas_install_before_sqlite_link_reuses_exact_bundle`
11. `test_artifact_ready_commit_never_precedes_fsynced_cas_and_exact_binding`
12. `test_existing_cas_digest_with_mismatched_bytes_fails_closed_without_overwrite`
13. `test_missing_or_tampered_committed_artifact_is_quarantined_and_not_served`
14. `test_wal_reopen_after_unclean_process_exit_preserves_committed_state_only`
15. `test_bounded_gc_keeps_referenced_artifacts_and_removes_only_expired_orphans`
16. `test_online_backup_restore_and_bounded_cas_reindex_rederive_all_digests`

Use subprocess termination only for the three crash-boundary tests; ordinary
unit tests should inject fault points immediately before/after transaction and
CAS commits. No PostgreSQL container, repository migration, network request,
provider call, publish, deployment, or remote mutation is required for this
evidence.

## Implementation gate

The SQLite store is safe to wire into the landing service only when the
service depends on a narrow store protocol rather than the current concrete
`InMemoryLandingJobStore` type, the blob startup behavior is reconciler-aware,
and the CAS-before-database ordering is covered by the crash tests above. Until
then, keep the in-memory implementation available only as a test double and do
not claim restart safety.
