# Data architecture analysis — existing Claw runtime upgrade

Route: `080b283b0cf3`. Inspected HEAD: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. Role: route-selected `data_architect`. This is source analysis, not an executed migration, restore drill, production inventory, or approval receipt. No live database, credential, or private runtime content was accessed; no tests or operational commands were run. Relevant product files match HEAD.

## Conclusion and compatibility

**Back up each stopped old instance before the first target-binary startup, including a provider-disabled startup.** Both old revisions (`5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` Qwen and `61a05da2bd0c9fb09db5307f53ebc99e4e94040d` Grok) expect SQLite schema v1. Target startup expands it to v2. A failed startup can already have committed the migration; failure is not evidence that the database remains v1.

| Operation | Source-supported behavior |
| --- | --- |
| Target opens genuine old v1 database | Validates exact v1 schema, adds nullable `observation_json BLOB`, sets `user_version=2`, validates v2 and runs `quick_check`; existing observations remain NULL. |
| Target backup reads v1 or v2 | Supported. It snapshots without opening `SQLiteLandingJobStore`, so backup does not migrate or recover jobs. Prefer the matching old tool for each pre-upgrade snapshot. |
| Target restores an old snapshot | Supported with its original manifest digest, identical configured landing/publication/artifact paths, valid private ownership, absent destination roots, and `live_enabled=false`. Restore copies files unchanged; a v1 snapshot remains v1 until a host/store opens it. |
| Old binary opens upgraded v2 database | Rejected as unsupported schema. There is no down migration. Do not change `user_version`, drop columns, or rewrite retained evidence to enable downgrade. |
| Old binary restores pre-upgrade snapshot | Supported using the matching old tool and original profile/config with `live_enabled=false`. Restore alone does not start a host. |

The backup manifest stays schema v1 at the target. Only the backup database-identity predicate changed between the old revisions and target; the restore implementation is unchanged. Publication SQLite remains application ID `0x4C355055`, schema v1, and its store/filesystem implementation has no diff from either installed revision. Landing application ID remains `0x4C354C35`.

Sources: `factory/src/adaptive_factory/landing_sqlite_store.py:32,354,584`; `factory/src/adaptive_factory/landing_backup.py:118,180,239`; old objects inspected with `git show`; `delivery/src/adaptive_delivery/landing_publication.py:20,111`.

## Migration, locks, and startup effects

- Migration executes `ALTER TABLE landing_jobs ADD COLUMN observation_json BLOB` and the version update in one `BEGIN IMMEDIATE` transaction. It introduces no index, table rebuild, or historical-observation backfill; existing tenant/repository/job primary keys and command foreign keys remain. Historical NULL observations cannot become provider-fallback authority.
- The process first holds nonblocking exclusive `landing.writer.lock` for its connection lifetime. Backup takes that same lock and publication's `.intent-writer.lock` before creating a snapshot destination. A writer conflict must stop the operation; never delete lock files. Their continued presence after shutdown is normal.
- Store connections use WAL, FULL synchronous, foreign keys, and a default 5-second SQLite busy timeout. This timeout bounds contention, not the total schema/integrity scan. `quick_check` and recovery selection may scan data; live volume and startup duration were not measured.
- The ownership lock is advisory. Stop and drain all legitimate writers instead of assuming it prevents unrelated raw SQLite access. Publication target mutation has its separate lock and is outside this deployment scope.
- Provider-disabled host composition still creates the store before selecting the unavailable provider. Startup may move at most 100 `accepted`, `normalizing`, `generating`, or `evaluating` jobs to `needs_human`, with respective reasons `input_unavailable_after_restart`, `provider_outcome_ambiguous`, or `local_run_interrupted`. Quarantine startup cleanup follows store acquisition. It does not replay providers. Do not repeatedly restart to process an unknown backlog.
- SQL migration commits before final integrity verification and recovery. Preserve all failure state and use a compatible disabled binary for containment before choosing data rollback.

Sources: `landing_sqlite_store.py:118,339,354,386,477,499`; `factory/src/adaptive_factory/landing_server.py:65`; `delivery/src/adaptive_delivery/landing_filesystem.py:52`; `engineering/runbooks/l5-provider-failover.md:88`.

## Required backup sequence

These commands are a reviewable procedure, not commands executed by this analysis. Config paths below are the documented installed paths; confirm they still match service metadata. Keep snapshots outside all three included roots, the control repository, and the landing source. Privately preserve old units and old nonsecret host configurations before replacement, without printing credentials or actor contents. Retain distinct per-service roots and original absolute artifact paths.

1. Pause admission and drain in-flight work. Preserve unresolved job IDs for reconciliation. Stop both service units and any separate publication writer; confirm no processes remain. The source unit has `TimeoutStopSec=360`, `KillMode=control-group`, and `Restart=no`; a stop timeout or forced termination is a reconciliation signal.

```sh
sudo systemctl stop adaptive-l5.service adaptive-l5-grok.service
```

2. Ensure `/var/lib/adaptive-l5/backups` and `/var/lib/adaptive-l5-grok/backups` exist as `adaptive-l5:adaptive-l5`, mode `0700`. Each destination below must be absent. As the data owner, use each exact old release:

```sh
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/venv/bin/adaptive-landing-state backup --config /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/landing-host.json --snapshot /var/lib/adaptive-l5/backups/pre-upgrade-26a0d3db8fa9-20260919
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/61a05da2bd0c9fb09db5307f53ebc99e4e94040d/venv/bin/adaptive-landing-state backup --config /etc/adaptive-l5/grok-host.json --snapshot /var/lib/adaptive-l5-grok/backups/pre-upgrade-26a0d3db8fa9-20260919
```

3. Require exit 0, `status=snapshot_saved`, `provider_replay=false`, and a final `manifest.json` for both. Retain each returned `manifest_sha256` separately in the deployment record. A partial directory or absent manifest is not a backup. Check the manifest's summed entry sizes fit restore's two-pass budget; backup success alone does not establish restore feasibility.
4. Only then install/switch the staged configs and units. Retain the same data roots; select `qwen-omni-intl` and `grok-vision`, initially `live_enabled=false`. Start the target and validate readiness/history through the existing authenticated API. Provider qualification is a later, bounded action. Keep original profiles/configs for downgrade: the old Qwen config loader rejects `qwen-omni-intl` even when disabled.

The snapshot uses SQLite backup API, capturing committed WAL pages into standalone DELETE-journal databases. It includes optional publication SQLite plus exact retained artifact ZIP/sidecar files; it excludes credentials, quarantine/raw inputs, scratch, source checkouts, caller journals, and external publication targets. Preserve those separately in place as applicable. Do not copy only the live `.sqlite3` file.

Bounds: 4,096 entries, 512 MiB per file, 4 GiB cumulative byte accounting, one 180-second deadline. Restore hashes then copies within the same budget, requiring summed payload at most 2 GiB and sufficient real time/disk space. Files must be data-owner regular single-link `0600`; roots private `0700`. Do not weaken these checks to finish deployment.

## Rollback procedure

Prefer keeping the compatible target binary with provider execution disabled while investigating. If an old-binary rollback is necessary:

1. Pause submissions and stop both affected service/publication writers. Preserve current v2 state, publication and artifact roots at explicitly named inactive paths; also preserve configs, job IDs, and any caller journal for later reconciliation. Moving an entire data parent can accidentally move its `backups` subtree; move the three exact configured roots individually. Destination paths must be absent and nonoverlapping; do not overwrite or delete anything.
2. Prepare private copies of the original configs with only `live_enabled=false`, keeping all original roots. Qwen's original profile is `qwen-intl`; Grok's is `grok-vision`. Original configured landing/publication/artifact destinations must all be absent before restore. Other required host paths remain intact.
3. Run the old release's matching `adaptive-landing-state restore` with its private rollback-config path, the exact pre-upgrade snapshot path above, and the separately retained digest:

```sh
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/venv/bin/adaptive-landing-state restore --config /ABSOLUTE/PRIVATE/QWEN-ROLLBACK-CONFIG.json --snapshot /var/lib/adaptive-l5/backups/pre-upgrade-26a0d3db8fa9-20260919 --manifest-sha256 QWEN_SAVED_MANIFEST_SHA256
sudo runuser -u adaptive-l5 -- /opt/adaptive-l5/releases/61a05da2bd0c9fb09db5307f53ebc99e4e94040d/venv/bin/adaptive-landing-state restore --config /ABSOLUTE/PRIVATE/GROK-ROLLBACK-CONFIG.json --snapshot /var/lib/adaptive-l5-grok/backups/pre-upgrade-26a0d3db8fa9-20260919 --manifest-sha256 GROK_SAVED_MANIFEST_SHA256
```

Those rollback-config paths/digests are explicit placeholders to bind before an operation. The target release's same CLI can also restore either old snapshot using a target-readable disabled config with identical roots; it will not migrate during restore. For binary downgrade, do not start the target on that restored root before switching to the old binary, since doing so upgrades it again.

4. Require `status=restored_inactive`, `provider_replay=false`, and `publication_reconciliation_required=true`, then restore the old units/config binding and start disabled. Preserve partial roots after restore failure and keep services stopped. Never rewrite retained absolute artifact paths. Restoration excludes later jobs from the active view, so reconcile preserved post-upgrade work without replay; it does not revert an external published site.

## Focused validation to run once

Use the target's Python environment with its pinned dependencies, from its repository root. These tests use disposable fixtures and synthetic actors; they need no live config, database, provider, or credential:

```sh
PYTHONPATH=factory/src:delivery/src python -m unittest -v \
  factory.tests.test_landing_failover_backend.BackendObservationTests.test_v1_store_migrates_without_fabricating_historical_observations \
  factory.tests.test_landing_failover_backend.BackendObservationTests.test_observation_and_terminal_state_survive_restart_atomically \
  factory.tests.test_landing_sqlite_store.SQLiteLandingJobStoreTests.test_schema_identity_inventory_keys_foreign_key_and_strictness_are_exact \
  factory.tests.test_landing_sqlite_store.SQLiteLandingJobStoreTests.test_startup_recovery_is_bounded_and_never_replays_processing_work \
  factory.tests.test_landing_backup
```

The backup suite covers committed WAL pages, actual landing/publication writer conflicts, inactive round trip, populated publication intent preservation, existing-root refusal, two-pass budget refusal before creating roots, link/inventory/tamper failures, and offline import boundaries. Existing tests separately cover v1 migration and current snapshot restore; they do not directly exercise an old-binary-produced snapshot through the target CLI. Old-snapshot compatibility above is source-derived, not a claimed completed cross-version drill.

## Stop conditions and handoff

Stop dependent activation on any missing/incomplete pre-upgrade snapshot, unknown or mismatched manifest digest, restore-size/deadline risk, unexpected path/owner/schema/identity, active writer, SQLite integrity failure, failed stop/drain, missing expected historical artifact, or unexplained pending/ambiguous work. Backup/restore CLI returns exit 2 and `needs_human` on failure; some non-BackupError failures are deliberately reported only as `snapshot_unavailable`, so do not interpret that as permission to bypass locks or path checks.

Row volume, artifact sizes, exact current private roots, actual backup success, and elapsed migration duration remain for the authorized deployment coordinator to establish. No large-table performance or production recovery qualification is claimed. Shared-memory fact for the coordinator: provider-disabled startup still mutates durable state, so migration safety depends on a complete old snapshot before any target launch.
