# Architecture analysis — safe M3 restack on accepted M2

**Route:** `41eadaeae674`
**Target M2 commit:** `022411b05924618cfde0cb97b8c8aff4955e6013`
**Current M3 head:** `d4cc01f`
**Merge base:** `635c9ddf2d63c1ea823074106976a8f3de6299a9`
**Scope:** analysis only; this report is workflow evidence and not merge authority.

## Ruling

Use a normal two-parent merge of the exact accepted M2 head into M3. Do **not** rebase, cherry-pick selected M2 commits, reconstruct the Trust-CI fix manually, or take a blanket `ours`/`theirs` conflict resolution. The accepted head is not an ancestor of M3 and M3 is not an ancestor of it, so a merge commit is the smallest auditable operation that retains the exact M2 lineage and the M3 governance lineage.

The merged tree must preserve both immutable contracts:

- M2: read-only/different-owner repository compatibility, exact command-scoped Git trust, no source `MANIFEST.sha256` mutation, no deployed Trust-CI mutation, finite `10820` architecture change ceiling, and the post-M2 zombie-only cleanup fix (including bounded, fail-closed procfs classification).
- M3: target-owned canonical governance registries, closed/frozen governance schemas and `GovernanceHandoffV1`, candidate-only lifecycle, externally evidenced activation, no Markdown authority, exact M2 architecture evidence binding, and governance-bound receipt invalidation.

No public HTTP/OpenAPI/event/database contract changes are required. This is a source-lineage integration repair; the only new externally relevant artifact is the final exact merge SHA, which requires fresh Trust CI and any required signed scopes.

## Conflict inventory and exact rulings

The only paths changed by both branches are:

```text
README.md
architecture/rules.yaml
decisions.md
mistakes.md
tests/test_architecture_fitness.py
tests/test_change_receipts.py
```

| Path | Safe ruling |
| --- | --- |
| `README.md` | Compose both factual additions: retain M2 read-only/package and zombie-cleanup claims and M3 governance/current-state/map/CLI claims. Recompute the final text from the merged tree; do not retain stale “pending” or exact-SHA claims from either historical branch. Preserve the complete K16 graph. |
| `architecture/rules.yaml` | Semantically union M3 governance path ownership and `FIT-GOVERNANCE-HANDOFF-COMPATIBILITY` with M2's accepted `FIT-BOUNDED-ARCHITECTURE-CHANGE.max_changed_lines = 10820`. Do not lower the limit back to 10000 and do not raise it further to make this merge pass. Retain M3's `governance`/`schemas` paths in separation, boundary, and budget lists. |
| `decisions.md`, `mistakes.md` | Append/merge the independently useful records from both histories in chronological order; never discard M2's read-only/run-cleanup lessons or M3's authority/provenance lessons. Keep projections non-authoritative and do not invent approval/operational facts. |
| `tests/test_architecture_fitness.py` | Keep M3 coverage that verifies the new governance-promotion category and semantic violations, but remove the root-cumulative assertion that `change_separation` passes and that no `trust-ci/**` path exists. The exact M2 ancestor deliberately contains Trust-CI changes, so that global assertion no longer tests a stable contract. Retain tests that evaluate a purpose-built isolated diff when asserting change separation. |
| `tests/test_change_receipts.py` | Keep M2's temporary process-scoped clone Git configuration and exact comparison-base/binding assertions. Keep M3 governance receipt, deletion, and architecture-digest rotation tests. Do not assert a cumulative root architecture result is `pass` or `fail`: its status is branch-history-dependent after the merge. Assert the invariant fields (named architecture result, configured state, exact base, route-base, fingerprint/evidence linkage) instead. |

The static merge preview also shows textual collisions in historical evidence-related prose. Preserve all existing evidence files unchanged wherever Git can auto-merge; do not rewrite old M2/M3 reports to claim the merge was previously tested. The restack's own verification/review evidence must be new and bind only to the merge head.

## Integration sequence

1. Confirm `022411b…` resolves locally and remains the externally accepted M2 head required by the task. Record its full SHA and parentage in the restack change package.
2. Make the normal merge into the designated M3 restack branch. Resolve only the six overlapping paths using the rulings above; application changes outside conflict resolution are out of scope.
3. Validate the merged architecture model/rules and governance registries before running broad tests. The governance handoff must rederive against the merged exact M2 architecture evidence; no cached M3 handoff/receipt may be reused.
4. Run targeted regressions for all preserved surfaces: M2 read-only checkout/package/receipt tests, M2 Trust-CI workspace cleanup tests, M3 governance/governance-fitness tests, architecture model/fitness tests, installer/structure regressions touched by the combined rules.
5. Run the route-selected verifier on the final fingerprint, then independent code, test, and security review. Any source change after that invalidates all local evidence.
6. Open/update PR #11 only through separately delegated action, then wait for the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact merge head and fresh scopes if the deployed policy requires them. Neither the merge commit nor local receipts inherit M2/M3 approval/check authority.

## Failure gates

Stop and return the merge to the single write owner if any of these occur:

- merged architecture fitness fails because M2 Trust-CI paths and M3 implementation/governance paths are now mixed; do not weaken `FIT-TRUST-CI-SEPARATION` or hide paths. The restack must use the already-reviewed exact-base binding/exception semantics, if present, or be escalated as an architecture decision;
- the merged measured change exceeds the retained M2 finite 10820-line budget; do not raise the ceiling as a conflict fix;
- governance schemas, registry digests, M2 architecture digest, or exact handoff SHA are stale/mismatched; regenerate evidence from the merged commit rather than editing frozen contracts;
- any M2 no-follow, source-invariance, process-group, or Git-trust regression fails;
- README/project documentation claims a check, approval, deployment, merge, or policy state not proven for the final merge head.

## Rollback and recovery

This is source-only integration with no database migration, deployment, external write, or runtime-state mutation. Before PR delivery, abandon the unmerged restack branch/merge commit and recreate it from the preserved M3 head; do not reset shared/protected branches. After PR delivery, rollback is a new PR reverting the merge or a narrowly reviewed forward fix, followed by fresh verification, reviews, exact-SHA Trust CI, and scopes. Do not roll back by changing deployed Trust CI policy, holdout, keys, approvals, branch protection, or historical M2/M3 evidence.

## Verification minimum

At minimum, the final plan must demonstrate:

- the merge base, M2 full SHA, M3 parent SHA, and final two-parent merge SHA;
- valid architecture and governance models plus a newly emitted governance handoff whose `architecture_digest`, exact base/head, governance digest, and evidence digest match the final tree;
- all M2 acceptance regressions, including `tests/test_architecture_fitness.py`, `tests/test_change_receipts.py`, `tests/test_manifest_package.py`, and `trust-ci/tests/test_workspace.py`;
- M3 `tests/test_governance.py`, `tests/test_governance_fitness.py`, `tests/test_architecture_model.py`, and receipt/verification tests;
- final route `base`, `frontend`, `contracts`, and `integration` quality profiles plus fresh independent code/test/security reports;
- an external exact-head App-owned check before merge eligibility.

This preserves the strict M2/M3 sequence: M3 consumes the accepted M2 architecture surface and does not convert a merge conflict into a weakening of Trust-CI isolation, finite fitness budgets, or governance authority.
