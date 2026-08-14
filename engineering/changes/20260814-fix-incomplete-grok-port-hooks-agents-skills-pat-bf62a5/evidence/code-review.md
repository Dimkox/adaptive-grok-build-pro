# Code review — bf62a5f2e873

Reviewer: `code_reviewer` (parent session; spawned `code_reviewer` child could not persist a report)
Tree inspected: working copy after hook/agent/installer repair
Scope: `.grok/hooks*`, `.grok/agents/`, `.agents/skills/`, `scripts/install_into.py`, `tests/_support.py`, `.grok/config.toml`, `Makefile`, `VERSION`, `docs/bitrix-local-AGENTS.md`

## Verdict

**pass** — no blocking defects. Policy/router/Bitrix checks were not rewritten. The missing scaffold now matches doctor and hook contracts.

## Findings

### Medium — dual skill trees can drift

`.grok/skills/` and `.agents/skills/` are copies. Doctor and structure tests only watch `.agents/skills`. A later skill edit in one tree will desync the other. Acceptable for this port; document `.grok/skills` as source of truth.

### Low — `stop_gate.py` duplicate branches

`stop_hook_active` true/false both emit the same block payload. Harmless; increment_stop_attempt still runs.

### Low — installer now manages the entire `.grok/` tree

`--force` overwrites project `.grok/config.toml` and hook files. Tests require this. Operators should review `--force` before applying to a repo with local Grok config.

### Info — Grok `.md` agents sit beside Codex `.toml` agents

Needed so routed types can be spawned. Tests only validate `.toml`.

## Safety

- `.env` remains gitignored; no secrets in the inspected files.
- `evaluate_pre_tool` still blocks `.env` reads, Bitrix core writes, destructive git, unapproved production/MCP writes.
- `project_copy` wipes `.grok-stack/runtime` except `.gitkeep`, so harness copies do not inherit this session's route.

## Residual risk

Project hooks require `/hooks-trust`. Until trusted, Grok will not enforce PreToolUse/Stop in the TUI even though scripts exist.

## Recommendation

pass
