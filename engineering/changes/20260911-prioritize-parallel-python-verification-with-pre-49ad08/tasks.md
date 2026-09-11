# Tasks

- [x] Confirm priority, exactmain and isolated branch.
- [x] Obtain independent runner/coverage/dependency analyses and explicit capacity fallback.
- [x] Add failing behavior tests; implement bounded Core sharding and fresh coverage.
- [x] Complete Trust CI loadfile entrypoint, sequential combined target and separately delivered runner-image source pins.
- [ ] Verify normal entrypoint, packaging and complete existing required checks.
- [ ] Independent code/test review and current local receipts.
- [ ] Push priority branch, open PR, obtain exact external check/scopes, merge only when eligible.

## Delivery split after architecture verification

`FIT-TRUST-CI-SEPARATION` rejects a PR combining local implementation with `trust-ci/**` source mutations. Move the three runner package pins and the existing test_ops pin assertion into a separate bootstrap branch/PR; this acceleration branch has no Trust CI source changes. Its Make target still invokes the existing Trust test suite with loadfile. Companion image deployment remains independently operated, and actual signed scopes come from the external exact-head check.
