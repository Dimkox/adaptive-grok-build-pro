# Data architecture: production promotion authority

Route: `75aa6daa89b1`
Base: `1c06299894279a88b881defa3f19b004fa742223`

## Existing durable store

- PostgreSQL currently stores jobs, attempts, PR-scoped human approvals, signed Trust CI attestations and a generic events table. Approval replay is rejected by unique `approval_id` and `nonce`; worker leasing uses `FOR UPDATE SKIP LOCKED`.
- Packaged migrations are contiguous and checksum-locked. Deployment SQL under `trust-ci/sql/` must be byte-identical to package resources under `trust-ci/src/adaptive_trust_ci/resources/`; historical `001`-`003` must not change.
- `trust_ci_attestations` binds a Trust CI job and repository/head SHA, but its typed columns do not contain policy digest, protected-branch merge membership or artifact digest. `trust_ci_events` has no promotion reference and is not written by the API. Therefore an envelope insert alone cannot prove "merged commit" or artifact provenance.
- Roles are deliberately separated. The API can insert approvals but cannot write events; worker can write attestations/events; backup is read-only; migrator owns DDL. Promotion grants must remain narrow and additive.

## Recommended additive migration

Add byte-identical `004_production_promotions.sql` in both migration trees. Do not modify or delete existing rows/tables. The migration should create four append-only authorities (if merge/artifact provenance is implemented outside PostgreSQL, the first two may instead be foreign references to an equally immutable service, but acceptance must fail closed when it is unavailable):

1. `trust_ci_merge_evidence`
   - `merge_evidence_id uuid PRIMARY KEY`, `repository text`, `protected_ref text`, `merged_commit_sha char(40)`, `observed_at timestamptz`, `source_event_id text`, `payload jsonb`, `created_at timestamptz`.
   - `UNIQUE(repository, protected_ref, merged_commit_sha)` and `UNIQUE(source_event_id)`; lowercase SHA and non-empty checks.
   - Written only from an independently authenticated GitHub merge/ref observation or exact protected-branch validation. Caller assertions from `POST /promotions` are never inserted as evidence.

2. `trust_ci_release_artifacts`
   - `artifact_evidence_id uuid PRIMARY KEY`, `repository text`, `merged_commit_sha char(40)`, `artifact_sha256 char(64)`, `source_attestation_id uuid REFERENCES trust_ci_attestations(attestation_id) ON DELETE RESTRICT`, `policy_digest char(64)`, `manifest_payload jsonb`, `manifest_signature text`, `verified_at timestamptz`, `created_at timestamptz`.
   - `UNIQUE(repository, merged_commit_sha, artifact_sha256, policy_digest)`; strict SHA/digest checks.
   - Created only after verification of the immutable supply-chain manifest and a passed source attestation. Never cascade-delete provenance.

3. `trust_ci_promotions`
   - `promotion_id uuid PRIMARY KEY`, globally unique `nonce text`, typed signed bindings `repository`, `merged_commit_sha`, `artifact_sha256`, `target_environment`, `policy_digest`, `actor`, `key_id`, `reason`, `issued_at`, `expires_at`, plus `merge_evidence_id` and `artifact_evidence_id` with `ON DELETE RESTRICT`.
   - Preserve the exact canonical `payload jsonb` and `signature text`; add `payload_sha256 char(64) UNIQUE` so a semantically identical signed payload cannot be reinserted with a different request identity.
   - Lifecycle columns: `state text NOT NULL DEFAULT 'accepted' CHECK (state IN ('accepted','consumed'))`, nullable `consumed_at`, `consumed_operation_id`, and a consistency check requiring both consumption fields exactly when state is `consumed`. No routine `expired` update is needed: expiry is derived from immutable timestamps. Do not add `revoked` unless a separately signed revocation contract is designed.
   - Checks: normalized environment, lowercase SHA/digests, `expires_at > issued_at`, non-empty identities/reason, nonce length >= 16. Application policy remains authoritative for maximum TTL and allowlists; database constraints are defense in depth.

4. `trust_ci_promotion_events`
   - `event_id bigserial PRIMARY KEY`, nullable `promotion_id ... ON DELETE RESTRICT`, `event_type`, bounded `reason_code`, `actor`, `key_id`, `correlation_id`, sanitized `details jsonb`, `created_at`.
   - Append-only event types include `promotion.accepted`, `promotion.rejected`, `promotion.consumed`, `deployment.completed`, `deployment.failed`, and `deployment.reconciled`. Store no raw signature, bearer credential, private material or unbounded request body.

Do not overload `trust_ci_approvals`: that table is PR/base/head/scope-shaped and reusable while unexpired; production promotion is a different, consume-once authority.

## Indexes and expected plans

- Acceptance/provenance resolution:
  - unique merge index `(repository, protected_ref, merged_commit_sha)`;
  - unique artifact index `(repository, merged_commit_sha, artifact_sha256, policy_digest)`;
  - unique promotion identity indexes already supplied by PK, `nonce`, and `payload_sha256`.
- Consumption lookup needs a partial covering B-tree:

  ```sql
  CREATE INDEX trust_ci_promotions_consumable_idx
      ON trust_ci_promotions
        (repository, merged_commit_sha, artifact_sha256,
         target_environment, policy_digest, expires_at, promotion_id)
      WHERE state = 'accepted';
  ```

  Equality on the five signed bindings plus `expires_at > statement_timestamp()` should produce an index scan over a very small candidate set. Do not use `now()` in a partial-index predicate because PostgreSQL requires immutable index predicates.
- Operations/reconciliation:
  - `(state, expires_at)` partial where `state='accepted'` for expired/unconsumed monitoring;
  - promotion events `(promotion_id, created_at, event_id)`;
  - correlation lookup `UNIQUE(correlation_id, event_type)` only for event types whose idempotence semantics are defined, otherwise a normal index.
- Before rollout, capture `EXPLAIN (ANALYZE, BUFFERS)` for exact consume, accepted-but-expired reconciliation, and per-promotion audit queries at projected high-cardinality volumes. Alert if consume stops using the tuple index. JSONB does not need a GIN index in v1 because authorization must use typed columns, not arbitrary payload queries.

## Transaction semantics

### Accept

Perform structural/cryptographic checks before opening the transaction, then use one short database transaction:

1. Resolve and `SELECT ... FOR KEY SHARE` the exact merge and artifact evidence; join the source job/attestation and require `status='passed'`, matching repository/commit/policy epoch and non-mutable provenance.
2. Insert `trust_ci_promotions`; unique constraints arbitrate concurrent ID, nonce and canonical-payload replay.
3. Insert exactly one `promotion.accepted` event.
4. Commit and return `201`. Any missing/mismatched evidence or audit insert failure rolls back the envelope and returns denial. A unique violation maps to `409`; PostgreSQL unavailability maps to `503`, never an in-memory fallback.

Rejected attempts that never produce a promotion row should be recorded through a separate bounded audit transaction after classification. Failure to persist a security-relevant rejection must increment a metric/page signal; it must never turn the rejection into acceptance.

### Consume once

Expose consumption only to a dedicated deploy identity, preferably through a migrator-owned function with tightly granted `EXECUTE`, not general API `UPDATE` privilege. In one transaction:

```sql
WITH consumed AS (
    UPDATE trust_ci_promotions
       SET state = 'consumed',
           consumed_at = statement_timestamp(),
           consumed_operation_id = $6
     WHERE repository = $1
       AND merged_commit_sha = $2
       AND artifact_sha256 = $3
       AND target_environment = $4
       AND policy_digest = $5
       AND state = 'accepted'
       AND issued_at <= statement_timestamp()
       AND expires_at > statement_timestamp()
     RETURNING promotion_id
)
INSERT INTO trust_ci_promotion_events (...)
SELECT ..., 'promotion.consumed', ... FROM consumed
RETURNING promotion_id;
```

Require exactly one returned row; zero or multiple rows deny. To make "multiple" impossible, either include `promotion_id` in the consume request or add a uniqueness rule permitting only one live accepted authorization per exact tuple. Prefer explicit `promotion_id` plus all signed bindings, because PostgreSQL cannot express time-dependent uniqueness safely. Concurrent consumers serialize on the selected row; exactly one transitions from `accepted`.

Consumption happens immediately before the first production side effect. A crash after consume is deliberately fail-closed: do not unconsume and do not automatically consume another envelope. Reconcile the external system using `consumed_operation_id`; append completion/failure/reconciliation events.

## Lock and migration impact

- Creating new tables, functions, sequences and indexes does not rewrite or scan existing business tables. Foreign keys acquire brief `SHARE ROW EXCLUSIVE` locks on new tables and lighter referenced-table locks; deploy migration before starting binaries and keep `lock_timeout`/`statement_timeout` bounded.
- Avoid `ALTER` on large existing tables in `004`. A nullable promotion FK added to `trust_ci_events` would still take an `ACCESS EXCLUSIVE` metadata lock, so the dedicated event table is safer and clearer.
- Do not use `CREATE INDEX CONCURRENTLY` inside the current migrator: it executes all migrations in one transaction and PostgreSQL forbids concurrent index creation there. New empty tables make ordinary index creation low risk.
- Migration role grants must be explicit: API/promotion-submitter gets only required `SELECT` plus insert capability through a narrowly scoped acceptance function; deploy consumer gets only `EXECUTE` on consume/reconcile functions; worker gets only provenance inserts it owns; backup retains `SELECT`. Revoke function execution from `PUBLIC`. No role receives `DELETE`, `TRUNCATE`, or broad table `UPDATE`.

## Retention, audit and reconciliation

- Accepted envelopes, consumption state, provenance and audit events are security records. Keep them append-only for the compliance retention window (recommend at least 400 days; make the exact duration deployed configuration). Keep nonce/payload replay tombstones at least as long as any restored backup can reintroduce old requests; safest v1 rule is no routine deletion.
- If volume later requires archival, partition only the event table by `created_at`; archive signed immutable partitions and verify checksums before detach. Never delete promotion identity/nonces while an older backup could be restored. Retention jobs must be bounded by time/row count, resumable, separately authorized and observable.
- Reconciliation queries/metrics: accepted but unconsumed past expiry; consumed without terminal deployment event after an SLO; duplicate operation IDs; event/promotion count mismatches; provenance whose referenced attestation/job is absent; authorization attempts by reason code; DB errors and consume latency.
- Backup/restore drills must verify the new tables, sequences, functions, grants and uniqueness constraints. After point-in-time recovery, external deployment history must be reconciled by operation ID before accepting new production work; restoration must never reset consumed rows or nonce history.

## Rollout and recovery

1. Apply additive migration `004` under the existing migrator advisory lock. Validate schema checks, grants, query plans and current backup coverage; do not backfill historical approvals.
2. Deploy code with acceptance/consumption disabled; validate rejection and audit durability. Then enable acceptance in a non-production environment, followed by consume-before-effect canary while old PR approvals remain active.
3. Only after the production gate is proven should deployed policy move to empty PR `approval_rules` and branch protection move to the new App-owned policy-epoch check.

Application rollback disables promotion acceptance/consumption and restores the previous images/policy. The schema and records stay in place; no down migration or destructive SQL. Forward recovery adds a new checksum-locked migration, never edits `004`. If gate health is uncertain, restore the previous PR approval policy rather than bypassing production authorization.

## Required PostgreSQL evidence

- Concurrent duplicate `promotion_id`, nonce and payload submissions: exactly one accepted row and one accepted event.
- Concurrent consume with the same exact tuple/ID: exactly one success; expiry boundary, policy rotation and connection loss deny.
- Transaction rollback tests prove no promotion exists without its accepted event and no consumed state exists without its consumed event.
- Role tests prove API/deployer cannot delete, truncate, rewrite signed columns, forge provenance or append unauthorized event classes.
- Real PostgreSQL migration from an existing `001`-`003` durable store, restart persistence, backup/restore drill, mirrored migration bytes, checksum-drift rejection, constraints, indexes and `EXPLAIN` evidence.

## Blocking data decision

Before implementation, the architecture must select the authoritative producers for protected-branch merge evidence and artifact evidence. PostgreSQL can make those records immutable and atomically consume a promotion, but it cannot derive merge membership or artifact identity from caller-supplied JSON. Shipping `POST /promotions` without independently produced provenance would satisfy storage mechanics while failing the core authorization claim.
