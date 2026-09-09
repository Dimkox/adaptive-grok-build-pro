# Data architecture analysis: M5 execution persistence

## Scope and inspected identities

This analysis is bound to route `6c578a9933b3`, immutable M4 source commit
`67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4` (tree
`399c65e7c65626f3d5236cae1bce009c5d3a9714`) and the canonical M5 reference
`3940267ac5754ad07a047894102015d33eb759b1` (tree
`4646582a7c5ff6f08ee7e8462687da400459b08d`). Inspection was read-only; no
database, network, provider or external operation was performed.

The thirteen packaged M4 migrations are byte-for-byte identical at both
identities (all Git blob IDs and content SHA-256 values match). Therefore
`001_initial.sql` through `013_persisted_infrastructure_retry_limit.sql` are a
closed migration history and must not be edited, renamed, reordered or
re-created during the M5 restack.

The final canonical M5 migration identities are:

| Version | File | SHA-256 |
| --- | --- | --- |
| 014 | `014_execution_plane.sql` | `997f3010ebdfc203931b6a629ec79d515e10b6614f3c13e0763f8a16cbea5b01` |
| 015 | `015_execution_canonical_persistence.sql` | `e2c8ca88a7a7013da29a8d0ab440ccb5791100400b4f75b5ad5e815ba6fb0c94` |
| 016 | `016_contract_execution_canonical_persistence.sql` | `3b6d6104a0074b5357915583385aa433f71ccf9755f101cf9a7d6322fcc75b54` |
| 017 | `017_execution_recovery_topology.sql` | `4114b0a1d3b5e8ab86227b0bd2dd459d62d023d033d1ff2b9b5bdc66aaa07da1` |

These migrations have not been published. The safe port is nevertheless the
final four-file sequence above, not any intermediate form from the historical
M5 commits. Once the sequence is applied outside a disposable local database,
future changes must use migration 018 or later.

## Minimal safe semantic-port order

1. Preserve the current M4 store, transition engine, history API and migrations
   001-013 as the base. Do not replace `store.py` with the older M5 reference
   file; the reference predates material M4 lifecycle/history hardening.
2. Add the final M5 contracts and model types required by persistence, then add
   the exact migrations 014-017 in numeric order. Update `migrations.py` only
   with the additive `factory_artifact_attestor` role boundary and its separate
   expected login/membership validation. Runtime and attestor login identities
   must remain distinct.
3. Port the execution persistence surface into the current M4 store in vertical
   order: execution material and start; stage advance; proposal context,
   canonical replay and commit; artifact attestation capability store; trusted
   snapshot and atomic finalization; recovery discovery, claim and cleanup;
   combined metrics. Reuse the current M4 transaction and transition helpers.
4. Integrate the two existing-state touchpoints last: cancellation/supersession
   must project an unfinished execution to `cancelled`, and expired-run recovery
   must close the M4 run/allocation through the current canonical M4 path before
   creating an execution cleanup claim. Both projections remain in the same
   transaction as their M4 state change.
5. Enable M5 execution composition only after schema version 17, runtime login
   validation and artifact-attestor login validation all pass. Provider or
   workspace unavailability must leave durable M4/M5 state unchanged or in the
   explicit retry/recovery state.

Migration-specific order is not compressible:

- **014 — base execution topology:** creates one execution packet, manifest and
  eventual workspace result per run; append-only stage events; monotonic,
  replayable proposals; and fenced `start`, `advance`, `propose` and
  `finalize` database functions.
- **015 — canonical expand/hardening phase:** installs canonical JSON/hash
  validation, strict closed envelopes, artifact attestations and the isolated
  attestor capability role, then replaces the execution functions with the
  authoritative versions. It intentionally takes `ACCESS EXCLUSIVE` locks on
  proposals/results and refuses legacy finalized results or unattested artifact
  proposals before any durable DDL remains.
- **016 — contract phase:** only after 015, removes the superseded 64 KiB
  proposal-body constraint and permits the same trusted snapshot digest to be
  evidence for separately fenced runs. The canonical 1 MiB proposal bound and
  per-run result uniqueness remain.
- **017 — recovery overlay:** requires PostgreSQL 17, installs bounded recovery
  jobs/claims/outcomes, claimable-work indexes, execution counters and combined
  metrics. It takes `SHARE ROW EXCLUSIVE` locks on execution write tables;
  execution writers must be quiescent while it is applied.

For a direct 013-to-017 upgrade, the migrator's advisory lock and single
transaction mean 014's new tables are empty when 015 executes, so no M5
backfill is required. A previously populated local schema 014-016 is a separate
upgrade case and must satisfy the explicit 015 guards. Migration 017 defines a
zero metrics epoch: pre-017 execution rows are deliberately not counted, and
must not be synthesized into the counters.

## Critical schema and data invariants

- **Immutable lineage:** `schema_migrations` stays contiguous, checksum-bound
  and drift-detecting. No migration may modify the bytes or semantics of
  001-013.
- **Cross-identity binding:** every M5 row is tied to the authoritative M4
  `(task_id, run_id)` pair. Packet, manifest, proposal and result digests are
  separate identities; `legacy_packet_digest` continues to bind the M4 lease
  without being substituted for the immutable M5 task-packet digest.
- **Cardinality:** at most one packet, one manifest and one workspace result
  exist per run; at most one terminal proposal exists per run; proposal
  sequence and idempotency key are unique within a run; stage sequence is
  unique and strictly append-only per manifest.
- **Fencing and atomicity:** execution mutation requires the current task/run,
  owner, fence, legacy digest, unreleased allocation, live lease and task
  deadline. Finalization atomically cross-binds the terminal proposal, trusted
  workspace snapshot, usage observations, artifact attestations, result
  digest, M4 disposition, attempt completion, run release, capacity release
  and task transition. No partial terminal state is acceptable.
- **Canonical evidence:** packet, manifest, proposals, snapshot and result use
  exact-key validation, domain-separated canonical hashes and bounded JSON.
  Worker-supplied digests cannot select or redefine trusted snapshot facts.
- **Artifact authority:** only the dedicated `factory_artifact_attestor`
  capability may record an attestation. Runtime cannot read or write the
  attestation table directly; an artifact proposal consumes exactly one
  matching, unconsumed attestation for the same run, sequence, fence,
  repository, workspace, path, class, digest, size and media type.
- **Tenant/repository isolation:** repository identity is inherited from the
  accepted M4 task and checked against packet, workspace and artifact facts.
  Direct table authority remains revoked; server-side repository authorization
  must precede all task/result reads. Cross-repository guessed identifiers must
  not expose rows.
- **Recovery safety:** a run and its capacity allocation must agree on release
  state. A finalized result is never recoverable as an orphan. Each run has one
  recovery job, each claim has a monotonically increasing fence and unique
  token, and each claim has at most one immutable outcome. Expired cleanup is
  at-least-once but stale claims cannot complete newer work.
- **Bounded operation:** recovery accepts pages of 2-100 and claims of 1-300
  seconds; database sessions must enforce statement, lock and PostgreSQL 17
  transaction timeouts. Recovery ordering is keyset-based over
  `(updated_at, run_id)` with a separate retry lane, and the claimable-job index
  is `(next_claim_at, updated_at, run_id) WHERE status <> 'succeeded'`.
- **Forward recovery:** there are no down migrations or destructive backfills.
  Before activation, rollback is disabling M5 composition while retaining the
  schema and evidence rows. A failed migration transaction must leave the
  prior version/checksum set intact; any later correction is migration 018+.

## Focused PostgreSQL evidence required before acceptance

Use one disposable PostgreSQL 17 database named by
`FACTORY_TEST_DATABASE_URL`; never point these tests at shared or production
state. The minimal evidence set is:

```bash
cd factory
python3 -m unittest -v \
  tests.test_migrations.MigrationTests.test_packaged_migrations_are_contiguous_and_factory_only \
  tests.test_migrations.MigrationTests.test_execution_migrations_are_immutable_forward_only_and_capability_shaped

python3 -m unittest -v \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_schema14_populated_execution_upgrades_forward_to_canonical_finalize \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_schema15_rejects_legacy_finalized_rows_before_any_ddl_or_release \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_schema15_rejects_unattested_schema14_artifact_without_residue \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_populated_schema16_to_17_is_atomic_zero_epoch_and_forward_only \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_runtime_cannot_persist_noncanonical_packet_or_manifest \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_finalize_atomically_derives_m4_failure_and_cross_binds_result_bundle \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_finalize_requires_exact_consumed_artifact_attestation \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_recovery_claim_atomically_orphans_expired_execution_and_denies_late_work \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_expired_cleanup_claim_is_at_least_once_but_durably_fenced \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_cancel_and_fresh_recovery_race_is_bounded_and_single_terminal \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_recovery_definers_reject_unbounded_runtime_sessions \
  tests.test_execution_persistence_postgres.ExecutionPersistencePostgresTests.test_attestor_proposal_probes_use_bounded_partial_and_sequence_indexes

python3 -m unittest -v \
  tests.test_runtime_capability_postgres.RuntimeCapabilityPostgresTests.test_runtime_store_requires_exact_capability_login_before_set_role \
  tests.test_runtime_capability_postgres.RuntimeCapabilityPostgresTests.test_runtime_store_rejects_swapped_dual_and_direct_authority
```

Additionally retain the existing M4 PostgreSQL integration tests for intake,
claim, accounting, capacity, cancellation, reconciliation and lifecycle
history. Their failure is a regression, not an M5 optimization item. Stop the
upgrade on checksum drift, a non-PostgreSQL-17 server, an unsafe capability role
or login membership, either 015 legacy-data guard, lock/statement timeout, or
any partial state after an injected failure.

## Disposition

The canonical M5 data design is a safe additive port onto exact M4 provided the
final 014-017 bytes are retained as a sequence and only the M5 persistence
surfaces are semantically merged into the newer M4 store. Wholesale replacement
of the current M4 store is unsafe because it would discard later M4 transition
and history guarantees. No schema execution or production readiness claim is
made by this analysis.
