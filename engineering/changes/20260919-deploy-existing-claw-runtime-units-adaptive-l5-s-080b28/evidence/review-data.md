# Independent data review — PASS

Route: `080b283b0cf3`. Reviewer: route-selected `data_reviewer`. Target HEAD: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. Scope: the planned operational upgrade of the existing Qwen and Grok services, with primary `qwen-omni-intl`. This is a pre-cutover procedure review, not a claim that production backup, migration, recovery, or acceptance has already succeeded.

No unresolved data blocker remains in the reviewed procedure. No live database, credential, or runtime configuration was read, and no runtime operation was executed by this reviewer. Only this report was written.

## Reviewed bindings

| File | SHA-256 |
| --- | --- |
| `upgrade-operations.py` | `c76de57452fb27999dd7fdac82bfd8beb37210367560b8a7129cc6897d5ebb0e` |
| `accept-runtime.py` | `8b54e6e23187d91a09f29270d828ef00478a1a146632e5a265ad5f938fcbcb28` |
| `operations-plan.md` | `7248902063f94d775c74cef7bd6eabed3e90a5d84b74833641e6b66393aeb06e` |
| `focused-verification.log` | `1fff5e0da1f021c9384b272cc96a3f47dd057489b7f70d9b85f0bb00bfa23bbf` |
| `factory/src/adaptive_factory/landing_backup.py` | `65fbd1be40bf1ef954231a35605e2958f636b6e3f9fd0471f0d88eb4b1e36ff0` |
| `factory/src/adaptive_factory/landing_sqlite_store.py` | `378e3eb9ee47e086c21da28768a447fdd65392acfcdd509ed61fc8b44e666caa` |

Also inspected `analysis-data_architect.md`, `preflight.md`, installed package verification, the actual host composition/configuration, publication/filesystem implementation, receipt validation, relevant tests, and the backup diff from each old service revision. Relevant product sources have no diff from the target HEAD. Both operator scripts parse successfully. The recorded installed-interpreter run contains 19 passing migration, restart, backup, writer-conflict, tamper, and restore-budget tests; this reviewer inspected that log without claiming an independent rerun.

## Findings and disposition

1. **Resolved: pre-stop observation raced admission.** The initial script saved job counts before stopping the unit. Final `upgrade-operations.py:101–106` confirms the stopped unit, reads counts again, and rejects pending `accepted`, `normalizing`, `generating`, or `evaluating` work. The saved baseline now belongs to the stopped store.
2. **Resolved: ambiguous stopped work could trigger automatic recovery before backup.** The post-stop metadata/pending check is outside the exception handler that resumes the old service. A failure of this check now leaves the service stopped. This matters because the old binary also performs startup recovery and quarantine cleanup; being the old binary does not make its restart observational.

## Data safety assessment

- **Ordering:** the matching old binary creates each snapshot before any target host launch, including provider-disabled launch. Final `offline` requires the completed backup record, inactive old unit, preserved original unit bytes, and disabled target config. The services are upgraded independently, Grok first, while the other service remains available.
- **Stopped writers:** the operation verifies inactive service state and zero pending jobs after stopping. The backup itself acquires the landing lifetime writer lock and publication intent lock before creating the snapshot root. Lock conflicts fail rather than being bypassed. These are advisory locks for legitimate writers; no separate writer may be started during the sequence.
- **Complete snapshot and budget:** the old CLI captures committed WAL pages through SQLite backup, normalizes the snapshot to a standalone database, includes publication SQLite when present and the artifact inventory, and writes/fsyncs the final manifest only after completion. The operator requires `snapshot_saved`, verifies its manifest digest, and rejects payloads at or above 1,900,000,000 bytes. Two payload passes therefore stay below the restore implementation's 4 GiB byte budget. The original 512 MiB/file, 4,096-entry, and 180-second bounds remain enforced. This size check does not independently prove disk headroom or restore duration.
- **Schema and retained history:** target startup validates genuine v1 schema, adds only nullable `observation_json`, and sets v2 in one immediate transaction. It then validates the v2 schema and integrity. There is no table rebuild, new index, historical backfill, provider replay, or fabricated historical observation. Landing identity remains `0x4C354C35`; publication remains schema v1. Old binaries reject v2, including when a target startup failed after committing migration.
- **Recovery and containment:** the plan correctly keeps the compatible target available with provider execution disabled as containment. A binary downgrade preserves the three exact upgraded roots separately, restores the old snapshot into absent original paths with its saved digest and original disabled profile, and validates through an old-binary unit bound to that disabled config before restoring the original live unit. Later work remains preserved for reconciliation; external publication targets and raw quarantine inputs are outside the snapshot. Use the actual snapshot path/digest in `backup.json`, not the earlier analyst command placeholders.
- **Acceptance evidence:** the client pins profile and source, uses a fixed idempotent job and no transport retries, validates the sealed durable attempt, and requires the v1 job/state/artifact digest to agree with the v2 artifact. Observe mode performs no POST, and `live_url` must remain null.

## Required execution evidence

For each service, retain the successful snapshot manifest digest, actual path and payload size, and frozen stopped-store counts. Before activation, require identical job counts by state after disabled startup and schema `1 → 2`; target readiness also depends on its exact schema/application identity validation. After finite acceptance, reconcile only the fixed synthetic job delta (normally one additional `artifact_ready` row); all historical state counts must remain unchanged. The later observe-only read must preserve the same accepted artifact/attempt bindings. Any unexpected count change, pending state, incomplete snapshot, integrity error, or resource/deadline failure stops dependent activation.

Production volume, free space, elapsed migration/restore time, and actual runtime outcomes were not measured by this review. No cross-version live restore drill, large-volume qualification, or external pilot acceptance is claimed. This PASS is bound to the scripts and procedure above and does not replace operational grants or external Trust CI authority.
