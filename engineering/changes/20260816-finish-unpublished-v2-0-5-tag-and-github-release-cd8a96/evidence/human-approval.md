# Human approval

**production_action_approval** granted 2026-08-16 by user.

- Prior: «гит пуш пакет релиз» then «да»; «смерджи все»
- This prompt: they see GitHub Latest 2.0.4 and said «делай»

Authorized last mile: push existing local tag `v2.0.5`, create GitHub Release `v2.0.5` with existing zip + sha256 + `dist/RELEASE-NOTES.md`. Do not force-push. Do not touch `v2.0.4`. Do not print secret values.

Machine token: `python3 scripts/grok_approve.py production` recorded in this session before the two commands.
