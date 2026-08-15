# Rollback

Revert:

- `.grok-stack/adaptive_grok/policy.py`
- `.grok-stack/adaptive_grok/router.py`
- `.grok-stack/adaptive_grok/verification.py`
- `.grok/hooks/user_prompt_submit.py`
- `tests/test_policy.py`, `tests/test_repo_router.py`, `tests/test_hooks.py`, `tests/test_verification_doctor.py`
- `CHANGELOG.md`

No data repair. After rollback: `python3 -m unittest discover -s tests`.
