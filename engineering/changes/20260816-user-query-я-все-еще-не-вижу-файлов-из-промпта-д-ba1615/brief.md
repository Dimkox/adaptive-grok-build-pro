# Put agent-prompt log files in the repo root

Change ID: `20260816-user-query-я-все-еще-не-вижу-файлов-из-промпта-д-ba1615`
Route ID: `ba1615416da5`

## Problem

The agent prompt names `decisions.md` and `mistakes.md`. Those files are only under `engineering/`. The root listing is `AGENTS.md`, `CHANGELOG.md`, `QUICKSTART.md`, `README.md`. The user still cannot see the prompt files in the root.

## Outcome

`decisions.md` and `mistakes.md` exist at the repository root. `AGENTS.md` first section names those exact filenames. Existing entries are not lost.

## Scope

### In scope

- Move the two logs to the root.
- Point `AGENTS.md` at `decisions.md` / `mistakes.md` (original prompt wording).
- Lock with a structure test: files exist at root; first `##` names those paths, not `engineering/`.
- Leave a one-line pointer in the old `engineering/` paths so historical links do not become a second live log.

### Out of scope

- Version bump, zip rebuild, git push, GitHub Release.
- Rewriting old change-package citations of `engineering/decisions.md`.
- GitHub Actions, `pyproject.toml`.

## Constraints

- One source of truth: root files. Do not keep two append-only logs.
