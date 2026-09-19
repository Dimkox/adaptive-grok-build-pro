# Claw runtime upgrade observed on 2026-09-19

The requested two-service upgrade is **partial**. Grok accepted the merged target `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. Primary Qwen rejected the only new-profile response and was restored from its pre-upgrade snapshot to `5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a` / `qwen-intl`. Both services are active and enabled. The separate `adaptive-l5-omni.service` remains unchanged at `e7d0f72bf834b75eb543d9424ee47c7829cc65c0` / `qwen-omni-intl`.

| Operation | Observed result |
| --- | --- |
| Installed source | Exact merged target; 62 factory/10 delivery Python files identical; dependency inventory preserved; pip check passed. |
| Focused installed tests | 19 passed once, 1.258 s; backup, migration and recovery. |
| Offline migration | Both SQLite stores 1→2; original job counts unchanged; authenticated disabled capability 409. |
| Grok acceptance | One POST, artifact_ready, 26.947 s, reported usage 1341/1642; same-job observation retained the same digest. |
| Qwen Omni acceptance | One POST, needs_human / draft, 3.225 s, reported usage 761/195; no artifact. |
| Qwen rollback | Complete snapshot restored with old binary disabled first; original live unit restored; historical artifact digest unchanged; zero recovery provider calls. |

Safe machine evidence and reviewed scripts are in the [change package](../changes/20260919-deploy-existing-claw-runtime-units-adaptive-l5-s-080b28/brief.md), especially [final-runtime.json](../changes/20260919-deploy-existing-claw-runtime-units-adaptive-l5-s-080b28/evidence/final-runtime.json), [acceptance-results.json](../changes/20260919-deploy-existing-claw-runtime-units-adaptive-l5-s-080b28/evidence/acceptance-results.json), and [backup-and-migration-results.json](../changes/20260919-deploy-existing-claw-runtime-units-adaptive-l5-s-080b28/evidence/backup-and-migration-results.json).

The Qwen executor passed transport, stream/model/stop and usage checks. Failure occurred in draft decoding before rendering. This source discards the exact decoder exception and replaces its response digest with a synthetic failure digest; the rejected field and original reply are unrecoverable from retained evidence. See the [source-grounded diagnosis](../changes/20260919-deploy-existing-claw-runtime-units-adaptive-l5-s-080b28/evidence/diagnosis-integration.md). Do not retry merely to obtain a green result or claim that a new response reproduces the discarded one.

The failed v2 roots remain privately retained at `/var/lib/adaptive-l5/{state,publication,artifacts}.rejected-26a0d3-20260919`. Pre-upgrade snapshots remain under each service's backups directory; the manifest digests and before/after counts are in the evidence. Original configs/unit bytes remain in root-private `/var/tmp/adaptive-l5-preserved-20260919-26a0d3`. No secrets or database dumps are committed.

Initial operational errors are retained: Grok's first backup met a root-owned backups parent and resumed its old service; an exact parent permission correction preceded the successful backup. One offline client ran before asynchronous startup finished and returned ConnectError with zero POSTs; the later readiness-bound check passed. These are distinct from Qwen's genuine rejected provider response.

No release/tag, public publication, external accepted pilot, M8 activation, M9 qualification or full failover-chain acceptance is established by this operation. The previous dated runtime observations remain historical; this record supersedes their current-installation inference.
