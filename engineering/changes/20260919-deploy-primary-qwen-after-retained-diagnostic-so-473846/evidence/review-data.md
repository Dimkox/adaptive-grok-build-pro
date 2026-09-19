# Independent data review — PASS-for-prepared-scripts

Route `473846f79243`; role `data_reviewer`; scope: prepared primary-only continuation scripts and plan. Both original findings are resolved; no unresolved data blocker remains. No runtime acceptance or execution authority is claimed.

| Reviewed file | SHA-256 |
| --- | --- |
| `upgrade-primary.py` | `defd025a98d346e7fc57b36928639b087d92515fe11a6e7bfa550fc59e692157` |
| `rollback-primary.py` | `0a636c89bd69e20e9ee8cda0ada916cbb387dd721e39181e642cde487a99282d` |
| `accept-primary.py` | `6b40bf6802eec78fe04967c8f2efc503d9ad63ecd1420f35f85b53435a13b898` |
| `read-restored-qwen.py` | `a1fff81289f5bdab033b7943f03cfb8b1bd81ede96fe11c353050825dec91c4e` |
| `operations-plan.md` | `8473f8742ce885b5a6ae1ed2ba19de328d13dcae604f4b9f6af8689edfd5b68f` |

Reviewed the actual scripts, their differences from `080b28`, prior upgrade/rollback data/security/release reviews, current analysis and requirements, snapshot/restore implementation, migration and startup recovery. All four final scripts parse. The historical reader is byte-identical to `080b28`. The recorded 13 passing offline checks match these script hashes; inspected their harness without rerunning its file-writing entrypoint.

## Original findings and disposition

1. **Resolved P1 — Snapshot/baseline binding.** The original script captured counts before the backup CLI acquired its locks without comparing the copied database, permitting recovery writes during disabled target startup before detecting drift. Final `upgrade-primary.py:133–136` compares both the actual snapshot landing database and current stopped store with the safe schema-1 terminal baseline before recording `backup.json`. Lines 154–155 repeat both comparisons before installing/starting the target. The error handler resumes old code only when current metadata still equals that safe baseline; changed or ambiguous state stays stopped.

2. **Resolved P2 — Synthetic-job rollback binding.** The original aggregate-only guard accepted the same terminal delta from an unrelated job when the synthetic job was absent; a tiny in-memory probe reproduced it. Final `rollback-primary.py:37–64` queries the deterministic job, requires exactly one row and its selected terminal state, and validates actor, repository, body and base identity against the private target-bound submission marker; `no_new_job` requires absence. Restore calls this under both existing writer locks and freezes the observed job plus `backup.json` SHA before renames. Activation rereads the preserved database and requires exact frozen-record equality. The aggregate guard remains an additional concurrency check.

Independent follow-up probe executed the actual AST-extracted `bound_job` with an in-memory SQLite database and mocked private marker I/O: the original unrelated-job case is rejected, the correct terminal job returns its bound record, and wrong terminal, false absence and pending-job cases are rejected. No operational entrypoint or production database was executed; the probe wrote no files.

## Confirmed safeguards

- Fresh snapshot, saved-operation, rejected-root and job names derive from target SHA plus route suffix and do not reuse earlier `26a0d3` locations. Backup consumes the matching old binary; the returned manifest digest and complete inventory protect landing/publication SQLite and artifacts. The conservative payload bound remains below the two-pass restore budget.
- Product backup/migration files have no diff between `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960` and candidate `a4023258047a03e1176daa3a35695c9d9b49f8be`. The migration adds nullable `observation_json` and changes schema 1 to 2 without historical backfill. Both old and new startup perform recovery, making the stopped ambiguity boundary necessary.
- Containment stops the unit and disables execution without restarting. The rollback rejects aggregate pending states and rechecks metadata after confirmed stop and both locks. Existing service-owned mode-0600 regular single-link landing/publication lock files are opened without following links or creating replacements; inode checks and retained descriptors cover freezing, every rename and restore.
- Restore preserves the complete new roots, passes the fresh manifest digest to the old disabled restore CLI, requires `restored_inactive` and `provider_replay=false`, then compares schema-1 metadata before and after old-binary disabled readiness. Activation rechecks the stopped baseline before restoring original byte-identical unit/config and checks preserved schema-2 counts afterward.
- The acceptance marker permits one POST and leaves a crash/ambiguity fenced from replay; retained same-job receipt facts precede acceptance assertions. Final acceptance also checks body digest/length and observation profile/model. Observe performs no POST. The historical reader pins the old job/artifact and explicitly disclaims new-profile acceptance.

Only this report was written. No credentials, provider calls, live database reads, service operations or broad tests were performed. The final plan records merged target `f12807c2b75750072ba768fc95ed492362ae6489` and its source-gate evidence; this local data review does not replace that external authority or exact operational grants. Actual snapshot, migration, acceptance and recovery results remain to be observed by the controller.

## Representation-only archive acceptance

Confirmed all four current script mappings in `script-archive-index.json` (SHA-256 `5888decf45eb1b12473a05b891afa2ef9a298aa9b1ad36a61eaba6ced62c5e74`): each original `.py` path maps to its `.py.txt` archive, whose actual bytes retain the reviewed SHA-256 above; the original executable paths are absent. PASS-for-prepared-scripts remains bound to those unchanged bodies. The architecture records separately granted external Claw execution and excludes archived semantics from repository fitness claims. No tests, semantic reanalysis or runtime operations were repeated; activation remains pending.
