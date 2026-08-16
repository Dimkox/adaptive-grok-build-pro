# Architecture

`AGENTS.md` is hand-authored and copied verbatim into consumer repos by `install_into.merge_agents`. It is not generated.

The two log files already live at:

- `engineering/decisions.md` — “Patterns that paid for themselves. Each entry is at most three sentences.”
- `engineering/mistakes.md` — “Root causes, not symptoms.”

Those files are this-repo memory. Change-package `## Decisions` is per-change. Do not fold the loop into the change package.

Place a new first section immediately after the H1, before the contract intro and before `## Mandatory entrypoint`. Point at the `engineering/` paths so agents do not create root-level `decisions.md` / `mistakes.md`.

Lock with `tests/test_structure.py`: `AGENTS.md` must contain both paths and both verbs (`log it in`, `record it in`) before `## Mandatory entrypoint`.
