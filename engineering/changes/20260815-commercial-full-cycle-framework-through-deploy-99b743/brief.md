# Commercial full-cycle framework through deploy

Change ID: `20260815-commercial-full-cycle-framework-through-deploy-99b743`
Created: 2026-08-15T00:42:47+00:00
Risk: high
Complexity: high-risk
Domains: generic

## Problem

The stack is a working adaptive development loop that **stops at review**. VERSION/CHANGELOG already say 2.0.4, but there is no 2.0.4 zip, no this-repo CI, no deploy stage, and no operator runbook. “Доведи до продакшена коммерческого фреймворка вплоть до деплоя” cannot mean a live `git push` / `gh release` from this agent: the route has `production_action_approval`, and AGENTS.md forbids unapproved publish.

## Outcome

After this change (and only after you approve this design):

1. The advertised loop includes a **gated deploy capability**: `grok_deploy.py` checks evidence and prints the exact human-owned publish commands.
2. This repo has optional GitHub Actions (verify + conditional package), docs, and a 2.0.4 publish runbook.
3. **No tag, push, or GitHub Release is created in this change.** That is a later `production_action_approval`.

## Scope

### In scope

- Prepare-only `scripts/grok_deploy.py`
- Extend `release-readiness` + one sentence in `adaptive-delivery`
- CI template + install on this repo
- Docs, runbook, installer `MANAGED_FILES`, tests

### Out of scope

- `git push` / tag / `gh release create` / docker/npm publish
- VERSION bump to 2.1.0
- New skill, service, queue, billing, EULA
- Matcher / hook baseline rewrite
- Real infra deploy adapters

## Constraints

- Human gates: `scope_and_design_approval` (now), `production_action_approval` (later publish)
- Uncommitted 2.0.4 hook/policy/verify work is baseline
- MIT stays
