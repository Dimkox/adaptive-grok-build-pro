# Adaptive Grok Build Pro v2.0.0

Port of Adaptive Codex Pro to **Grok Build** (xAI CLI coding agent).

## What this is

Enterprise-style adaptive workflow for Grok Build:

- Task routing + domain skills (Bitrix, API/events, data, frontend, security, incidents, …)
- Quality profiles and change packages under `engineering/changes/`
- Verification / review receipts via `scripts/grok_*.py`
- Multi-agent discipline described in `AGENTS.md`

## Requirements

- [Grok Build CLI](https://x.ai/build) (`grok`) installed and authenticated (SuperGrok / X Premium+)
- Python 3.10+
- Git

## Install into a project

```bash
# from this package root
python3 scripts/install_into.py /path/to/your/repo
```

Or copy manually:

```text
.grok/            → project .grok/          (config, hooks, agents, skills)
.agents/skills/   → project .agents/skills/
.grok-stack/      → project .grok-stack/
scripts/          → project scripts/
AGENTS.md         → project AGENTS.md
engineering/      → project engineering/  (if empty scaffold needed)
```

Then in the project:

```bash
cd /path/to/your/repo
grok inspect    # should see skills + AGENTS.md
grok            # start TUI
```

Invoke the main controller skill:

```text
/adaptive-delivery
```

or just describe a development task — Grok should pick up skills from `.grok/skills/`.

## Scripts

| Script | Role |
|--------|------|
| `scripts/grok_route.py` | Classify / show route |
| `scripts/grok_change.py` | Start durable change package |
| `scripts/grok_status.py` | Runtime status |
| `scripts/grok_verify.py` | Verification gate |
| `scripts/grok_review.py` | Record review receipt |
| `scripts/grok_doctor.py` | Health check |
| `scripts/install_into.py` | Install stack into target repo |

## Hooks

Lifecycle adapters live in `.grok/hooks/` and are registered in both:

- `.grok/hooks.json` — doctor/structure contract (`command` + `commandWindows`)
- `.grok/hooks/adaptive.json` — Grok project-hook discovery

Trust the folder once (`/hooks-trust` or `grok --trust`). Hooks classify prompts, enforce policy (secrets, Bitrix core, destructive/production commands), and block Stop until required receipts exist.

## Package

```bash
python3 scripts/package_stack.py --output dist/adaptive-grok-build-pro-v2.0.0.zip
```

The zip filename is `adaptive-grok-build-pro-v2.0.0.zip`. Members stay under `adaptive-codex-pro/` for compatibility with the existing manifest tests.

## Bitrix

See skills under `.grok/skills/bitrix-development/` and example module in `examples/bitrix-module/`.

## License

Same as upstream package (see `LICENSE`).

## License & CI

**MIT.** No GitHub Actions, no paid hosted CI required.
Local: `make doctor` / `make verify`.
