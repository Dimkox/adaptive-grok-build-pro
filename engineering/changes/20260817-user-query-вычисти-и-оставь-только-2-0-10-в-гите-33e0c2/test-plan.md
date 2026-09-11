# Test plan

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | HEAD still v2.0.10 / 975ccb2 | `git rev-parse` / `git describe` |
| P0 | No leftover sibling dirt | `git status --porcelain` excluding this change id |
| P1 | Product tests still pass | `python3 scripts/grok_verify.py --mode pr` |
