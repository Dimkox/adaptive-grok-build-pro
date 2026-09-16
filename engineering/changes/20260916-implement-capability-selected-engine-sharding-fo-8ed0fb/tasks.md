# Tasks — 20260916-implement-capability-selected-engine-sharding-fo-8ed0fb

- [x] Reproduce the original failure mode exactly: ported suite on a pytest-free host mirrors the Trust CI image (9 failures with the old contract).
- [x] Port runner + suite + pin file + verification wiring from preserved head 6d72d4c.
- [x] Implement `parallel_engine_ready`/`select_engine`; degrade before execution; engine recorded in versions; `core.workers` drives the backend label.
- [x] Rework the contract tests (degrade test, strict-pin test, engine-conditional distribution assertions, backend-agnostic coverage damage hook, explicit skip for xdist-only worker-loss).
- [x] 19 runner tests OK with no pytest; ruff clean on touched files.
- [ ] `grok_verify --mode pr`, reviews, receipts, PR; the external no-pytest check closes AC-004.
