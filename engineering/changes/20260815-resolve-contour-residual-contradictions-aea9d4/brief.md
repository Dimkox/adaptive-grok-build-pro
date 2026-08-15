# Resolve contour residual contradictions

Change ID: `20260815-resolve-contour-residual-contradictions-aea9d4`
Created: 2026-08-15T00:12:39+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

The last close named three residuals that contradict a complete working contour:

1. `bash -lc 'git push'` (and `bash -c` / `sh -c`) is not a production invocation.
2. Follow-up tokens (`делай`, `continue`) reuse leftover routes even when the leftover is from another session or already `ready`/`completed`.
3. `_python` lights unittest via `rglob` (deeper than discover) and the pytest-wins branch is untested.

## Outcome

Wrapped one-layer shell `-c`/`-lc` payloads are gated like the inner command. Follow-up reuse is only for an open route in the same session. Unittest detection matches `unittest discover -s tests`, and pytest-wins is characterized.

## Scope

### In scope

- One-layer unwrap of `bash|sh|zsh|dash|ksh -c/-lc` quoted payloads
- Same-session + non-closed-status gate on follow-up reuse
- `tests/test*.py` glob + pytest-wins test

### Out of scope

- Full shell parser; `python -c` / `os.system` unwrap
- HIGH_RISK substring scoring
- Hard Stop block
- Packaging, VERSION, GitHub release

## Constraints

- Keep path/echo/cat text allowed; keep `git push` / `gh pr merge` / `docker push` / `npm publish` / `gh release create` gated
- Child-agent payloads still skip rematch
- `делай` during an in-progress same-session route still reuses
