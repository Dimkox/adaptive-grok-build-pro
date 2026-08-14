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
python scripts/install_into.py /path/to/your/repo
```

Or copy manually:

```text
.grok/skills/     → project .grok/skills/
.grok/config.toml → project .grok/config.toml
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

## Hooks note

Original Codex hooks (`UserPromptSubmit`, `PreToolUse`, …) are **not** 1:1 portable.
Grok Build uses its own hook model under `.grok/hooks/` (needs `/hooks-trust`).

This port keeps the **Python policy/routing engine** and **skills**. Automatic route injection on every prompt is manual until you wire Grok hooks to `scripts/grok_route.py` / stack entrypoints.

## Bitrix

See skills under `.grok/skills/bitrix-development/` and example module in `examples/bitrix-module/`.

## License

Same as upstream package (see `LICENSE`).

## License & CI

**MIT.** No GitHub Actions, no paid hosted CI required.
Local: `make doctor` / `make verify`.
