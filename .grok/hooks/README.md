# Grok Build hooks

Project hooks require `/hooks-trust` in the Grok TUI.

- `.grok/hooks.json` — Codex-compat contract used by doctor/structure tests (`command` + `commandWindows`).
- `.grok/hooks/adaptive.json` — Grok discovery path (`<project>/.grok/hooks/*.json`).
- `.grok/hooks/*.py` — lifecycle adapters over `adaptive_grok` routing, policy, and receipts.

They accept both Codex snake_case and Grok camelCase stdin envelopes.
