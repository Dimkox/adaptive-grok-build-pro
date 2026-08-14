# Grok Build hooks (optional)

Project hooks live here and require `/hooks-trust` in the Grok TUI.

The original Adaptive Codex Pro used Codex-specific lifecycle events
(UserPromptSubmit, PreToolUse, …). Those JSON payloads differ in Grok Build.

Recommended next step: add thin shell/python wrappers that call:

- `python scripts/grok_route.py` on session/prompt start
- `python scripts/grok_verify.py` before declaring done

See https://docs.x.ai/build/features/skills-plugins-marketplaces
