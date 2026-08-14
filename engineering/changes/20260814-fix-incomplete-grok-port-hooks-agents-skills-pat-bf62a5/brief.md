# Fix incomplete Grok port: hooks, agents, skills paths, installer

Change ID: `20260814-fix-incomplete-grok-port-hooks-agents-skills-pat-bf62a5`
Created: 2026-08-14T19:34:03+00:00
Risk: low
Complexity: micro (routed) / bounded scaffold completion
Domains: generic

## Problem

The Adaptive Codex Pro → Grok Build port shipped policy/router/skills but not the files the harness tests and doctor require. `python3 -m unittest discover -s tests` reports 67 errors and 7 failures. Doctor reports 39 missing agents/skills/hooks.

## Outcome

A developer can clone the repo, run `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py` with zero failures. Grok can trust project hooks and discover skills from both `.grok/skills` and `.agents/skills`.

## Scope

### In scope

- `.grok/hooks.json` and hook scripts that satisfy `tests/test_hooks.py`
- Grok-native hook registration under `.grok/hooks/`
- 21 managed agent TOML files
- Skill mirror at `.agents/skills/`
- `VERSION`, Bitrix local AGENTS doc, CI template
- Installer and `project_copy` path fixes
- Makefile `python3`

### Out of scope

- Router/policy/verification logic changes
- Renaming package zip prefix `adaptive-codex-pro/`
- Production deploy or git push
- Full Grok `.md` agent marketplace packaging

## Constraints

- Backward compatibility: keep existing Python APIs and hook stdout fields used by tests
- Data/privacy: do not commit `.env` or runtime receipts
- Operational: hooks must fail closed only when policy explicitly denies; missing route is not an error for session start
