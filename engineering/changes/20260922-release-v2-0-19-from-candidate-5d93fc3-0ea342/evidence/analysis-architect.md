# Architecture analysis — v2.0.19 R/A release

Verdict: **NO-GO in the current worktree; the bounded design is viable after the blockers below are corrected.** Reviewed read-only at HEAD `5d93fc3d68869ab26799935adab5fa62be5e2a80` on `release/v2.0.19-candidate-20260922`; product changes are uncommitted. No long tests were run.

## Findings

1. **Blocker — no exact release-sync identity exists yet.** `README.md` and `START_HERE.md` describe `5d93fc3…` as the v2.0.19 candidate tree, but that SHA/tree is the clean parent before the current dirty identity/state/test changes. `grok_status.py` reports zero commits after the initial checkpoint and eleven dirty product paths. Commit R first, then bind the R head and tree consistently in docs/state/evidence; all verification, reviews and the App-owned check must cover that exact R head.

2. **Blocker — the typed package is invalid and has no release evidence.** `grok_status.py` reports `change-spec.yaml` as `spec_invalid`; verification and code/test/security/release receipts are all `not_run`. The release chain must not progress until the schema error is exposed/fixed and current-fingerprint obligations are complete. A later A commit invalidates R-bound completion evidence and needs the applicable final-tree verification/reviews plus its own exact-head external check.

3. **High — artifact binding language conflates two identities.** The sound design is: ZIP bytes are deterministically built from sealed merged R; A adds only ZIP+sidecar; tag/release target merged A. `INV-002` instead says the artifact is “content-addressed to the exact merged artifact-child commit,” which is self-referential if the archive must embed A. Rewrite it to bind archive manifest/provenance to R head/tree and bind repository custody/tag/publication to A head/tree/merge commit. Record both identities and both digests explicitly.

4. **Medium — state/handoff status is premature and internally mixed.** `current_unreleased_change.status=release_sync_authored` and `local_candidate.status=pending_release` are truthful, but `active_delivery.status=source_delivered_operational_qualification_incomplete` implies delivery before R has a PR/check/merge. `START_HERE.md` also labels the older factory/tooling work as “Active delivery” while saying top-level `active_delivery` describes v2.0.19. Use a pending release-sync status and clearly mark the factory entry historical/separate.

5. **Medium — acceptance needs explicit stage records.** The documents describe R→A correctly, preserve v2.0.18, keep package fields null/absent, and prohibit deployment. Add stage-specific acceptance evidence: R checked head/tree, R merge commit/tree, A source-parent equality to merged R, A delta exactly the two package paths, two-build byte equality, sidecar-to-ZIP equality, A checked head/tree, A merge commit/tree, tag target equality, and release-asset digest equality. Any changed base/head/policy/holdout must fail closed and restart the affected gate.

## Rollback assessment

Pre-publication rollback is adequate: abandon R or A and retain immutable v2.0.18. Post-publication, tags/assets must never be overwritten; consumers may pin v2.0.18 and metadata defects require a new exact-SHA forward-fix. Clarify that a bad v2.0.19 publication is not “rolled back” by moving the tag: preserve it, document the defect, and issue a successor release. No service/database rollback applies because deployment is out of scope.

## Required go conditions

- Valid typed change spec and a clean committed R identity replacing every provisional `5d93fc3…` candidate claim.
- Current local verification and independent receipts bound to the applicable frozen tree.
- Successful App-owned `adaptive-trust-ci/verified@06ecf1c875bc` on exact R and A PR heads, with required external signed scopes and exact local grants.
- A built only from merged R, deterministic ZIP/sidecar evidence, A limited to the package pair plus necessary truthful state evidence, and tag/GitHub Release targeting the exact merged A commit.
- `PROJECT_STATE.json`, README and START_HERE agree on pending/merged/published state at each transition; operational activation remains false.
