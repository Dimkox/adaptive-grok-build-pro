# Analysis — repo_explorer

| Contradiction | Current | Tests | Touch |
| --- | --- | --- | --- |
| Wrapped `-c` | `_leading_argv` only; `_WRAPPERS` is sudo/time/nohup | no wrap cases | policy.py, test_policy.py |
| Follow-up leftover | hook uses `should_reuse_active_route(prompt)` only | follow-up same session reuses; leftover+repair rematches | router.py, user_prompt_submit.py, test_hooks.py, test_repo_router.py |
| rglob vs discover | `tests.rglob('test*.py')` | A1–A4 top-level only | verification.py, test_verification_doctor.py |
