# Independent Qwen rollback data review — PASS

Route `080b283b0cf3`; role `data_reviewer`; source HEAD `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. This reviews the bounded rollback procedure after the rejected Qwen acceptance. It does not assert that rollback has run. No production database, credential, or live runtime configuration was read; no operational command was executed by this reviewer. Only this report was written.

| Reviewed script | SHA-256 |
| --- | --- |
| `rollback-qwen.py` | `266478891d1de0ed2ebff04e9aa072b9f0641a073f8ed6b0b51cd07d30c87504` |
| `read-restored-qwen.py` | `a1fff81289f5bdab033b7943f03cfb8b1bd81ede96fe11c353050825dec91c4e` |

Both final scripts parse successfully. Inspected the full scripts, prior operations/data analysis and review, failure diagnosis, actual snapshot restore and writer-lock implementations, and their diff from old Qwen revision `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a`. The old restore implementation is unchanged; its config loader accepts the original disabled `qwen-intl` profile.

**Resolved finding:** the initial rollback renamed the publication root without excluding a separate publication writer. The final script acquires both existing landing and publication lifetime locks after stopping the unit, before the frozen count check or any rename. It checks owner, regular-file type, single link, mode, and inode identity, uses nonblocking exclusive locks without following links or creating replacements, and retains descriptors until process exit. Lock failure leaves the service stopped. Restore operates on newly created destination roots, so holding the preserved roots' locks does not obstruct it.

No unresolved data blocker remains:

- Original config and unit bytes and the exact snapshot manifest digest are pinned. The three roots must match the original configuration. Snapshot manifest `e68888961396b019cae2e1c715c50407262fd02b3d7fba02c62b2d3b6d91a43e` is passed to the matching old CLI, which verifies each entry, exact roots, private ownership, disabled provider, absent destinations, and the two-pass budget before restoration. Earlier backup review's size bounds still apply.
- After stop and lock acquisition, current state must equal schema 2 with 1 `artifact_ready`, 5 `needs_human`, and 1 `provider_unavailable`. Each entire state/publication/artifact root moves to its distinct `.rejected-26a0d3-20260919` sibling. The backups subtree remains in place. No database column, version, sealed record, or artifact path is rewritten; the failed attempt remains in the preserved v2 state.
- Full same-path restoration must return `restored_inactive`, `provider_replay=false`, and schema 1 with 1 `artifact_ready`, 4 `needs_human`, and 1 `provider_unavailable`. The old binary starts first through a unit bound to the original config with only `live_enabled=false`; readiness and unchanged counts precede its completion record.
- Live activation requires that offline record, exact disabled unit/config, original `qwen-intl` live configuration, and unchanged counts before and after another confirmed stop. The original unit then starts; baseline counts and the preserved failed v2 counts are checked again. No target binary opens the restored v1 root.
- The separate historical check performs only one authenticated GET and pins job `pr82-smoke-5f6f6ce1ecb0`, its `artifact_ready` state, artifact digest `85b3360aaa28c38448c8d31770a5307df809aa7ce4829e81f1ac7b4ddddc76ed`, and null live URL. Neither script submits a provider job or publication request. Re-enabling the original service restores its normal admission capability; zero calls refers to this rollback procedure.

Any failed count, lock, digest, restore, or readiness check must stop dependent steps. A partial restore/rename is preserved for investigation; do not rerun destructive steps or start either binary against an unverified root. Record the actual restore/offline/historical-read/final results before claiming recovery. This PASS approves the reviewed data procedure only; Qwen Omni acceptance remains failed, and the separately accepted Grok service remains outside the rollback scope.
