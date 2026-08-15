# Complete working Adaptive Grok contour

Change ID: `20260814-complete-working-adaptive-grok-contour-2eacdf`
Created: 2026-08-14T23:44:07+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

Lockout repair `757a43` is ready (invocation policy, follow-up-only rematch, child-brief skip, live hooks). The advertised contour is still hollow: `python3 scripts/grok_verify.py --mode pr` never runs this repo's unit tests because `verification._python` only activates when `pyproject.toml` / `requirements.txt` / `setup.py` exist. This stack has `tests/` and no those markers. README still says v2.0.3. QUICKSTART.md leaves `/hooks-trust` inside the verify fence.

## Outcome

A user can run the documented loop — route → change package → implement → `grok_verify` (which actually executes `python-unittest` when `tests/test*.py` exist) → review receipts → `grok_status` with zero evidence gaps — and docs match VERSION `2.0.4`.

## Scope

### In scope

- Run `python-unittest` from `grok_verify` when `tests/` contains `test*.py`, without adding a Python-project marker
- End-to-end contour characterization test on `project_copy`
- README H1 / QUICKSTART fence / one CHANGELOG 2.0.4 bullet

### Out of scope

- Packaging, tags, GitHub release, VERSION bump
- `grok_change status` CLI alias
- HIGH_RISK substring scoring, hard Stop block, wrapped-shell policy
- Committing, merge, push, deploy

## Constraints

- Backward compatibility: keep pytest/ruff only when a Python-project marker exists; do not change `detect_repo`
- Security: do not weaken secret, Bitrix core, destructive, or production-invocation gates
- Operational: no new services or dependencies; lockout repair stays as baseline
