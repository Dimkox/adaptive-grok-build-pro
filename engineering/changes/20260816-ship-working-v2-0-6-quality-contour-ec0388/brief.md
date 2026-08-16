# Ship working v2.0.6 quality contour

Change ID: `20260816-ship-working-v2-0-6-quality-contour-ec0388`
Route: `ec0388060302`
Write owner: `general_implementer`

## Problem

User: «всё полностью до рабочей версии 2.0.6 собирай». Prior approval (ef7b14) already chose Bucket A plus later optional consumer profiles.

## Outcome

Working 2.0.6 tree: first-class Ruff/Bandit/Coverage in `grok_verify`, Dependabot for GitHub Actions, thin skip-unless-signal Semgrep/Trivy/Prettier adapters, VERSION 2.0.6, CHANGELOG, tracked zip. GitHub tag/release is last mile, not this change.

## Scope

### In scope

- A: ruff.toml, bandit.yaml, measured coverage fail-under, dependabot github-actions
- B: emit Semgrep/Trivy-config/npm prettier|format only on consumer signals
- Identity + `packages/adaptive-grok-build-pro-v2.0.6.zip*`
- Tests first; CI installs A tools and runs the same `grok_verify --mode pr`

### Out of scope

- `pyproject.toml` / `requirements.txt` / `setup.py`
- Tag, push, `gh release`, retag 2.0.5
- Handbook dump / SaaS / new service
- Rewriting `verify()` to load quality-profile JSON
