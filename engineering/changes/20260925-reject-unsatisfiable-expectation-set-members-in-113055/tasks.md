# Tasks — Reject unsatisfiable expectation-set members in typed specs at plan time

- [x] Freeze contracts and expected behavior: confirmed the independent holdout pins a criterion to exactly
  `id`, `statement`, `evidence`, so no new document field is available; the obligation must ride on existing
  prose plus existing evidence kinds. Contract surface for this change is
  `schemas/change-spec.schema.json` (annotation only).
- [x] Reproduce first: `engineering/changes/**` measured with the shipped validator — 0 criteria declare a
  brace set at all, so the defect is invisible to every static check today; a synthetic spec declaring
  `exactly {css-link-count, frozen-plan-text}` was accepted by `validate_spec` in both profiles.
- [x] Add the failing/characterization test module `tests/test_spec_expectation_sets.py` (19 tests): dead
  member rejected and named, fully-probed accepted, upper bound without non-emptiness rejected, placeholder
  and JSON brace groups inert, historical packages gain no finding.
- [x] Implement the smallest vertical change: `expectation_set_findings` in
  `.grok-stack/adaptive_grok/spec.py`, wired into `_semantic_errors` for both profiles; one annotation in
  `schemas/change-spec.schema.json`; one obligation paragraph in the change-package requirements template.
- [x] Run the selected quality profile (base + contracts): module green, spec-adjacent modules green,
  before/after sweep over 106 packages identical, mutation battery kills 9 mutants of the new rule.
- [x] Bind the typed spec: `scripts/grok_spec.py validate --gate` returns `ok: true` for this package.
- [ ] Complete independent reviews (code_review, test_review) on the frozen tree.
- [ ] Record fingerprint-bound local evidence and deliver the branch through a pull request.
