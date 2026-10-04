# Grok Build hooks (Adaptive)

Project hooks need `/hooks-trust` in the Grok TUI.

## Soft mode (default since v2.0.4)

- **PreToolUse**: real policy when import works; on any error → **allow**
- **Stop**: evidence gaps are **warnings only**, never block the agent

Hard lockouts (exit 2 / infinite stop loops) are intentional bugs — fixed in 2.0.4.
Canonical source hooks live in `.grok/hooks/`. For older `adaptive.json` files that call `python3 pre_tool_use.py` from a consumer project root, the installer generates nine compatibility aliases from `.grok-stack/templates/hook_root_shim.py`; these aliases dispatch to canonical hooks or preserve the fail-open JSON fallback. Generated consumer aliases are not tracked source-root files.

## Disable all hooks

```bash
mv .grok/hooks .grok/hooks.disabled
# or set in config:
# [features]
# hooks = false
```

Then restart `grok`.

## Local child lifecycle

SubagentStart records a known child ID and returns its generation, route and task identity. Pre/PostToolUse record closed activity only for that explicit child and generation; activity does not mean useful progress. SubagentStop remains empty and cannot clear an interrupted or resumed owner through an unversioned event. Use `python3 scripts/grok_agent.py` for heartbeat, checkpoints, finite watchdog polling and matching control ACKs. The controller must observe native interruption before recording interrupt-ack and same-task resume. The CLI records local intent and observations; it does not control the native harness. See `engineering/runbooks/local-agent-watchdog.md` in the source repository for the complete recovery sequence.

## Policy still enforced when healthy

Secrets (`.env`, keys), destructive shell (`rm -rf /`, `git push --force`), Bitrix core paths, and real side-effect invocations (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`) remain blocked by `policy.py` when the stack imports cleanly. Bare words in file paths or `echo`/`cat` arguments are not side-effects.
