# Tasks — Add Factory v1.5 decision accounting boundary behavior from source commit 531089f to the PR2 persistence foundation: enforce bounded cost and duration values and exact persisted accounting invariants as a new feature slice, with regression tests and isolated PR delivery

- [x] Freeze contracts and expected behavior: existing signed-bigint integer bound and summary shape; no schema/API/migration change.
- [x] Add failing test: cumulative max+1 rejected in five complete/incomplete scenarios through both discovery paths; observed 10 expected subtest failures before repair.
- [x] Implement the smallest vertical change: validate `known` immediately after each known-charge addition; adapt source regression cases into the shared dependency-free suite.
- [x] Run focused writer checks: both discovery modules pass 26 tests; changed-file ruff and diff whitespace pass. See `evidence/implementation-report.md`.
- [ ] Run final full PR quality profile, including real PostgreSQL exit coverage (coordinator).
- [ ] Complete independent reviews.
- [ ] Bind evidence to the final tree fingerprint.
