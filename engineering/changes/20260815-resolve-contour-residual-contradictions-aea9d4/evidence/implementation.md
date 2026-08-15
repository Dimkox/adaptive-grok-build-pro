# Implementation — resolve contour residual contradictions

Route `aea9d4f3b060`. Write owner: `general_implementer`. Fail-first tests landed, then the three residual fixes.

## Changed files

- `.grok-stack/adaptive_grok/policy.py` — `_unwrap_shell`; `is_production_invocation` unwraps then re-chunks
- `.grok-stack/adaptive_grok/router.py` — `CLOSED_ROUTE_STATUSES`, `can_reuse_active_route`; `should_reuse_active_route` stays FOLLOW_UP_RE-only
- `.grok/hooks/user_prompt_submit.py` — reuse leftover only for child payloads or `can_reuse_active_route`
- `.grok-stack/adaptive_grok/verification.py` — `has_unittest_files` uses `tests.glob('test*.py')`
- `tests/test_policy.py` — wrapped-shell deny / echo-allow / approval-lift
- `tests/test_repo_router.py` — `can_reuse` session + closed-status cases
- `tests/test_hooks.py` — rematch on session mismatch and `ready` leftover
- `tests/test_verification_doctor.py` — nested glob + pytest-wins characterization
- `CHANGELOG.md` — 2.0.4 bullets (VERSION not bumped)

## Fail-first (current tree, before implementation)

```text
test_wrapped_shell_push_requires_approval ... FAIL
  AssertionError: True is not false : bash -lc 'git push origin feature'
test_wrapped_shell_chained_push_requires_approval ... ok   # naive && split already denied
test_wrapped_shell_echo_is_not_a_side_effect ... ok
test_approval_lifts_wrapped_shell_push ... ok              # already allowed without unwrap
test_can_reuse_requires_same_session_and_open_status ... ERROR
  ImportError: cannot import name 'can_reuse_active_route'
test_followup_reuses_active_route ... ok
test_followup_rematches_when_session_differs ... FAIL     # leftover route_id kept
test_followup_rematches_when_route_is_ready ... FAIL      # leftover route_id kept
test_child_agent_brief_does_not_replace_parent_route ... ok
test_python_ignores_nested_unittest_without_top_level ... FAIL
  python-unittest lit via rglob
test_python_pytest_wins_when_project_marker_present ... ok
```

## Post-fix

```bash
python3 -m unittest discover -s tests
# Ran 109 tests in 10.216s
# OK
```

Targeted new cases plus path/echo/cat/direct-invocation and child-brief tests all pass.

## Residual risk

- One quoted `-c`/`-lc` layer only. `python -c`, `os.system`, nested shells, and `bash -l -c` (two flag tokens) are not unwrapped.
- `_command_chunks` is still not quote-aware; a quoted `&&` at the outer level can still split before unwrap. The chained wrapped-push case is covered because unwrap-then-resplit and the naive split both see `git push`.
- HIGH_RISK substring scoring, Stop fail-open, packaging, and VERSION are unchanged.

## Rollback

Revert the files listed above. Do not bump VERSION or ship a package from this change.
