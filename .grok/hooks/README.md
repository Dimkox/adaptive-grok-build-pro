# Grok Build hooks (Adaptive)

Project hooks need `/hooks-trust` in the Grok TUI.

## Soft mode (default since v2.0.4)

- **PreToolUse**: real policy when import works; on any error → **allow**
- **Stop**: evidence gaps are **warnings only**, never block the agent

Hard lockouts (exit 2 / infinite stop loops) are intentional bugs — fixed in 2.0.4.

## Disable all hooks

```bash
mv .grok/hooks .grok/hooks.disabled
# or set in config:
# [features]
# hooks = false
```

Then restart `grok`.

## Policy still enforced when healthy

Secrets (`.env`, keys), destructive shell (`rm -rf /`, `git push --force`), and Bitrix core paths remain blocked by `policy.py` when the stack imports cleanly.
