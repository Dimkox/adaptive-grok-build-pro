# Rollback — Complete working Adaptive Grok contour

Revert:

- `.grok-stack/adaptive_grok/verification.py`
- `tests/test_verification_doctor.py`
- `tests/test_change_receipts.py`
- `README.md`, `QUICKSTART.md`, `CHANGELOG.md`

No data repair. Reverting `_python` restores hollow verify (unit tests not run by `grok_verify`). Prefer forward-fix.

After rollback: `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`.
