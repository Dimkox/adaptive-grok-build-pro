# Tasks

- [x] Preserve initial failing code/test reviews and continue their repairs under the existing route and implementation owner.
- [x] Capture red regressions for ordering mismatch, malformed sections, original item bounds, and HTTP/Codex/service outcomes before production edits.
- [x] Apply bounded decoder-only repair; preserve strict contracts, section order, text/field checks, and existing caller catches.
- [x] Pass the 18-test regression run, 66-test locked focused suite, and Ruff; update scope, evidence, rollback, and shared learning notes.
- [x] Parent: run initial full verification, diagnose its sole pre-existing PDF-fixture failure, and obtain independent code/test re-review after focused recovery verification.
- [ ] Parent: update existing PR #82 under exact delegated authority and wait for a fresh exact-head Trust CI result and required merge authority.
- [ ] Operator: after merge and exact deployment delegation, stage/install the merged SHA and verify runner identity and readiness.
- [ ] Operator: perform the authorized bounded synthetic normalization and inspect success/failure evidence; any real job resubmission remains a separately authorized action.

Verification recovery: complete; valid 100/101-page fixtures and the 74-test locked targeted run pass. Final local completion is conditional on `UV_LOCKED=1 python3 scripts/grok_verify.py --mode pr` passing for the committed, unchanged tree and all required runtime receipts matching that tree. Use `python3 scripts/grok_status.py` for current evidence gaps; tracked review reports describe the pre-commit source hashes and cannot replace this final gate.
