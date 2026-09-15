# Test plan — Caroline cross-project M8 evidence

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Case/index do not claim M8 acceptance, activation or authority; repository-bound cohorts stay separate | Source review and independent code review |
| P1 | Pinned links, SHAs, issue/PR state and test limits match observed sources | `gh` read-only inspection, Markdown link check |
| P1 | No runtime, schema, state or release artifact changes | `git diff --name-only`, `git diff --check` |

Run `python3 scripts/grok_verify.py --mode pr` as route-selected preflight, then selected `code_reviewer`. Documentation change does not justify implementation-mirroring unit tests. Full WPF and live SDK tests belong to Caroline PR #13 and are not claimed here.
