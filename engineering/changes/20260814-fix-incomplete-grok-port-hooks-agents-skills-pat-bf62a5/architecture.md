# Architecture — Fix incomplete Grok port

## Current behavior

Skills exist only under `.grok/skills/`. There are no managed agents, no hook scripts, and no `.grok/hooks.json`. Installer and test copies still look for Codex `.codex/` and do not install `.grok/`.

## Proposed behavior

Dual-layout port that matches tests and Grok discovery:

```
.grok/config.toml          # Grok + Codex contract keys
.grok/hooks.json           # doctor/structure contract (command + commandWindows)
.grok/hooks/*.py           # executable hook scripts
.grok/hooks/adaptive.json  # Grok project-hook discovery
.grok/agents/*.toml        # 21 managed agents
.grok/skills/              # Grok-native skills
.agents/skills/            # Codex-compat / doctor skill root (mirror)
```

Hook scripts are thin adapters over `adaptive_grok.router`, `policy`, `state`, and `receipts`.

## Components and boundaries

- Policy and routing stay in `.grok-stack/adaptive_grok/`
- Hooks only translate I/O and call existing functions
- Installer copies `.grok`, `.agents`, `.grok-stack` (skip missing; skip runtime state)

## Decisions

1. Keep `.agents/skills` as a mirror rather than moving skills off `.grok/skills` (Grok loads both).
2. Do not require `.codex/` after the port.
3. Parent session implements as `general_implementer` because custom agent types cannot be spawned until this change lands.

## Risks and mitigations

- Runtime leak into tests → wipe `.grok-stack/runtime` except `.gitkeep` in `project_copy`
- Skill drift between two trees → copy from `.grok/skills` as the source
- Grok ignores `.grok/hooks.json` → also register `.grok/hooks/adaptive.json`
