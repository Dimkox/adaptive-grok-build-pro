# Analysis — architect

Route has **no write owner**. Scope is release assembly, not new product work.

## Decision

Ship **v2.0.0** from the current working tree plus release notes. The hook/agent/installer repair is already implemented and verified (80 tests, doctor clean).

## Keep unchanged

- Zip member prefix `adaptive-codex-pro/` (test contract)
- Router/policy/verification engines
- Public MIT license, no required hosted CI

## Release-only files allowed

- `CHANGELOG.md`
- README/QUICKSTART corrections so the shipped hooks are documented (`python3`, `/hooks-trust`)
- This change package and human-gate evidence

## Steps

1. Record scope + production gates (user message + `grok_approve.py`)
2. Commit assembly
3. `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`
4. `python3 scripts/package_stack.py --output dist/adaptive-grok-build-pro-v2.0.0.zip`
5. Independent `security_reviewer` + `release_reviewer`
6. Bind verification/security/release receipts
7. Tag `v2.0.0`, push `main` + tag, create public GitHub Release

## Rollback

Delete the GitHub Release and tag `v2.0.0`. Revert the release commit on `main` if needed. No data migrations.
