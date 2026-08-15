# Test plan — Resolve contour residual contradictions

## Fail first

### Policy (`tests/test_policy.py`)

- `test_wrapped_shell_push_requires_approval` — `bash -lc 'git push origin feature'`, `bash -c "git push origin feature"`, `sh -c 'npm publish'` deny
- `test_wrapped_shell_chained_push_requires_approval` — `bash -lc 'cd dist && git push origin feature'` deny
- `test_wrapped_shell_echo_is_not_a_side_effect` — `bash -lc 'echo git push origin feature'` allow
- `test_approval_lifts_wrapped_shell_push` — after production approval, wrapped push allows

Keep existing path/echo/cat/approve-script/direct-invocation tests green.

### Rematch (`tests/test_repo_router.py` + `tests/test_hooks.py`)

- `test_can_reuse_requires_same_session_and_open_status` — helper cases
- Hook: same session, status routed, `делай` → same route_id (existing `test_followup_reuses_active_route`)
- Hook: leftover session A, `делай` session B → new route_id
- Hook: same session, status ready, `делай` → new route_id
- Child brief still keeps leftover (existing test)

### Verify (`tests/test_verification_doctor.py`)

- `test_python_ignores_nested_unittest_without_top_level` — `tests/nested/test_x.py` → `_python` == []
- `test_python_pytest_wins_when_project_marker_present` — mock pytest present + pyproject.toml → pytest check, no python-unittest

## Verification

```bash
python3 -m unittest discover -s tests
python3 scripts/grok_doctor.py
```
