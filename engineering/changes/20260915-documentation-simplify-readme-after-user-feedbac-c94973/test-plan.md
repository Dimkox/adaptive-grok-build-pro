# Verification

Baseline: 35 existing state/structure tests pass. Update only existing graph-specific assertions and stale documentation checks as required; retain meaningful model/rule/view links and manual-adoption coverage. Run focused state/structure tests, whitespace and relative-link checks, then the mandatory grok_verify --mode pr with UV_FROZEN=1 and stable source. Route-selected code_reviewer inspects the final diff after full verification. No new tests that merely mirror prose edits; actual immutable archive and packaging behavior tests remain.
