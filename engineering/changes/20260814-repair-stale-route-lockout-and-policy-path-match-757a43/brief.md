# Repair stale-route lockout and policy path matching

Change ID: `20260814-repair-stale-route-lockout-and-policy-path-match-757a43`
Created: 2026-08-14T23:01:23+00:00
Risk: medium
Complexity: standard
Domains: generic

## Problem

The stack locks itself:

1. PreToolUse treats path and argument text as a side-effect (`\brelease\b`, `\bpublish\b`, `\bprod(?:uction)?\b` anywhere in the Bash string).
2. UserPromptSubmit reuses a leftover route unless the new prompt hits intent/domain keywords. `"repair yourself"` stays glued to the previous high-risk route.
3. Child-agent briefs are classified as new user tasks and overwrite the parent route (observed: architect brief replaced `757a43330038` with `6e532e7417ef`).
4. `test_stop_blocks_without_evidence` still expects the pre-2.0.4 hard Stop block.
5. `.grok/hooks/adaptive.json` uses bare script names, so Grok running from the workspace root loads untracked hook copies at the repo root (`_lib.py` then points `STACK` at the parent of the repo).

## Outcome

A user can say `repair yourself` (or any other non-follow-up request) and get a new route with a real write owner. Ordinary `ls`/`cat`/`echo` of change-package paths works. `scripts/grok_approve.py` can be invoked. Child-agent briefs do not replace the parent route. `python3 -m unittest discover -s tests` is green.

## Scope

### In scope

- Invocation-shaped side-effect matching in `policy.py`
- Follow-up-only route reuse; `"repair"` as a bugfix keyword
- Ignore child-agent UserPromptSubmit rematch
- Path-qualify `adaptive.json` commands; delete stray root hook copies
- Align Stop-hook tests and the README Stop sentence with the 2.0.4 warn-only contract

### Out of scope

- Restoring a hard Stop block
- Recursing into `bash -lc` / `python -c` payloads
- HIGH_RISK substring scoring on long instruction text
- Packaging, tags, VERSION bump, installer rewrite

## Constraints

- Backward compatibility: keep `git push` / `gh pr merge` / `docker push` / `npm publish` / `gh release create` gated
- Security: secrets, Bitrix core, destructive git, MCP writes stay fail-closed
- Operational: no new services or dependencies
