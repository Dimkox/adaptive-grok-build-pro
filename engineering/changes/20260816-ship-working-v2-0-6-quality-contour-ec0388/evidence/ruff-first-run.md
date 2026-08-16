# Ruff first run — 2026-08-16

Command:

```bash
ruff check .grok-stack/adaptive_grok scripts tests .grok/hooks \
  user_prompt_submit.py pre_tool_use.py post_tool_use.py pre_compact.py \
  session_start.py session_end.py stop_gate.py subagent_start.py subagent_stop.py
```

- ruff 0.16.3
- First run: **exit 1**, **8 findings**, all `F401` unused imports
- Files: `policy.py`, `repo.py`, `router.py`, `toolchain.py`, `verification.py`, `scripts/package_stack.py`, `tests/_support.py`, `tests/test_toolchain.py`
- After removing those unused imports (no format rewrite): **exit 0**, **0 findings**
