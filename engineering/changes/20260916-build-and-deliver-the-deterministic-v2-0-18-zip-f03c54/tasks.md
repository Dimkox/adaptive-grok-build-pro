# Tasks — 20260916-build-and-deliver-the-deterministic-v2-0-18-zip-f03c54

- [x] Route `A` inside its own worktree (`f03c541d184f`, base `fc8d9e6`).
- [x] Confirm nothing landed between `R` and `A` (open pull requests: none), so the tagged tree will be exactly `R` plus these bytes.
- [x] Build the ZIP twice in private `0700` staging from two independent clones at `fc8d9e6`; require byte identity (`0bc6adc9…`, 11 160 330 B).
- [x] Commit `packages/adaptive-grok-build-pro-v2.0.18.zip` and its sidecar; add the `packages/README.md` row.
- [x] Flip `local_candidate` and the currency fields with the anchor-checked map script; keep self-identities null and publication flags false.
- [x] Re-observe the installed L5 services and bind a new dossier (`runtime-observation-post-107.json`) to this base.
- [x] Move the coupled test literals in lockstep; `tests.test_structure`/`test_project_state`/`test_manifest_package` → 89 tests OK.
- [x] Security and release reviews PASS on `497de07` (all 14 findings dispositioned in `evidence/review-response.md`); `grok_verify --mode pr` PASS 16/16 on the review-round head `07d1141` (changed=28) with verification/security_review/release_review receipts bound to it.
- [x] Opened as PR #108 and merged as `e7d0f72bf834b75eb543d9424ee47c7829cc65c0` on App check `104809218211` SUCCESS; tag `v2.0.18` (object `31d3171f651ea77e29de58d4affc58d008f1c7a5`) and GitHub Release with both delta assets published `2026-09-16T13:52:24Z` under release-profile grant `fef0f24d625f4ea3` bound to the merged tree.
- [x] `SR` (route `8c6e9e30b239`, package `20260916-release-successor-record-for-the-published-v2-0-8c6e9e`) records the merged identities and flips the publication flags.
