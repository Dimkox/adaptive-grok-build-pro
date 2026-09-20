# Tasks — issue #147

- [x] Reproduce the false `compatible` on the exact base (`90078959ff816068af374ad42f4bb80fdbaec866`) before touching code.
- [x] Implement path-first resolution for bases that fold onto a declared path; keep `$id` lookup for everything else
      (`architecture.py:1182-1197`, `:1361-1369`, used at `:1476`), and keep ambiguity refusal loud.
- [x] Add model-level rejection of a cross-contract path-`$id` collision at the single place documents and declared
      paths coexist (`contract_inventory()`, `architecture.py:655-689`, `:716`), with self-`$id` accepted.
- [x] Five arms in `tests/test_architecture_model.py`; mutation set m1–m7 proving each is load-bearing, plus the
      non-vacuity control on the shipped differential.
- [x] Correct #146's claimant-attribution assertion (it asserted the defect); scope/status halves untouched.
- [x] Focused checks green (238 tests, ruff, `git diff --check`, `tests.test_structure`), evidence embedded:
      `implementation-arms.md`, `measurement-harness.md`.
- [ ] Independent reviews (route-selected: code, test) and the three receipts on the final fingerprint.
- [ ] Push, open the pull request, wait for the App-owned exact-SHA check.
