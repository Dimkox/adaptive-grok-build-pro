# Tasks — 20260916-release-successor-record-for-the-published-v2-0-8c6e9e

- [x] Re-derive the publication facts live (tag object, merge, tree, checked head, check-run, attestation, GitGuardian, published_at).
- [x] Move published_release to v2.0.18; archive v2.0.17 unchanged into prior_published_releases.
- [x] Flip local_candidate/current_unreleased_change/active_delivery/trust_ci.last_success and the post-v2.0.17 landing status.
- [x] Bind a fresh runtime observation (`post-108`, live systemctl re-confirmed: MainPIDs 698333/3597736 unchanged, active/enabled) to the new base.
- [x] Move every coupled test literal in lockstep; 119 tests OK.
- [ ] Final `grok_verify --mode pr` PASS and receipts on the review-round head, then PR and exact-head App check. (First gate PASSed on `28de12c`; security PASS + release FAIL findings are all closed in the review-round commit with both reports and dispositions in `evidence/`.)
