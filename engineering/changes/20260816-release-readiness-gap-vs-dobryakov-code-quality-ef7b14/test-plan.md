# Test plan

Design-only. No new product tests on this route.

If a later slice implements Ruff:

1. Characterization: `grok_verify --mode pr` still runs `python-unittest` (must not skip because of a new packaging marker)
2. Fail: introduce an unused import, expect `ruff` fail
3. CI installs ruff and fail-closes
4. Local without ruff: skip, not fail
