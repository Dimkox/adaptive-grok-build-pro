# Tasks — 20260916-docs-state-the-release-chain-landing-convention-627a16

- [x] Route (`627a16845fc4`) and open this package on base `83925c12`.
- [x] Re-derive the three causes from the retained Trust CI job records (failing command plus the assertion or error text).
- [x] Added the landing-row convention sentence to `START_HERE.md`, in the machine-readable-handoff paragraph a routed agent reads first.
- [x] Replaced all three `failure_cause` placeholders and moved both exact-value pins; `grep -c 'not inspected or inferred' PROJECT_STATE.json` is now 0 and `tests.test_project_state`/`test_structure`/`test_manifest_package`/`test_change_spec` report 119 tests OK.
- [ ] Independent `security_review` and `release_review` receipts plus `grok_verify --mode pr` on the frozen tree.
- [ ] Deliver as a pull request and merge only on the exact-head App check.
