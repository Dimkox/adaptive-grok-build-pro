# Independent release review: bounded Qwen rollback

**PASS — rollback preparation. No concrete release blocker found.** Route `080b283b0cf3`, reviewer `release_reviewer`, 2026-09-19, repository HEAD `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`.

| Reviewed script | SHA-256 |
| --- | --- |
| `rollback-qwen.py` | `266478891d1de0ed2ebff04e9aa072b9f0641a073f8ed6b0b51cd07d30c87504` |
| `read-restored-qwen.py` | `a1fff81289f5bdab033b7943f03cfb8b1bd81ede96fe11c353050825dec91c4e` |

The scripts follow the approved recovery design. The coordinator reports Grok accepted on the target, while Qwen produced a retained `needs_human`/`draft` outcome after one dispatched call with reported usage 761/195 and is contained on the target with live execution disabled. The source-grounded diagnosis establishes the failed draft-validation stage; its precise cause remains unavailable. This review does not reinterpret that failure as Omni acceptance.

- Only primary `adaptive-l5.service` and its explicit Qwen configuration/data roots are addressed. Grok and the separate Omni service are untouched. Original configuration, saved unit and snapshot manifest have exact hash guards; the original `qwen-intl` profile is checked before live restoration.
- Restore requires expected target unit, disabled new config, absent preservation destinations and exact expected v2 counts before and after stopping. It takes nonblocking exclusive locks on both existing landing/publication lock inodes, verifies their private owner/mode/regular-file identity, and retains them through root preservation and process exit. It never creates or replaces those locks. Unexpected state or an active writer leaves the service stopped before mutation.
- Complete state/publication/artifact roots move to fixed `.rejected-26a0d3-20260919` paths, retaining the failed attempt. The matching old restore CLI uses the pinned manifest and a service-owned private disabled config to restore into the now-absent original paths. The reviewed restore source verifies inventory, content digests, original paths and budget; it does not invoke a provider. The script requires successful inactive restoration and the exact original schema-1/count baseline.
- Offline startup uses the old executable with the disabled recovery config, outside its old control repository and compatible with its old closed config schema. Exact local readiness and unchanged counts precede the offline marker. The separate activate phase checks that marker, disabled unit/config and baseline again, including after stop; only then does it install the original live unit. No old executable opens the preserved v2 store.
- Final checks require old-host readiness, original counts and preserved failed v2 counts. The authenticated reader sends only a GET for historical job `pr82-smoke-5f6f6ce1ecb0`, requiring matching job/state, exact artifact digest `85b3360aaa28c38448c8d31770a5307df809aa7ce4829e81f1ac7b4ddddc76ed`, and null live URL. Retries, redirects and environment proxies are disabled. This proves historical artifact recovery, not a new inference or successful new profile.

Both final scripts parsed successfully without importing or executing them. Reviewed the previous rollback plan, diagnosis, old host-config loader and restore implementation. No runtime, database, credential, service or provider commands were executed; only this report was written.

Exact delegated grants remain an execution prerequisite after reviews are frozen. Capture both phase results, historical authenticated GET, final executable/profile/active/enabled identity and preservation paths. A partial restore or failed readiness/count check stops progression: preserve the partial/current roots, do not rerun the non-idempotent restore, and do not re-enable the failed new profile to collect evidence. The reader must use the established opaque systemd credential boundary. The script's zero-provider-call field describes its own operation scope rather than measuring unrelated concurrent traffic.

This local review supports recovery within existing delegation; it is not proof of completed rollback or fulfillment of the original Qwen Omni upgrade objective. Grok's independently successful upgrade may remain in place.
