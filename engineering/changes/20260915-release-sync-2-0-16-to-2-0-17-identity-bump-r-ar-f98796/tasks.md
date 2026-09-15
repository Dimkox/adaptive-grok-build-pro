# Tasks — Release sync 2.0.16 to 2.0.17: identity bump R, artifact child A, tag release and successor SR per pinned doctrine

- [x] Route the release task and open this change package (route `f98796afe7de`, base `280cbff`).
- [x] Freeze the content: `v2.0.16` publication is immutable; post-publication landing set is #82, #83, #85, #88, #89, #90, #91, #93, #13 and #64, each with its merge commit, checked head and App check run.
- [x] Write the typed spec, requirements, architecture, test plan, release and rollback plans.
- [x] Re-derive `observed_main_sha` after #64 merges and rebase `feature/v2.0.17-release-sync` onto it.
- [x] Identity bump: `VERSION`, `__version__`, README H1/identity line, CHANGELOG `2.0.17` section, ROADMAP identity lines, `START_HERE.md`, `GROK_BUILD_HANDOFF.md`.
- [x] `PROJECT_STATE.json` transform: candidate product version, opened `current_unreleased_change` and pending `local_candidate`, appended post-publication landing record.
- [x] Lockstep test edits in `tests/test_structure.py`, `tests/test_project_state.py`, `tests/test_manifest_package.py`; prove the trio is red before and green after in the frozen tree.
- [ ] Run `python3 scripts/grok_verify.py --mode pr` on the frozen tree and record the verification receipt.
- [ ] Independent `security_review` and `release_review` receipts for this route.
- [ ] Open the pull request, wait for the exact-head App check, merge `R`.
- [ ] `A`: build the ZIP+sidecar from the merged `R` tree in `0700` staging with two byte-identical builds, deliver them plus the `local_candidate` flip as the artifact-child pull request.
- [ ] Tag `v2.0.17` and publish the GitHub Release bound to `A`'s exact merged commit — requires its own explicit delegated grant (production action).
- [ ] `SR`: documentation successor recording `merge_commit`, `artifact_child.commit`/`tree`, `published=true`, `published_at` and the joined route/branch/package identities.
