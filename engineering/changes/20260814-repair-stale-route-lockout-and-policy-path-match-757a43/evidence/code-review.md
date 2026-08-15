# Code review — 757a43330038

Reviewer: `code_reviewer` (read-only). Write owner is `general_implementer` (parent performed the write). This review does not approve its own implementation.

Change: `20260814-repair-stale-route-lockout-and-policy-path-match-757a43`
Tree: working copy on `main` at `eaf0a0026734cded4310ffed2725c5ebe6a48669` (route `base_commit`; HEAD has not advanced). Reviewed files are the uncommitted working tree.

## What I inspected

### Contracts

- `.grok-stack/runtime/active-route.json`
- `engineering/changes/20260814-repair-stale-route-lockout-and-policy-path-match-757a43/{brief,requirements,architecture,tasks,test-plan,rollback,release}.md`
- `engineering/changes/20260814-repair-stale-route-lockout-and-policy-path-match-757a43/evidence/{implementation,analysis-architect,analysis-repo_explorer}.md`

### Implementation (full files, not summaries)

- `.grok-stack/adaptive_grok/policy.py` — `DESTRUCTIVE_COMMANDS`, `PRODUCTION_INVOCATIONS`, `_command_chunks`, `_leading_argv`, `is_production_invocation`, `evaluate_pre_tool`, `SIDE_EFFECT_TOOL`, secret/protected globs
- `.grok-stack/adaptive_grok/router.py` — `INTENT_KEYWORDS['bugfix']`, `FOLLOW_UP_RE`, `should_reuse_active_route`, `is_development_prompt`, `build_route`
- `.grok-stack/adaptive_grok/state.py` — `has_valid_approval` (production / protected-path / `*`)
- `.grok-stack/config/policy.json` — protected + secret globs
- `.grok/hooks/_lib.py` — `STACK` path, `is_child_payload`
- `.grok/hooks/user_prompt_submit.py` — rematch predicate
- `.grok/hooks/{pre_tool_use,stop_gate,session_start,post_tool_use,subagent_start,session_end}.py`
- `.grok/hooks/adaptive.json`, `.grok/hooks.json`, `.grok/hooks/README.md`, `.grok/config.toml`
- `scripts/grok_approve.py` (scopes unchanged)
- `CHANGELOG.md` 2.0.4, `README.md` Hooks section, `VERSION`

### Tests

- `tests/test_policy.py`
- `tests/test_repo_router.py`
- `tests/test_hooks.py`
- `tests/test_structure.py`
- `tests/_support.py` (`run_hook` still executes `root / '.grok/hooks' / name`)

### Surrounding / absence checks

- Workspace-root hook copies (`_lib.py`, `user_prompt_submit.py`, `pre_tool_use.py`, `stop_gate.py`, `session_start.py`) — **absent**
- `.grok/hooks.disabled/` and `.grok/hooks.json.off` — **absent**
- Live hooks present under `.grok/hooks/`
- Agent briefs (`.grok/agents/architect.toml`, `code_reviewer.toml`) start with `You are the \`…\`` — matches `_CHILD_BRIEF`

### Commands / lookups

- Read `.git/HEAD`, `.git/refs/heads/main`, `.git/logs/HEAD`, `.git/COMMIT_EDITMSG` (HEAD == `eaf0a00`; no new commit)
- Grep: `PRODUCTION_COMMANDS` (gone from `*.py`), `is_development_prompt` (tests only; hook no longer uses it for rematch), `decision.*block` (only the new Stop **non**-block assertion)
- Existence probes for stray root hooks and `hooks.disabled`
- Did **not** execute `git diff` or `python3 -m unittest` in this process (no shell in the reviewer tool set). Implementation report claims 95 tests OK; `test_reviewer` should confirm execution.

## Acceptance vs code

| # | Criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Path / echo / cat / `grok_approve.py production` is not a side-effect | **Met** | `is_production_invocation` compares leading argv prefixes only. `ls …/release.md`, `echo production deploy release publish`, `cat …/release.md`, `python3 scripts/grok_approve.py production --reason "ship"` cannot match `('git','push')` etc. Tests: `test_path_text_is_not_a_side_effect`, `test_echo_and_cat_arguments_are_not_side_effects`, `test_approve_script_is_not_blocked_by_scope_argument`. |
| 2 | Real invocations stay gated | **Met** | Prefixes: `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`. Deny without approval; allow after `add_approval(..., 'production')`. Tests: `test_real_side_effect_invocations_still_require_approval`, `test_approval_lifts_real_side_effect_invocations`. |
| 3 | `cd … && git push` still denied | **Met** | `_COMMAND_SPLIT` splits `&&` / `\|\|` / `;` / `\|` / newlines; second chunk is `git push origin feature`. Test: `test_chained_push_still_requires_approval`. |
| 4 | Follow-up-only reuse; `"repair yourself"` → bugfix / `general_implementer` | **Met** | `'repair'` in `INTENT_KEYWORDS['bugfix']`. `should_reuse_active_route` is `FOLLOW_UP_RE` only. Hook rematches unless child or follow-up. Tests: `test_repair_yourself_is_bugfix_with_generic_write_owner`, `test_reuse_active_route_only_for_followups`, `test_repair_yourself_rematches_leftover_route`, `test_non_keyword_request_rematches_leftover_route`, tightened `test_followup_reuses_active_route` (`route_id` kept). |
| 5 | Child UserPromptSubmit does not replace parent route | **Met** | `is_child_payload`: top-level `agent_id` / `agentId` / `subagent_*` / `agent_type` **or** prompt `^\s*You are \w+`. Hook: `existing and (is_child_payload or should_reuse_active_route)`. Test: `test_child_agent_brief_does_not_replace_parent_route`. |
| 6 | `adaptive.json` path-qualified | **Met** | Every command is `python3 .grok/hooks/…`. Test: `test_adaptive_hooks_are_path_qualified`. |
| 7 | Stop remains warn-only | **Met** | `stop_gate.py` still emits `systemMessage` only; no `decision`. Test rewritten to `test_stop_warns_without_evidence` (`decision` ≠ `block`). README Hooks sentence now says warning, not hard block. |
| 8 | Secret / Bitrix / destructive / MCP fail-closed | **Met** | `DESTRUCTIVE_COMMANDS`, `DEFAULT_SECRET_READ`, `bitrix/**`, `SIDE_EFFECT_TOOL` unchanged and still evaluated. Existing tests remain: `test_blocks_destructive_git`, `test_blocks_secret_read`, `test_blocks_bitrix_core_edit`, `test_blocks_mcp_write_without_approval`. Destructive is checked **before** production invocation, so `git push --force` stays unconditional. |
| 9 | Hooks live under `.grok/hooks/` | **Met** | Canonical scripts present. Root copies and `hooks.disabled` absent. Test: `test_workspace_root_does_not_host_hook_scripts`. `.grok/hooks.json` restored with `command` + `commandWindows`. |

`PRODUCTION_COMMANDS` bare-word regexes are gone from Python. Rematch no longer calls `is_development_prompt`.

## Findings

No blocking defects. The matcher, rematch predicate, child skip, hook layout, and Stop contract match the change package.

### Low — child-skip regex is broader than agent names

- **File:** `.grok/hooks/_lib.py` (`_CHILD_BRIEF`)
- **Evidence:** `r'^\s*You are \w+'` matches any leading `You are <word>`, including user text such as `You are stuck, repair yourself`. Architecture explicitly chose this heuristic (and agent TOMLs start `You are the \`architect\`` / `You are the \`code_reviewer\``), so this is within design. A user sentence that starts with `You are` will keep a leftover route.
- **Not a fail:** contract is satisfied; isolate in a later change if user prompts need rematch in that shape.

### Low — child detectors are only tested together

- **File:** `tests/test_hooks.py` `test_child_agent_brief_does_not_replace_parent_route`
- **Evidence:** the case sends `agent_id`, `agent_type`, **and** a `You are architect.` prompt. Either detector alone would pass. A live child brief that has neither top-level id/type nor a leading `You are` would still rematch (the original overwrite shape, if Grok wraps the brief).
- **Not a fail:** product code implements both gates the architecture named.

### Info — README H1 still says v2.0.3

- **File:** `README.md` line 1 vs `VERSION` `2.0.4`
- **Evidence:** Hooks paragraph was updated as required; title was out of scope. Does not affect behavior.

## Residual risk

- Wrapped shells remain unmatched, as accepted: `bash -lc 'git push'`, `sh -c`, `python -c`, `$(git push)`, `xargs git push`.
- Leading-argv is whitespace split, not a shell parse. Misses include `/usr/bin/git push`, `git --no-pager push`, `sudo -u user git push` (wrapper flags left in argv), `nice -n 10 git push`, `docker compose push`, `pnpm publish`. Same class as the architecture residual; do not add a parser in a follow-up without a new change.
- `#` comment strip is naive (`chunk.split('#', 1)`). Does not unblock the listed invocations; can only cause a miss if a production prefix is hidden behind a `#` in the same token stream.
- Follow-up tokens (`делай`, `continue`, `yes`) still attach to a leftover high-risk route. Intended.
- `'repair'` is still a padded substring (`_score`). `irreparable` can classify as bugfix. Same class as existing `'fix'`.
- If a child UserPromptSubmit fires with **no** existing parent route, the hook still `build_route`s from the child brief. Typical parent-first order avoids this.
- PreToolUse / Stop stay fail-open on import/exception. `user_prompt_submit.py` still has no fail-open wrapper (pre-existing). A broken rematch import can leave a leftover route in place.
- This reviewer did not re-run the unit suite. Treat execution evidence as belonging to `test_reviewer`.

## Safety

- No `.env` / credential reads in the inspected change.
- `grok_approve.py` scopes unchanged (`production`, `external-write`, `protected-path`, `*`).
- `stop_gate.py` was not restored to `decision=block`.
- Write-owner / allowed-agent / MCP gates untouched.
- No push, merge, tag, or deploy in this review.

## Recommendation

**PASS**

The working tree implements the nine acceptance criteria with fail-closed gates preserved. Residual misses are the ones the architecture explicitly accepted. No application-code change is required from this review.
