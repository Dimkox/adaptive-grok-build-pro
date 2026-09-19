# Tasks — issue #146 contract-closure reverse edges

- [x] Reproduce the defect on pristine `d871ea6` and attribute it honestly (arms A/B/C in `closure-fix-blast-radius.md`; the hole predates #133, which only made it load-bearing).
- [x] Characterization first: plain-relative control asserted to keep surfacing its dependent, so the fix cannot be "verify less".
- [x] Implement: shared reference grammar (`schema_reference_parts`, `schema_reference_relative_path`, `schema_reference_target_path`) with explicit `precedence` and no default; comparator keeps `ID_FIRST`, closure uses `PATH_FIRST`; the legacy `_relative_path` was moved, not copied.
- [x] Add the seven regression arms to `tests/test_architecture_fitness.py::ArchitectureFitnessTests`.
- [x] Mutation matrix M0–M8, including M1 (revert) and M7 (closure inherits `id_first` → fails, the anti-inheritance lock).
- [x] Independent controller verification of the patch in private clones (differential, closure sweep, end-to-end arms) → `controller-verification.md`.
- [x] Correct the controller's own blast-radius note after measurement (one new failure → three, all on `M7-READY-BUNDLE-V1`).
- [x] Run selected quality profiles: `base` + `contracts` focused modules, full root discovery, `git diff --check`, `ruff`.
- [ ] Complete independent reviews (route-selected: code, test, security).
- [ ] Bind the `verification` and review receipts to the final tree fingerprint.
- [ ] Push branch, open pull request, wait for the App-owned exact-SHA check; merge is a separately delegated action.
