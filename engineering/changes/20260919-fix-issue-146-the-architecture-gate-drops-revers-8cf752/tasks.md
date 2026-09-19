# Tasks — issue #146 contract-closure reverse edges

- [x] Reproduce the defect on pristine `d871ea6` and attribute it honestly (arms A/B/C in `closure-fix-blast-radius.md`; the hole predates #133, which only made it load-bearing).
- [x] Characterization first: plain-relative control asserted to keep surfacing its dependent, so the fix cannot be "verify less".
- [x] Implement: shared reference grammar (`schema_reference_parts`, `schema_reference_relative_path`, `schema_reference_target_path`) with explicit `precedence` and no default; comparator keeps `ID_FIRST`; the closure attaches the union of both precedences (`PATH_FIRST` and `ID_FIRST`), never one in place of the other; the legacy `_relative_path` was moved, not copied.
- [x] Add the regression arms to `tests/test_architecture_fitness.py::ArchitectureFitnessTests` (six new at first delivery, ten from this contour, 16 more than `d871ea6` overall).
- [x] Mutation matrix M0–M8, including M1 (revert) and M7 (closure inherits `id_first` → fails, the anti-inheritance lock).
- [x] Independent controller verification of the patch in private clones (differential, closure sweep, end-to-end arms) → `controller-verification.md`.
- [x] Correct the controller's own blast-radius note after measurement (one new failure → three, all on `M7-READY-BUNDLE-V1`).
- [x] Run selected quality profiles: `base` + `contracts` focused modules, full root discovery, `git diff --check`, `ruff`.
- [x] Complete independent reviews (route-selected: code, test, security): code FAILed the first commit and
      PASSed the delivered bytes on re-review, the two test Criticals and all three security Importants are closed
      with arms; `evidence/residual-risks.md` records the seven things still open.
- [ ] Bind the `verification` and review receipts to the final tree fingerprint.
- [ ] Push branch, open pull request, wait for the App-owned exact-SHA check; merge is a separately delegated action.
