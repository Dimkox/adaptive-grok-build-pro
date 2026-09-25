# Tasks — architecture model path-shape preflight with located diagnostics

- [x] Freeze contracts and expected behavior. Architecture documents, schemas and generated views
  are explicitly out of scope; the rejected path-shape set is frozen as-is (INV-001).
- [x] Add the failing evidence before the repair. The defect was reproduced with the pre-fix code in
  a private scratch copy (`~/.cache/issuewave-50/before`, one injected line
  `"factory/runtime/",` at `architecture/system.yaml:2263`):
  `Ran 924 tests in 453.136s` / `FAILED (failures=1, errors=40)` — 40 errors in eight modules plus one
  failure in a ninth, every copy of
  the message unlocated. The permanent regression assertions then live in
  `tests/test_architecture_model_preflight.py`; its first local runs went red for fixture reasons
  (rules `severity` enum, and the rules path loop not yet routed through the located check), which
  is what caught the missing wiring in `_validate_rule_semantics`.
- [x] Implement the smallest vertical change: `_path_shape_problem()` reason classification,
  `document`/`line` on `ArchitectureError`, canonical-text line resolution for declared paths,
  `preflight_architecture()`, and the `architecture-model` doctor item.
- [x] Run selected quality profile: module suite, neighbouring architecture/governance/receipt/
  structure/doctor suites, ruff, `git diff --check`, then one `grok_verify --mode pr`.
- [ ] Complete independent reviews (route-selected `code_reviewer` and `test_reviewer` receipts).
- [ ] Bind evidence to the final tree fingerprint (`python3 scripts/grok_review.py ...` after the
  reviews; a receipt goes stale after any later repository change).
