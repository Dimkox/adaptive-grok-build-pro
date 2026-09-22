# Integration architecture assessment

Decision: **NO-GO in the current worktree; conditionally sound after the gates below.** Reviewed read-only at branch `release/v2.0.19-candidate-20260922`, HEAD `5d93fc3d68869ab26799935adab5fa62be5e2a80`, tree `794e7623b8c1551528147b949342ca477c2f1b46`, after fetching `origin/main` at `130ce4a42d9f9bbd1b56772d40b19ae530283205`.

## Findings

1. **Branch/base and candidate source are coherent.** `HEAD` is seven commits ahead and zero behind `origin/main`; the merge base and routed base are both `130ce4a…`. The release-sync edits are layered on exact candidate `5d93fc3…`, not on a stale main. However, the release-sync itself is still an uncommitted 11-product-path change plus two untracked change packages, with zero commits after the route checkpoint. There is no matching remote branch or pull request, hence no exact-head external check.

2. **The local package is not gateable yet.** `python3 scripts/grok_status.py` reports the change package incomplete because `change-spec.yaml` cannot be validated; verification and all four review receipts are `not_run`. This blocks checkpoint, review, push/PR, and any claim that the release-sync source is ready. The current human-gate records explicitly identify themselves as workflow evidence, not delegated grants or Trust CI authority.

3. **Artifact-child handoff is correctly separated but remains entirely pending.** `PROJECT_STATE.json` keeps both v2.0.19 package paths absent and leaves `source_parent`, source tree, artifact commit/tree, and digests null. After release-sync merge, resolve the actual protected-main merge commit and tree, require that tree to equal the accepted release-sync PR tree, then build twice from that clean tracked merged commit. `package_stack.py` packages tracked `HEAD` blobs and checks source identity, which is the right mechanism; do not build from this dirty worktree or from pre-merge `5d93fc3…`. The artifact-child must add the ZIP and sidecar as its own delta and record the merged release-sync commit/tree as source provenance.

4. **Trust CI authority is per exact PR head and does not cross transitions.** Require App-owned `adaptive-trust-ci/verified@06ecf1c875bc` (GitHub App ID `4694114`) on the final release-sync PR head, merge only while up to date, then independently require that check on the final artifact-child PR head. A release-sync check does not authorize the merged commit, artifact build, artifact-child head, tag, or publication. Any commit/base/policy/holdout change invalidates the applicable result. Local verification, reviews, route files, and local grants never substitute for this boundary.

5. **Publication sequencing needs fail-closed identity checks.** Before each operation, prove tag `v2.0.19` and its GitHub Release are absent; bind fresh local grants to the exact repository, route, HEAD/tree, action and resource. After the artifact-child merge, verify its merged tree equals the checked artifact-child PR tree, create the tag at that exact merge commit, verify the remote tag target, then create the GitHub Release with exactly the tracked ZIP and sidecar and verify downloaded asset hashes. Do not generate notes implicitly, retag, overwrite assets, or mark publication complete before both assets and identities verify.

6. **Rollback is preservation/forward-fix, not mutation.** Before tag publication, stop and retain immutable v2.0.18. After any partial or complete publication, never move/delete/reuse the tag or overwrite release assets; disclose the partial state, keep consumers on or direct them back to v2.0.18, and repair metadata through a new exact-SHA reviewed successor. No deployment or runtime rollback is involved.

## Required order

Validate the typed spec → checkpoint the complete release-sync tree → focused/full verification and independent reviews on that fingerprint → push/open PR → exact-head App check and signed scopes → merge R and verify tree equivalence → clean two-build artifact reproduction from merged R → checkpoint artifact child and refresh all evidence → separate PR and exact-head App check → merge A and verify tree equivalence → exact grants → tag exact A merge → verify remote tag → publish both assets → verify downloaded digests and only then record publication.

Residual risk is concentrated in identity drift between PR head, merge commit, artifact source, tag target, and uploaded bytes. The proposed two-stage design controls it only if every arrow above is re-resolved and checked rather than inferred from prior evidence.
