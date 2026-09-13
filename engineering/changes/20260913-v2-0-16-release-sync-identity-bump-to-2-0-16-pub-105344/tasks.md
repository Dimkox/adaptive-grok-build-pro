# Tasks
- [x] identity files + PROJECT_STATE transform + lockstep test edits
- [x] lockstep trio green; parallel harness PASS; serial verify receipt recorded
- [x] security/release review receipts
- [ ] merge after exact-head gate (R)
- [ ] artifact-child PR (A) + tag + GitHub Release (separate exact delegations)

## Artifact-child (A) checklist — from release review (full text: /tmp/review-sync-release.md §4)
- [x] zip 71f63a10 + sidecar 14e3753a, 0700 staging, two byte-identical builds from merged R 287b27a
- [x] status=artifact_bytes_delivered, artifact_status=pending_tag_and_release; source_parent/tree = R merge identities; zip/sidecar shas recorded; commit/tree intentionally null (no self-record); published stays false until tag exists
- [x] literals flipped; manifest conditional re-gated on artifact_status with full sidecar-vs-digest integrity verification; null-pin loop split (self-identities stay null)
- [x] row added
- [x] both false; v2.0.15 remains published_release
- [ ] A cannot self-record its merge_commit/tree: tag v2.0.16 + GitHub Release bind to A's merged commit; post-A doc successor carries the final wording (v2.0.15 precedent)

## Recorded follow-ups (not blocking R)
- test_project_state L624 doc-currency anchor no longer proves README/START_HERE freshness (code-review medium 1)
- CURRENT_MAIN_SHA naming misnomer after the split (code-review low 1); F2: notes must say "bytes in tree", not "release published"
- l5 ledger: fix union completed_at 17:33:28→17:33:02 in landing block; archive 0e93bc draft package before any l5-split-g worktree cleanup (ref-safety audit)

## Release-addendum FAIL items (fixed in the amended A commit)
- [x] stray root file `reviewing` removed (shell-redirect artifact of `echo ->reviewing`)
- [x] README/START_HERE/CHANGELOG "ZIP+sidecar exists not" prose reconciled with delivered bytes
- [x] zip_source_note records that A's record/doc paths are outside archive bytes (pre-publication snapshot caveat)
- [ ] post-tag documentation successor must record: merge_commit, artifact_child.commit/tree, published=true, published_at, route_id/branch/change_package join, source_gate_status/review_status
