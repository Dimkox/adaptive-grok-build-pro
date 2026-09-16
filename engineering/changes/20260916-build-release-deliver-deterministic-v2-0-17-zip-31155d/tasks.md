# Tasks — 20260916-build-release-deliver-deterministic-v2-0-17-zip-31155d

- [x] Route `A` inside its own worktree (`31155d4d2a6a`, base `78082a2`).
- [x] Confirm nothing landed between `R` and `A` (`gh pr list --state open` → `#33` only), so the tagged tree will be exactly `R` plus these bytes.
- [x] Build the ZIP twice in private `0700` staging from two independent clones at `78082a2`; require byte identity (`770f1db5…`, 10 940 676 B).
- [x] Commit `packages/adaptive-grok-build-pro-v2.0.17.zip` and its sidecar; add the `packages/README.md` row.
- [x] Flip `local_candidate` and the currency fields with the anchor-checked map script; keep self-identities null and publication flags false.
- [x] Re-observe the installed L5 services and bind a new dossier (`runtime-observation-post-98.json`) to this base.
- [x] Move the coupled test literals in lockstep; `tests.test_structure`/`test_project_state`/`test_manifest_package` → 89 tests OK.
- [x] Independent `security_review` and `release_review` receipts were recorded on the delivered fingerprint; both reviews reproduced the archive independently, and `grok_verify --mode pr` returned only the disclosed issue #80 blob-analysis red.
- [x] Opened as PR #99 and merged on the exact-head App check `104621989321`; tag `v2.0.17` and the GitHub Release followed under their own delegated grant.
- [x] `SR` (route `7c56479f61d3`, package `20260916-docs-release-record-the-published-v2-0-17-identi-7c5647`) records the merge commit, tree, checked head, pull request, `published=true` and `published_at`.
