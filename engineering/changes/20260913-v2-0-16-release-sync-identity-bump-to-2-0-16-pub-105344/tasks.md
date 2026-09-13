# Tasks
- [x] identity files + PROJECT_STATE transform + lockstep test edits
- [x] lockstep trio green; parallel harness PASS; serial verify receipt recorded
- [x] security/release review receipts
- [ ] merge after exact-head gate (R)
- [ ] artifact-child PR (A) + tag + GitHub Release (separate exact delegations)

## Artifact-child (A) checklist — from release review (full text: /tmp/review-sync-release.md §4)
- [ ] packages/adaptive-grok-build-pro-v2.0.16.zip + .zip.sha256 (0700 staging, built from merged R tree, byte-reproduced twice)
- [ ] PROJECT_STATE.local_candidate flip: status/artifact_status/published/notes + artifact_child source_parent/tree/commit/zip/sidecar identities; requirement string updated
- [ ] test flips: test_project_state L372/377/378/381-382 + test_manifest_package L1426 (pending literals); published-conditional L1434-1438 needs no edit; add exists()-guard mirror in test_project_state (test-review note)
- [ ] packages/README.md: v2.0.16 row
- [ ] keep external_effect/operational_activation false; do NOT demote v2.0.15 into prior list
- [ ] A cannot self-record its merge_commit/tree: tag v2.0.16 + GitHub Release bind to A's merged commit; post-A doc successor carries the final wording (v2.0.15 precedent)

## Recorded follow-ups (not blocking R)
- test_project_state L624 doc-currency anchor no longer proves README/START_HERE freshness (code-review medium 1)
- CURRENT_MAIN_SHA naming misnomer after the split (code-review low 1); F2: notes must say "bytes in tree", not "release published"
- l5 ledger: fix union completed_at 17:33:28→17:33:02 in landing block; archive 0e93bc draft package before any l5-split-g worktree cleanup (ref-safety audit)
