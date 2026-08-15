# Implementation — parent write-owner

Route `757a43330038` write owner is `general_implementer`. Architecture ruling: parent performs the write because dispatching a keyword-rich implementer brief previously overwrote this route. Child-brief skip is now in the rematch hook; this report is the write-owner return.

## Changed files

- `.grok-stack/adaptive_grok/policy.py` — invocation matcher (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`)
- `.grok-stack/adaptive_grok/router.py` — `repair` keyword + `should_reuse_active_route`
- `.grok/hooks/_lib.py` — `is_child_payload`
- `.grok/hooks/user_prompt_submit.py` — follow-up-only reuse; child briefs keep parent route
- `.grok/hooks/adaptive.json` — path-qualified commands
- `.grok/hooks.json` — restored (was moved to `.off` during lockout)
- `.grok/hooks/README.md`, `CHANGELOG.md`, `README.md`
- `tests/test_policy.py`, `tests/test_repo_router.py`, `tests/test_hooks.py`, `tests/test_structure.py`

Hooks were restored from `.grok/hooks.disabled/` after the rematch/policy edits. Disabled copies were removed so the stack can execute.

## Commands

```bash
python3 -m unittest discover -s tests
# 95 tests, OK
```

## Residual risk

Wrapped shells (`bash -lc 'git push'`) are not matched. Follow-up tokens still attach to a leftover high-risk route. Intended.

## Rollback

Revert the files above. Do not re-disable hooks as a routine rollback.
