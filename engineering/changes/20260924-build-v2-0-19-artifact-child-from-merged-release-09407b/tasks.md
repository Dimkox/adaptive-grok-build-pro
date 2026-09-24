# Tasks — Build v2.0.19 artifact child from merged release-sync 3f41be92

- [x] Freeze the exact merged release-sync source parent, tree and expected ZIP/sidecar digests.
- [x] Build twice in private 0700 staging and compare bytes.
- [ ] Update candidate state, release docs and coupled manifest/project-state tests.
- [ ] Run `python3 scripts/grok_verify.py --mode pr` on the final artifact-child tree.
- [ ] Complete independent security and release reviews.
- [ ] Bind evidence to the final tree fingerprint and exact PR head.
- [ ] Deliver through PR, wait for App-owned Trust CI, then separately tag/release under exact grants.
