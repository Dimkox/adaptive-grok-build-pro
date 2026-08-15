# Human approval

## scope_and_design_approval — granted

At: 2026-08-15
Decision: **Да — утверждаю дизайн 2.0.4**

Accepted:

- Complete 2.0.4, do not open 2.1.0
- Prepare-only `scripts/grok_deploy.py`; extend `release-readiness`; no new skill
- CI from template + conditional package job; no publish job
- Docs + runbook
- No `git push` / `gh release` / `docker push` in this change

## production_action_approval — not granted

Tag, push, and GitHub Release stay blocked.
