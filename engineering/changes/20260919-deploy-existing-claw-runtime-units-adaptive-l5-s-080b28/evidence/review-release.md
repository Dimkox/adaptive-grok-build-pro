# Independent release review

Result: **PASS — pre-cutover readiness**, 2026-09-19. Route `080b283b0cf3`; reviewer `release_reviewer`. No unresolved release blocker in the reviewed staged operation. This decision is local workflow evidence, not deployment completion, merge authority, a human security signature, or permission beyond the recorded user delegation.

Reviewed control HEAD: `26a0d3db8fa9f3e8ad69caafd02a5ef4e9613960`. HEAD and PR150 head `c335a33b9cffde4d8912b173803c3adec3348d06` independently resolve to tree `30ff3707c5eb11b88f485f37795b967737a096d9`. The App-owned check identity and success are recorded in operations-plan.md; this review did not independently query the Checks API. Remote refs were fetched. Product files have no working-tree diff.

## Reviewed SHA-256 bindings

| File | SHA-256 |
| --- | --- |
| `evidence/upgrade-operations.py` | `c76de57452fb27999dd7fdac82bfd8beb37210367560b8a7129cc6897d5ebb0e` |
| `evidence/accept-runtime.py` | `8b54e6e23187d91a09f29270d828ef00478a1a146632e5a265ad5f938fcbcb28` |
| `evidence/operations-plan.md` | `7248902063f94d775c74cef7bd6eabed3e90a5d84b74833641e6b66393aeb06e` |
| `rollback.md` | `4cbd803d99bf5a4d7ce197e9de362738bccee32720f474a737da0c0fd0dcb377` |

## Findings and decision basis

- **Provenance and installation:** the exact installer requires independent clean Git checkouts and immutable release creation. Its installer and service template are unchanged from both existing runtime revisions. Installed-package-verification.json records zero dependency drift and zero source mismatches across 62 factory and 10 delivery Python files. Preflight records successful pip check and the target interpreter's focused run; focused-verification.log contains 19 passing migration/restart/backup tests. These are supplied execution records, not commands rerun by this reviewer. Both final operational scripts independently parse successfully without execution.
- **Exact units and staged startup:** only the two named units are eligible. Staging preserves each original unit/config, rejects drop-ins, retains its actor/environment/socket/storage boundaries and changes the release/config references. Each inactive original unit must still equal the saved bytes before replacement. Grok is completed before primary Qwen. The separate Omni unit, source checkout, Trust CI, publication and releases remain outside scope.
- **State compatibility:** backups precede even disabled target startup, which opens and migrates SQLite. The final script rechecks pending-state counts after the service is inactive and outside the auto-resume exception handler; ambiguous work stays stopped. It requires completed backup output, the separately retained manifest digest and a conservative two-pass restore-size budget. Target schema v2 is additive; old binaries cannot read it. Comparing both old backup implementations confirms that the target changes only acceptance of the v1 database identity, preserving snapshot/restore format.
- **Meaningful acceptance:** offline readiness checks the exact dedicated-host response and authenticated disabled capability behavior. Live acceptance verifies the sealed capability, attempt protocol, complete expected profile/digest and pinned landing source; the POST is actor/profile-bound. One fixed job and zero transport retries prevent a fresh job from replacing an ambiguous attempt. The final client validates the sealed durable receipt, actor/repository/source, normalized dispatched observation and reported usage; its v1 result must match the same job/state/artifact digest and have null live URL. A separate observe invocation submits nothing. The documented launcher supplies the existing opaque credential as the service owner with an outer 200-second deadline. This qualifies the bounded text path only.
- **Recovery:** containment uses the compatible target with live execution disabled. Full binary rollback preserves upgraded roots, restores the complete snapshot into absent original paths, and explicitly binds the old binary to a disabled recovery config for validation. Only successful validation permits restoring original unit bytes and their original live config. This resolves the original wording's risk of starting the old service live during recovery validation. No data downgrade or provider replay is proposed.

## Execution gates and limits

The operator must still materialize and validate exact delegated grants after freezing all evidence; execute each stopped backup; require offline API success, schema v2 and unchanged stopped-baseline counts; capture live acceptance plus separate observation for each service; and verify final executable/config identity, active/enabled state and unchanged Omni identity. A failed gate stops that service's rollout and invokes the documented containment/recovery path. No runtime, provider, credential, or production database command was executed by this reviewer. Production restore feasibility has bounded source/test evidence, not a newly exercised live recovery drill.

Before the durable evidence PR is finalized, populate the remaining scaffold criteria/metrics or link the concrete operational criteria consistently; operations-plan.md currently contains the substantive acceptance and stop conditions. No release/tag, public publication, failover-chain, multimodal, external-pilot, M8 or general M9 qualification is implied.
