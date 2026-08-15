# Architecture — Resolve contour residual contradictions

## Decisions

1. **One quoted `-c` layer.** After chunk split, if the chunk is `bash|sh|zsh|dash|ksh` with a flags token containing `c` (`-c`, `-lc`, …), strip matching quotes from the remainder and run the existing `_leading_argv` matcher on that inner command. Destructive regex already sees the full string. No `python -c`.
2. **Follow-up needs an open same-session route.** Keep `should_reuse_active_route(prompt)` as FOLLOW_UP_RE only. Add `can_reuse_active_route(prompt, existing, session_id)` used by the hook: follow-up AND `existing.session_id == session_id` AND `existing.status` not in `{ready, released, completed, cancelled, archived}`. Child payloads still skip rematch.
3. **Discover-shaped unittest files.** `has_unittest_files` uses `tests.glob('test*.py')`. Pytest-wins stays: marker + pytest + tests dir → run pytest and return. Characterize with mocks.

## Control flow

```
is_production_invocation(command):
  for chunk in split(command):
    argv = leading_argv(unwrap_shell(chunk))
    match PRODUCTION_INVOCATIONS prefixes

UserPromptSubmit:
  child? reuse
  can_reuse_active_route(prompt, existing, session)? reuse
  else rematch

_python:
  if marker:
    ruff?
    if pytest and tests/: pytest; return
  if tests/test*.py: python-unittest
```

## What does not change

Stop fail-open, production prefix list, FOLLOW_UP_RE, HIGH_RISK, VERSION, packaging.
