# Architecture — Repair stale-route lockout and policy path matching

## Decisions

1. **Invocation tokens, not bare words.** Split the Bash string on `&&` / `||` / `;` / `|` / newlines, drop comments and leading `NAME=value` / `sudo` wrappers, then match argv prefixes: `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`.
2. **Follow-up-only reuse.** `should_reuse_active_route(prompt)` is true only when `FOLLOW_UP_RE` matches the whole prompt. Stop using `is_development_prompt` for rematch.
3. **Child briefs do not rematch.** If the UserPromptSubmit payload has a child agent id/type, or the prompt starts with `You are <name>`, keep the existing route. Observed live: architect brief overwrote `757a43330038`.
4. **Canonical hooks only under `.grok/hooks/`.** Path-qualify `adaptive.json`. Delete untracked root copies so Grok does not import root `_lib.py` (`STACK` would be the parent of the repo).
5. **Stop is warn-only.** v2.0.4 changelog is source of truth. Rewrite the stale hard-block test; do not restore `decision=block`.
6. **Single writer in this session.** Dispatching `general_implementer` would fire UserPromptSubmit on a keyword-rich brief and replace the route (already happened to analysis agents). Parent performs the write-owner work.

## Data / control flow

```
UserPromptSubmit
  → child payload? reuse
  → should_reuse_active_route? reuse
  → else build_route + set_active_route

PreToolUse / Bash
  → DESTRUCTIVE_COMMANDS (unchanged)
  → production invocation prefixes + approval
  → secret / protected / MCP / write-owner (unchanged)
```

## What does not change

`stop_gate.py`, `DESTRUCTIVE_COMMANDS`, secret/protected globs, MCP `SIDE_EFFECT_TOOL`, `grok_approve.py` scopes, HIGH_RISK list, VERSION.
