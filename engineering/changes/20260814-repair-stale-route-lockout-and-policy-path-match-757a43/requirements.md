# Requirements — Repair stale-route lockout and policy path matching

## Acceptance criteria

- [x] Given a Bash command whose only match is a path or argument token such as `…-publish-…-github-…/release.md`, when PreToolUse runs, then the command is allowed
- [x] Given `python3 scripts/grok_approve.py production --reason "ship"`, when PreToolUse runs, then the command is allowed without a prior approval
- [x] Given `git push`, `gh pr merge`, `docker push`, `npm publish`, or `gh release create` without approval, when PreToolUse runs, then the command is denied
- [x] Given those same invocations after a valid `production` approval, when PreToolUse runs, then they are allowed
- [x] Given `cd dist && git push origin feature` without approval, when PreToolUse runs, then the command is denied
- [x] Given leftover route + prompt `"repair yourself"`, when UserPromptSubmit runs, then a new route is stored with `intent=bugfix` and `write_agent=general_implementer`
- [x] Given leftover route + a non-follow-up with no intent keywords (`please inspect hook policy matching`), when UserPromptSubmit runs, then the stored `route_id` changes
- [x] Given leftover route + `"делай"` / `"continue"`, when UserPromptSubmit runs, then the same `route_id` is kept
- [x] Given an active parent route + a child-agent UserPromptSubmit payload (`agent_id` / `You are …` brief), when the hook runs, then the parent `route_id` is unchanged
- [x] Given missing/stale evidence, when Stop runs, then stdout has a non-blocking `systemMessage` and no `decision=block`
- [x] Given `.grok/hooks/adaptive.json`, when structure tests run, then every command is path-qualified under `.grok/hooks/`
- [x] Given the workspace root, when structure tests run, then hook scripts and `_lib.py` are absent there

## Failure and edge cases

- `git push --force` remains unconditionally destructive
- Wrapped shells (`bash -lc 'git push'`) are an accepted residual miss
- Follow-up tokens still attach to a leftover high-risk route (intended)

## Non-functional requirements

- Security: do not weaken secret-read, Bitrix core, destructive, or MCP write gates
- Reliability: hooks stay fail-open on import/exception
- Performance: matcher is string/token only; no shell parse
- Observability: deny reasons still name the approval command
