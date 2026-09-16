# Tasks — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

- [x] Route the release task and open this change package (route `f98796afe7de`; routing-time base `280cbff`, delivered parent `7bbf425` after the rebase recorded below).
- [x] Freeze the content: `v2.0.16` publication is immutable; the post-publication landing set is twelve merges — #81, #82, #83, #85, #88, #89, #90, #91, #93, #13, #64 and #94, re-derived from `git log --first-parent 969c4f65..7bbf425` — each with its merge commit, checked head and App check run.
- [x] Write the typed spec, requirements, architecture, test plan, release and rollback plans.
- [x] Re-derive `observed_main_sha` after #64 merges and rebase `feature/v2.0.17-release-sync` onto it.
- [x] Identity bump: `VERSION`, `__version__`, README H1/identity line, CHANGELOG `2.0.17` section, ROADMAP identity lines, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`.
- [x] `PROJECT_STATE.json` transform: candidate product version, opened `current_unreleased_change` and pending `local_candidate`, appended post-publication landing record.
- [x] Lockstep test edits in `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py`; prove the trio is red before and green after in the frozen tree.
- [x] `grok_verify --mode pr` on the frozen release-sync tree returned `RESULT: PASS | profiles=base,contracts | changed=28`, and the verification receipt was recorded with the review receipts on fingerprint `39f9e77b…`.
- [x] Independent `security_review` (PASS, 0 Critical, 0 Important, 4 Minor — all fixed) and `release_review` (PASS, no Critical, 3 Important) receipts recorded for route `f98796afe7de`; dispositions in `evidence/review-response.md`.
- [x] Opened as PR #98 and merged on its exact-head App check `104605819798` as `78082a290f8b90cade88685351fbb2ba263689b9`.
- [x] `A` delivered: two byte-identical builds of `packages/adaptive-grok-build-pro-v2.0.17.zip` (770f1db5…, 10,940,676 B) plus its sidecar, merged as PR #99 (`c86b1a1989ace899a4450bde558fcd8adc00e4e2`, App check `104621989321`).
- [x] Published: tag `v2.0.17` (object `5c6687ed97e1c365597bf27047016eb07411f28b`) binds `c86b1a1…`, and the GitHub Release ships the ZIP plus sidecar, published `2026-09-16T01:17:14Z`, under a delegated release grant.
- [x] `SR` in this chain: route `7c56479f61d3`, package `20260916-docs-release-record-the-published-v2-0-17-identi-7c5647`, recording `merge_commit`, `checked_head`, `tree`, `pull_request`, `published=true`, `published_at`, the tag object and both artifact digests.
