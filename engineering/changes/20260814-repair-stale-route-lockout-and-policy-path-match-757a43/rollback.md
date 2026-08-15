# Rollback — Repair stale-route lockout and policy path matching

Revert the files listed in `architecture.md`. No schema or data repair.

- Reverting policy restores the path-word lockout. Prefer forward-fix.
- Reverting rematch restores leftover-route stickiness and child-brief overwrite.
- Leave the warn-only Stop test in place even if policy/rematch is rolled back.

Verification after rollback or forward-fix: `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`.
