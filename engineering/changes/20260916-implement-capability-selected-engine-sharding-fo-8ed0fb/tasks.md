# Tasks — 20260916-implement-capability-selected-engine-sharding-fo-8ed0fb

- [x] Reproduce the original failure mode exactly: ported suite on a pytest-free host mirrors the Trust CI image (9 failures with the old contract).
- [x] Port runner + suite + pin file + verification wiring from preserved head 6d72d4c.
- [x] Implement `parallel_engine_ready`/`select_engine`; degrade before execution; engine recorded in versions; `core.workers` drives the backend label.
- [x] Rework the contract tests (degrade test, strict-pin test with both missing and wrong-version arms, engine-conditional distribution assertions, backend-agnostic coverage damage hook, explicit skipTest for the xdist-only worker-loss, repo-root default-parity test, config bounds/schema arms, /proc guard).
- [x] 20 runner tests OK with no pytest (one explicit xdist-only worker-loss skip); ruff clean.
- [x] Code review PASS + test review PASS (both rounds): trust CLI prints effective workers+engine; repo-root default-parity test; strict-pin version-mismatch arm; skipTest not continue; /proc guard; requested_workers kept in details; _stop wait hardened; opt-in gitignored; docs honest that xdist-only arms are mock-pinned here and executed by the App check.
- [ ] Final `grok_verify --mode pr` and receipts on the review-round head; PR; the external no-pytest check closes AC-004.
