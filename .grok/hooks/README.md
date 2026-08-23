# Grok Build hooks (Adaptive)

Project hooks need `/hooks-trust` in the Grok TUI.

## Soft local guardrails

- **PreToolUse** runs repository policy when imports succeed; an infrastructure error still fails open so a broken hook cannot freeze the session.
- **Stop** reports missing or stale evidence as a warning and never creates a retry loop.
- Production commands, workflow dispatch, MCP writes, and control-plane edits are denied whenever policy is healthy. A local approval request never lifts those denials.

Root shims dispatch into `.grok/hooks/` and retain fail-open fallbacks for recovery after an incomplete pull.

## Disable local hooks

```bash
mv .grok/hooks .grok/hooks.disabled
# or set in config:
# [features]
# hooks = false
```

Then restart `grok`. Disabling hooks removes local convenience guardrails; it does not bypass protected branches, required GitHub checks, CODEOWNERS, or the `production` Environment.

## External authority

Hooks are not an operating-system security boundary. `.github/workflows/trusted-ci.yml`, branch protection, CODEOWNERS, and `.github/workflows/release.yml` provide the independent merge and release boundary described in `docs/TRUST-BOUNDARY.md`.

When healthy, policy blocks secrets, destructive shell commands, Bitrix core paths, the control plane, and real side-effect invocations such as `git push`, `gh pr merge`, `gh workflow run`, `docker push`, `npm publish`, and `gh release create`. Bare words in file paths or `echo` and `cat` arguments are not side effects.
