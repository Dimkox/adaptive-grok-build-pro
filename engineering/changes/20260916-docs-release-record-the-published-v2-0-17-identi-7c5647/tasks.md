# Tasks — published v2.0.17 successor (SR)

- [x] Route `SR` on the merged artifact-child base (`7c56479f61d3`).
- [x] Re-derive the publication facts from the remote, not from prose: `git ls-remote` peeled tag `5c6687ed… → c86b1a1…`, `gh release view` published_at and both asset digests, App check run `104621989321` with attestation `b9510589-…`.
- [x] Move `published_release` to v2.0.17 and append the superseded v2.0.16 record to `prior_published_releases` unchanged.
- [x] Publish `local_candidate` with the child's merge identities, keeping `reviewed_product_*` null and `operational_activation` false.
- [x] Advance `current_unreleased_change`, `active_delivery` and `trust_ci.last_success`; keep the historical M-stack at v2.0.13.
- [x] Reconcile README, START_HERE, ROADMAP, CHANGELOG, HANDOFF and `packages/README.md`; close the release-sync package's A/SR checkboxes.
- [x] Move every coupled test literal in the same commit: lockstep modules **119 tests OK**.
- [x] Record the release-cycle process defects in `mistakes.md`.
- [ ] Independent `security_review` and `release_review` receipts plus `grok_verify --mode pr` on the frozen tree.
- [ ] Open the pull request and merge only on the exact-head App check.
