# Tasks — Release v2.0.19 with fail-closed factory issue fixes

- [x] Freeze contracts and expected behavior for #35/#39/#48/#73/#167 and #36 disposition.
- [x] Obtain independent issue-slice analysis and preserve separate worktree evidence.
- [x] Integrate the accepted issue slices in one release worktree, resolving shared verifier files.
- [x] Run issue-focused RED/GREEN/regression suites.
- [ ] Run full `python3 scripts/grok_verify.py --mode pr` on the fix tree.
- [x] Update VERSION/README/CHANGELOG/state/package release metadata in a separate commit.
- [ ] Complete independent code/test reviews on the final candidate.
- [ ] Bind verification/review evidence to the final tree fingerprint.
- [ ] Open protected PR with `Fixes #35, #39, #48, #73, #167`; retain #36/#186 disposition.
