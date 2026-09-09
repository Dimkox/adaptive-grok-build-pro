# M6 data architecture ruling

## Bound identities

- Target base: M5 `85cd4343143915ce9342634e7fe81886b6394871`, tree
  `779e0b99a5e489a2c91e866662cc1f31ae73b4c3`.
- Canonical M6 reference: `2d2360cd6f2a19ad3328d468073a52927691b112`.
- Canonical M6 migration: `014_semantic_validation_bridge.sql`, 2,154
  lines, content SHA-256
  `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70`.
- Inspection was read-only. No database or external operation was performed.

## Migration ruling

Port the final SQL content from canonical M6 unchanged as:

`factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql`

Version 018 is mandatory because exact M5 already owns immutable migrations
014-017. Migrations 001-017 must retain their current names and bytes. The SQL
contains no hard-coded reference to migration number 014, so semantic
renumbering requires a filename/test/evidence update only; database object and
function names do not change.

`discover_migrations()` derives the version and name from the filename but
hashes only the raw SQL bytes. Consequently the expected applied record is:

```text
version=18
name=018_semantic_validation_bridge.sql
sha256=33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70
```

Do not port canonical M6 `migrations.py`: that older file removes M5's runtime
and artifact-attestor role validation and its guarded migrator parameters.
Current M5 `migrations.py` already discovers version 018 automatically. Any
semantic-role support added there must be strictly additive and must not weaken
the existing M5 role boundary.

## SQL and store compatibility

Migration 018 is additive over the M5 final schema. Its external dependencies
exist on the target base: `tasks`, `accepted_intents`, `runs`, `attempts`,
`workspace_results`, execution packets/manifests/proposals/artifact
attestations, M0 authority observations and `execution_contract_hash`.

It adds two bounded `tasks` columns with the constant default `legacy`, new
append-only semantic tables/functions/metrics, and three disjoint NOLOGIN
capability roles. It contains no destructive migration or semantic-evidence
backfill. The `ALTER TABLE factory.tasks` requires a table lock; apply with M5
writes quiesced and retain the existing five-second migration lock/statement
bounds. Failure must leave schema version 17 and all M5 rows intact through the
existing single migration transaction.

Port only the new semantic coordinator, validator and adjudicator persistence
surfaces. Do not replace current M5 `store.py` with canonical M6 `store.py`,
which predates the integrated M5 transaction, recovery and lifecycle code.
Semantic-merge these two existing-store touchpoints:

1. `intake` persists `intake_actor_kind` and `intake_actor_id` and calls
   `semantic_repair_intake_status` before accepting a repair child.
2. `claim` calls `semantic_task_claimable` while retaining all current M5
   owner, role, fence, capacity, deadline, recovery and transaction checks.

Renaming the migration does not change any store SQL function signature.

## Critical invariants

- One immutable subject is bound to one exact M5 workspace result and its
  packet, manifest, terminal proposal, snapshot, repository, run, fence and
  exact SHAs.
- Semantic command replay is keyed by `(operation, idempotency_key)` and rejects
  a changed request or changed resource digest.
- Subjects, assignments, findings, coverage, verdicts, directives, repair
  proposals, child bindings, escalations, recovery facts and metrics are
  append-only; update/delete remains denied by triggers and grants.
- Coordinator, validator and adjudicator logins have exactly one disjoint
  capability membership and no direct table authority.
- A subject has at most one verdict; repair cycles are unique per subject and
  limited to 1-3. A fourth requested cycle persists `needs_human`, never a new
  child proposal.
- Repair intake must bind the exact proposal digest, repository, parent head,
  dedicated broker identity, original writer and fresh M0 authority. Ordinary
  intake remains unchanged, and no crafted API source may enter the repair
  claim path.
- The final index-aware SQL from `2d2360c` must be used; earlier variants have
  known repair digest/claim lookup regressions.

## Only critical focused database evidence

Run against one disposable PostgreSQL 17 database only:

```bash
cd factory
python3 -m unittest -v \
  tests.test_migrations.MigrationTests.test_packaged_migrations_are_contiguous_and_factory_only \
  tests.test_migrations.MigrationTests.test_missing_renamed_or_checksum_changed_applied_migration_fails \
  tests.test_migrations.MigrationTests.test_semantic_migration_is_additive_append_only_and_capability_shaped \
  tests.test_migrations.MigrationTests.test_semantic_evidence_functions_are_reserved_to_distinct_capabilities

python3 -m unittest -v \
  tests.test_postgres_integration.PostgresFactoryTests.test_semantic_subject_publish_is_exact_replay_safe_and_role_isolated \
  tests.test_postgres_integration.PostgresFactoryTests.test_repair_source_identity_and_claim_owner_are_atomic \
  tests.test_postgres_integration.PostgresFactoryTests.test_semantic_repair_functions_use_exact_digest_index_conditions
```

Update the existing migration-name assertion from 014 to 018. Add one focused
upgrade test, `test_schema17_upgrades_to_semantic_018_without_m5_drift`, which
applies 018 over a populated version-17 fixture, verifies the exact migration
record above, confirms existing M5 rows/digests are unchanged, and proves an
injected migration failure rolls back atomically. No broader database matrix is
required for this restack checkpoint.
