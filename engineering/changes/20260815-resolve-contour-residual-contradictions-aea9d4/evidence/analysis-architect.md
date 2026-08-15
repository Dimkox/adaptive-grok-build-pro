# Analysis — architect

Route `aea9d4f3b060`. Resolve three residuals. Not a release.

## Files

| File | Change |
| --- | --- |
| `.grok-stack/adaptive_grok/policy.py` | `_unwrap_shell` + use in `is_production_invocation` |
| `.grok-stack/adaptive_grok/router.py` | `CLOSED_ROUTE_STATUSES`, `can_reuse_active_route` |
| `.grok/hooks/user_prompt_submit.py` | call `can_reuse_active_route` |
| `.grok-stack/adaptive_grok/verification.py` | `glob('test*.py')` |
| `tests/test_policy.py` | wrapped-shell cases |
| `tests/test_repo_router.py` | `can_reuse` helper cases |
| `tests/test_hooks.py` | session mismatch + ready status |
| `tests/test_verification_doctor.py` | nested glob + pytest-wins |
| `CHANGELOG.md` | 2.0.4 bullets |

Keep `should_reuse_active_route(prompt)` as FOLLOW_UP_RE only so existing unit tests stay meaningful.
