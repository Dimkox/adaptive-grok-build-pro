# Grok Build hooks

Project hooks require `/hooks-trust` in the Grok TUI.

- `.grok/hooks.json` — doctor/structure contract (`command` + `commandWindows`).
- `.grok/hooks/adaptive.json` — Grok discovery path (`<project>/.grok/hooks/*.json`).
- `.grok/hooks/*.py` — lifecycle adapters over `adaptive_grok` routing, policy, and receipts.

They accept both snake_case and camelCase stdin envelopes.
