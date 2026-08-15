# Analysis — architect

Change: `20260814-repair-stale-route-lockout-and-policy-path-match-757a43`
Route (intended): `757a43330038` · write owner: `general_implementer`
Risk: medium · no new services or dependencies

This is the smallest coherent vertical fix for three already-shipped defects. Do not restore a hard Stop block. Do not treat this as a release or packaging change.

## Problem (observed)

### 1. PreToolUse treats path/argument text as a production side-effect

`.grok-stack/adaptive_grok/policy.py` `PRODUCTION_COMMANDS` is:

```python
r'\bprod(?:uction)?\b', r'\bdeploy\b', r'\brelease\b', r'\bpublish\b',
r'\bgit\s+push\b', r'\bgh\s+pr\s+merge\b', r'\bdocker\s+push\b',
```

`evaluate_pre_tool` runs `re.search` over the entire Bash `command` string. Any path or argument that contains those bare words is denied unless a `production` approval exists.

This is a live lockout, previously recorded in `engineering/changes/20260814-рабочий-релиз-v2-0-0-пакеты-и-выкат-e86e93/evidence/analysis-repo_explorer.md`: agents were denied ordinary file tools because `release.md` matches `\brelease\b`.

Same false positives today:

| Command | Current | Required |
| --- | --- | --- |
| `ls engineering/changes/…-github-release-…/release.md` | deny | allow |
| `echo production deploy release publish` | deny | allow |
| `cat engineering/changes/…/release.md` | deny | allow |
| `python3 scripts/grok_approve.py production --reason "…"` | deny | allow (this script exists to satisfy the same policy) |
| `git push origin feature` | deny without approval | keep deny |
| `gh pr merge 12` | deny without approval | keep deny |
| `docker push img:tag` | deny without approval | keep deny |
| `npm publish` | deny only because `\bpublish\b` | keep deny, but as a real invocation |
| `gh release create vX` | deny only because `\brelease\b` | keep deny, but as a real invocation |

After bare-word patterns are removed, `npm publish` and `gh release create` must be added as explicit invocations or they silently become unguarded.

### 2. Leftover routes stick unless the new prompt looks like a “development” phrase

`.grok/hooks/user_prompt_submit.py` reuses the active route when `not is_development_prompt(prompt)`:

```python
if existing and prompt and not is_development_prompt(prompt, detect_repo(root)):
    context = route_context(existing)  # reuse leftover
```

`is_development_prompt` is False for:

- short confirmations (`FOLLOW_UP_RE`: `делай`, `continue`, `yes`, `ок`, …) — correct
- any other prompt that lacks `INTENT_KEYWORDS` and lacks long domain-keyword text — incorrect

`"repair yourself"` has no current intent/domain keyword, so a leftover high-risk route is reused. Adding `"repair"` to bugfix keywords fixes that one phrase and is **necessary** so rematch classifies it as `bugfix` + `general_implementer`. It is **not sufficient**: `"please inspect hook policy matching"` or `"look at the stop tests"` would still reuse the leftover route.

Reuse must be follow-up-only. Any other new user request rematches.

This workspace already shows the lockout shape: durable change `757a43330038` is medium / `general_implementer`, while `.grok-stack/runtime/active-route.json` is leftover `6e532e7417ef` (high-risk, Bitrix write owner, production gates) because a later prompt was classified independently. Repair prompts must not stay glued to that leftover.

### 3. Stop-hook tests still expect the pre-2.0.4 hard block

`CHANGELOG.md` 2.0.4 and `.grok/hooks/stop_gate.py` are fail-open / warn-only:

- missing or stale evidence → emit `systemMessage` only, **no** `decision: block`
- missing route or empty `required_evidence` → `{}`
- exceptions → `{}`

`tests/test_hooks.py::test_stop_blocks_without_evidence` still asserts `data['decision'] == 'block'` and reason `Missing/stale evidence`. That test is stale. **Do not restore the hard block** to make it pass.

`README.md` Hooks section still says Stop is blocked until receipts exist. Align that sentence with 2.0.4; do not change hook behavior.

## Proposed behavior

### A. Production side-effects are command invocations, not substrings

Keep fail-closed for secrets, Bitrix core, destructive git, and unapproved **real** side-effect commands.

Replace bare-word `PRODUCTION_COMMANDS` with an invocation matcher inside `evaluate_pre_tool` (same file, no new module):

1. Split the Bash string on `&&`, `||`, `;`, `|`, and newlines.
2. For each chunk, drop a trailing `#` comment and leading `NAME=value` assignments.
3. Drop a single leading wrapper token: `sudo`, `command`, `time`, `nohup`.
4. Tokenize on whitespace; compare the leading tokens case-insensitively.

Block (unless `has_valid_approval(..., 'production')`) only these invocations:

| argv prefix | Example |
| --- | --- |
| `git push` | `git push origin feature` |
| `gh pr merge` | `gh pr merge 12 --merge` |
| `docker push` | `docker push img:tag` |
| `npm publish` | `npm publish --access public` |
| `gh release create` | `gh release create v2.0.4` |

Do **not** inspect arguments after those prefixes. `echo`, `cat`, `ls`, `python3 scripts/grok_approve.py …` therefore cannot trip the gate.

Keep `DESTRUCTIVE_COMMANDS` as they are (already command-shaped, no approval override). Check them first so `git push --force` stays unconditionally blocked.

Do not add a shell parser, do not recurse into `bash -lc '…'` / `sh -c '…'` strings, and do not move the list into `policy.json`.

### B. Rematch every non-follow-up; classify “repair” as bugfix

In `router.py`:

1. Add `'repair'` to `INTENT_KEYWORDS['bugfix']`.
2. Export `should_reuse_active_route(prompt) -> bool` that is True **only** when `FOLLOW_UP_RE` matches the whole prompt.

In both hook copies of `user_prompt_submit.py` (runtime source of truth is `.grok/hooks/`; root-level clone is packaged and must stay identical):

```python
if existing and prompt and should_reuse_active_route(prompt):
    context = route_context(existing)
else:
    route = build_route(root, prompt or 'development task', session_id(payload))
    set_active_route(root, route.to_dict())
    context = route_context(route)
```

Stop using `is_development_prompt` for rematch. Leave that helper in place for existing unit tests; do not make rematch depend on intent/domain keyword hits.

Expected route for `"repair yourself"` on this generic repo: `intent=bugfix`, `domains=['generic']`, `risk=low`, `complexity=micro`, `write_agent='general_implementer'`. No Bitrix/security/release reviewers.

`"делай"` / `"continue"` / `"yes"` still reuse the leftover route (including a leftover high-risk one). That is the follow-up contract.

### C. Stop tests match the 2.0.4 contract

Do not edit `stop_gate.py`. Rewrite the stale test.

| Situation | Hook stdout |
| --- | --- |
| Active route, missing/stale evidence | `{ "systemMessage": "Adaptive note (non-blocking): missing/stale evidence: …" }` and **no** `decision` |
| Active route, current receipts | `{}` and route `status=completed` (already tested) |
| No route / no `required_evidence` | `{}` |
| Import/exception | `{}` (already implemented; no new test required) |

## Files to change

| File | Change |
| --- | --- |
| `.grok-stack/adaptive_grok/policy.py` | Replace bare-word `PRODUCTION_COMMANDS` with the invocation matcher above. Keep `DESTRUCTIVE_COMMANDS`, secret-read, protected-path, MCP, and write-owner gates. |
| `.grok-stack/adaptive_grok/router.py` | Add `'repair'` to bugfix keywords. Add `should_reuse_active_route`. |
| `.grok/hooks/user_prompt_submit.py` | Reuse leftover route only via `should_reuse_active_route`. |
| `user_prompt_submit.py` (repo root clone) | Same one-line rematch change so the packaged duplicate does not drift. |
| `tests/test_policy.py` | New allow/deny cases listed below. Keep existing secret/Bitrix/destructive/MCP tests. |
| `tests/test_repo_router.py` | Repair intent + rematch helper tests. |
| `tests/test_hooks.py` | Rematch hook tests. Replace `test_stop_blocks_without_evidence` with warn-only assertions. |
| `CHANGELOG.md` | One patch bullet under the current unpublished 2.0.4 section (VERSION is already `2.0.4`, packages stop at 2.0.3). Do not invent a new major. |
| `README.md` | Fix the one Hooks sentence that still claims Stop blocks. Optional one-liner that production policy matches invocations, not path words. |
| `.grok/hooks/README.md` | Optional: note that bare words in paths/args are not production side-effects. |

## Test cases that must fail first

Add these against the current tree **before** policy/router/hook edits. They must fail now and pass after the fix.

### Policy (`tests/test_policy.py`) — fail on current matcher

1. **Path text is not a side-effect.** `Bash` `ls engineering/changes/20260814-publish-v2-0-3-github-release-6d15cb/release.md` → allow.
2. **echo/cat arguments are not a side-effect.** `echo production deploy release publish` → allow; `cat engineering/changes/demo/release.md` → allow.
3. **Approve script is not blocked by its own scope argument.** `python3 scripts/grok_approve.py production --reason "ship"` → allow.
4. **Real side-effects still require approval.** Each of `git push origin feature`, `gh pr merge 12`, `docker push img:tag`, `npm publish`, `gh release create v2.0.4` → deny, reason mentions approval.
5. **Chained invocation still counts.** `cd dist && git push origin feature` → deny without approval.
6. **Approval still lifts the real commands.** After `add_approval(..., 'production', …)`, the five commands in (4) allow.
7. **Fail-closed unchanged (must stay green, not rewritten):** `git reset --hard`, `git push --force`, Read of `config/.env`, Write of `bitrix/modules/…`, MCP `mcp__github__create_issue` without `external-write`.

### Rematch (`tests/test_repo_router.py` + `tests/test_hooks.py`) — fail on current reuse rule

8. `build_route(..., "repair yourself")` → `intent == 'bugfix'` and `write_agent == 'general_implementer'`.
9. `should_reuse_active_route("repair yourself")` is False; `should_reuse_active_route("please inspect hook policy matching")` is False; `should_reuse_active_route("делай")` and `should_reuse_active_route("continue")` are True.
10. Hook: seed a leftover high-risk route (`write_agent='bitrix_implementer'`, `risk='high'`, known `route_id`). Submit `"repair yourself"` → persisted `route_id` changes, intent bugfix, write owner `general_implementer`.
11. Hook: same leftover, submit `"please inspect hook policy matching"` → new `route_id` (proves keyword add is not the only rematch path).
12. Hook: same leftover, submit `"делай"` → **same** leftover `route_id` (existing follow-up contract).

### Stop (`tests/test_hooks.py`) — align to 2.0.4; do not TDD a block back in

13. Replace `test_stop_blocks_without_evidence` with `test_stop_warns_without_evidence`:
    - `decision` is absent / not `'block'`
    - `systemMessage` contains `missing/stale evidence` (case-insensitive)
    - hook exit 0
14. Keep `test_stop_allows_current_evidence`.
15. Optional characterization: no active route → `{}`.

Cases 13–15 should **pass immediately** against current `stop_gate.py`. If they fail, the implementation drifted from the 2.0.4 changelog; fix the test to the changelog, not the hook toward a hard block.

## What NOT to change

- `.grok/hooks/stop_gate.py` and root `stop_gate.py` — already the intended contract.
- `.grok/hooks/pre_tool_use.py` fail-open wrapper — keep allow-on-exception.
- `DESTRUCTIVE_COMMANDS`, `secret_read_paths`, `protected_paths`, Bitrix core writes, MCP `SIDE_EFFECT_TOOL`.
- `scripts/grok_approve.py` behavior or scopes (`production`, `external-write`, `protected-path`, `*`).
- Write-owner selection rules, HIGH_RISK/MEDIUM_RISK lists, domain keyword lists (except adding `'repair'`).
- `FOLLOW_UP_RE` vocabulary, unless a test proves a needed alias. Do not expand it to long sentences.
- New config keys, new services, new dependencies, new hook events.
- Recursing into `bash -lc` / `python -c` payloads (accepted residual: wrapped shells can still hide a push).
- Runtime leftovers under `.grok-stack/runtime/` — rematch on the next real user prompt is the fix; do not hand-edit runtime as product.
- Packaging, tags, GitHub releases, VERSION bump, installer, quality profiles, agent TOMLs, Bitrix examples.
- Do not add `"repair"` and leave rematch keyed on `is_development_prompt` keyword hits.

## Decisions (bounded rulings)

1. **Invocation tokens over regex-anywhere.** Smallest way to keep `git push` / `gh pr merge` / `docker push` / `npm publish` / `gh release create` gated while letting path and echo/cat text through. Exempting named binaries (`echo`/`cat`) alone is not enough: `ls …/release.md` would still match `\brelease\b`.
2. **Follow-up-only reuse.** Rematch is a property of prompt shape, not of whether the text looks “technical”. Keyword expansion cannot enumerate every non-follow-up.
3. **Stop is test-only.** v2.0.4 changelog is source of truth. A failing hard-block test is a stale test, not a product regression to restore.
4. **HIGH_RISK substring matching on long instruction text is out of scope.** A new prompt that *mentions* `production` / `deploy` / `secret` as constraints can still classify high-risk (that is how leftover `6e532e7417ef` was born). Fixing that classifier is a separate change.

## Rollout

- Pure library + hook + test change. No migration, no feature flag, no schema bump.
- Next Grok process / next `UserPromptSubmit` picks up rematch. Next `PreToolUse` picks up invocation matching.
- Existing leftover `active-route.json` is overwritten automatically on the next non-follow-up user prompt. No operator action.
- Do not package, tag, merge, or publish as part of this change.

## Rollback

- Revert the files in “Files to change”. No data repair.
- Reverting policy restores the path-word lockout (known broken). Prefer forward-fix.
- Reverting rematch restores leftover-route stickiness.
- Reverting only the Stop test reintroduces a red suite against the 2.0.4 hook; leave the warn-only test in place even if policy/rematch is rolled back.
- Verification after rollback/forward-fix: `python3 -m unittest discover -s tests` and `python3 scripts/grok_doctor.py`.

## Residual risk

- `bash -lc 'git push origin main'` and `python -c "os.system('git push')"` will not match the invocation prefix. Accept for this patch; still fail-closed for direct commands and for `DESTRUCTIVE_COMMANDS`.
- Follow-up tokens (`yes`, `делай`) still attach to a leftover high-risk route. Intended.
- `'repair' in "irreparable"` can score as bugfix via the existing substring `_score`. Same class of issue as `'fix'`; do not invent a tokenizer here.
- Root hook clones vs `.grok/hooks/` can drift if only one rematch call site is updated.

## Implementation order for `general_implementer`

1. Land failing tests 1–12 (and the rewritten Stop test 13).
2. Implement policy invocation matching.
3. Implement `repair` keyword + `should_reuse_active_route` + both `user_prompt_submit.py` call sites.
4. Confirm fail-closed tests still pass.
5. Docs/changelog last. Do not touch `stop_gate.py`.
