# Implementation

Change: `20260816-the-user-sent-a-message-while-you-were-working-u-f1bdb9`  
Route: `f1bdb94f5af3` · write owner: `general_implementer`

README is now the standing push-time product map. `VERSION` stays `2.0.8`. No push, tag, or zip from this owner.

## SHA

`ffd30fd901359dfeead7c37c289e502e651c5084`  
Subject: `Require current complete-graph README before every push; record ship evidence`

This report is written after the commit so it can record the SHA. It is intentionally uncommitted (same wave as upcoming review reports).

## What changed

| Path | Change |
| --- | --- |
| `AGENTS.md` | New `## README before push` immediately after the self-learning bullets. Requires refresh before `git push` / `grok_deploy` and a complete pairwise `---` graph. |
| `decisions.md` | New 2026-08-16 entry: `README is the push-time product map`. |
| `README.md` | After the H1/pitch: Current state, Read first, How work runs, Map. Existing K10 mermaid (45 edges) kept. Names `QUICKSTART.md`, `CHANGELOG.md`, `2.0.8`. |
| `tests/test_structure.py` | `test_agents_md_requires_readme_refresh_before_push`, `test_decisions_md_records_readme_before_push`, `test_readme_names_onboarding_docs_and_current_version`. Existing `test_readme_stack_graph_is_complete` unchanged. |
| f1bdb9 + 79f406 packages | Included. Already-staged keeper change-package files from cleanup also went in this commit. |

Not touched: `VERSION` (2.0.8), packager, zip, `pyproject.toml`, GitHub Actions, tag, push.

## Red then green

Before the docs:

```
python3 -m unittest \
  tests.test_structure.StructureTests.test_agents_md_requires_readme_refresh_before_push \
  tests.test_structure.StructureTests.test_decisions_md_records_readme_before_push \
  tests.test_structure.StructureTests.test_readme_names_onboarding_docs_and_current_version \
  tests.test_structure.StructureTests.test_readme_stack_graph_is_complete -q
```

- `test_agents_md_requires_readme_refresh_before_push` — `AssertionError: '## README before push' not found`
- `test_decisions_md_records_readme_before_push` — `AssertionError: 'README is the push-time product map' not found`
- `test_readme_names_onboarding_docs_and_current_version` — `AssertionError: 'QUICKSTART.md' not found`
- `test_readme_stack_graph_is_complete` — ok (K10, 45 edges)

After the docs:

```
python3 -m unittest tests.test_structure -q
```

`Ran 20 tests in 0.011s` · `OK`

## Residual risk

- Official `grok_verify --mode pr` and independent `code_review` / `test_review` are not recorded here. Controller runs those after this stop (fingerprint includes HEAD plus this uncommitted report).
- GitHub Release Latest may still be an older tag until a human last mile creates `v2.0.8`. This owner does not tag or push.
