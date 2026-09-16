# Tasks — 20260916-docs-state-the-release-chain-landing-convention-627a16

- [x] Route (`627a16845fc4`) and open this package on base `83925c12`.
- [x] Re-derive the three causes from the retained Trust CI job records (failing command plus the assertion or error text).
- [x] During review the maintainer ordered PR #33 closed (2026-09-16T07:21:05Z), so it moved from `open_pull_requests` to `retained_unresolved` as `closed_unmerged` with its inspected cause and the condition for re-taking the work, `open_pull_requests` is now empty, and the pins were regenerated from the data instead of being hand-edited.
- [x] Added the landing-row convention sentence to `START_HERE.md`, in the machine-readable-handoff paragraph a routed agent reads first.
- [x] Replaced all three `failure_cause` placeholders and moved both exact-value pins; `grep -c 'not inspected or inferred' PROJECT_STATE.json` is now 0 and `tests.test_project_state`/`test_structure`/`test_manifest_package`/`test_change_spec` report 119 tests OK.
- [x] Independent reviews completed: `security_review` FAIL on the first head (two over-attributed causes) and `release_review` PASS; both were rewritten against the verbatim records and the roadmap/START_HERE contradictions they exposed are closed — see `evidence/review-response.md`. `grok_verify --mode pr` and the receipts bind the corrected head.
- [x] Delivered as PR #102; the corrected head carries the #33 close-out as well, so merge still requires its own exact-head App check.
