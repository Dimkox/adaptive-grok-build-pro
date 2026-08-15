# Analysis — repo_explorer

Route (change package): `757a43330038`
Live leftover active route: `6e532e7417ef` (high-risk, `write_agent=bitrix_implementer`)
Question: What is the current implementation and test coverage for (1) PreToolUse production-command matching, (2) UserPromptSubmit rematch via `is_development_prompt`, and (3) Stop hook vs `test_stop_blocks_without_evidence`?

Read-only inspection of the live tree. No application code was edited. Parent facts were verified against sources and are not contradicted.

## Verdict

Three independent defects, all present now:

1. `PRODUCTION_COMMANDS` is a list of bare word-boundary regexes searched against the **entire** Bash command string. Path/argument text such as `...-publish-...-github-...` or `scripts/grok_approve.py production` is treated as a side effect.
2. `is_development_prompt("repair yourself")` is `False` because `"repair"` is not in `INTENT_KEYWORDS` and is not a domain keyword. Any leftover route is reused. The inverse of `is_development_prompt` is much larger than “follow-up”.
3. `stop_gate.py` is fail-open / warn-only since v2.0.4 (`VERSION` = `2.0.4`). `test_stop_blocks_without_evidence` still expects `decision=block` and will `KeyError`. 82 collected tests; this is the one error.

Canonical hook implementations live under `.grok/hooks/`. Identical-looking copies also sit at the repository root and are what `.grok/hooks/adaptive.json` would execute if Grok’s cwd is the workspace root.

---

## 1. PreToolUse production-command matching

### Call chain

| Layer | Path | Role |
| --- | --- | --- |
| Grok discovery | `.grok/hooks/adaptive.json` lines 17–25 | `python3 pre_tool_use.py` (no directory prefix) |
| Doctor/structure contract | `.grok/hooks.json` lines 27–37 | `python3 .grok/hooks/pre_tool_use.py` |
| Hook wrapper | `.grok/hooks/pre_tool_use.py` | Fail-open; calls `evaluate_pre_tool` |
| Policy | `.grok-stack/adaptive_grok/policy.py` | Real deny/allow |
| Config | `.grok-stack/config/policy.json` | Protected/secret globs only; **does not** override production patterns |

`tests/_support.py:run_hook` (lines 49–63) always executes `root / '.grok/hooks' / name`. Unit tests never exercise the root copies or `adaptive.json`’s bare filenames.

### Policy implementation (exact)

`.grok-stack/adaptive_grok/policy.py` lines 37–40 define:

```python
PRODUCTION_COMMANDS = [
    r'\bprod(?:uction)?\b', r'\bdeploy\b', r'\brelease\b', r'\bpublish\b',
    r'\bgit\s+push\b', r'\bgh\s+pr\s+merge\b', r'\bdocker\s+push\b',
]
```

Applied at lines 100–107:

```python
if tool == 'Bash':
    command = str(tool_input.get('command', '')) if isinstance(tool_input, dict) else str(tool_input)
    for pattern in config.get('destructive_command_patterns', DESTRUCTIVE_COMMANDS):
        ...
    if any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in PRODUCTION_COMMANDS):
        if not has_valid_approval(root, 'production'):
            return False, 'Production/publish side effect requires explicit approval: python scripts/grok_approve.py production --reason "..."'
```

Facts confirmed:

- Matching is case-insensitive (`re.IGNORECASE`).
- The subject is the **whole** command string, not argv[0] / the first token.
- `PRODUCTION_COMMANDS` is hardcoded. `policy.json` can override `destructive_command_patterns` (line 102) but there is no `production_command_patterns` config key and none is read.
- `\b` still matches hyphen-delimited path segments: `20260814-publish-v2-0-3-github-release-6d15cb` matches both `\bpublish\b` and `\brelease\b`. Same for `release.md`.
- `scripts/grok_approve.py production --reason "..."` matches `\bprod(?:uction)?\b`. The deny message tells the agent to run the same command the policy then denies.
- `\bprod(?:uction)?\b` also matches a standalone `prod` (e.g. `engineering/prod/`). `product` / `publisher` / `released` / `deployed` do **not** match because the trailing word char defeats `\b`.

`DESTRUCTIVE_COMMANDS` (lines 24–36) is a separate fail-closed list (`git reset --hard`, `git push --force`, `terraform apply/destroy`, `rm -rf /`, etc.). That list is **not** the bug. Destructive matching is also whole-string, but its patterns are command-shaped.

`npm publish` and `gh release create` are gated only because of the bare `\bpublish\b` / `\brelease\b` tokens. There is no dedicated `npm publish` or `gh release create` pattern. `git push` / `gh pr merge` / `docker push` do have command-shaped patterns.

### Approval escape hatch

`scripts/grok_approve.py` lines 15–20: scope choices are `production`, `external-write`, `protected-path`, `*`. `has_valid_approval` (`.grok-stack/adaptive_grok/state.py` lines 157–177) accepts that scope or `*`.

The documented invocation cannot be issued through Bash PreToolUse without an **already-valid** production approval. That is the lockout.

### Wrapper fail-open (not the matching bug)

`.grok/hooks/pre_tool_use.py`:

- Lines 18–23: `_lib` import failure → `{"decision":"allow"}`.
- Lines 32–41: `adaptive_grok.policy` import failure → allow.
- Lines 67–75: any other exception → allow.
- Lines 47–66: successful `evaluate_pre_tool` still **denies** when policy returns `allowed=False`.

v2.0.4 fail-open does **not** weaken a healthy policy. Path-text denials still fire.

### Existing production tests (and the missing cases)

`tests/test_policy.py`:

| Test | Command | Expectation | Gap |
| --- | --- | --- | --- |
| `test_blocks_production_side_effect_without_approval` (28–32) | `git push origin feature` | deny, reason contains `approval` | Only the intended command-shaped case |
| `test_allows_production_side_effect_with_approval` (34–38) | same, after `add_approval(..., 'production')` | allow | Same |
| `test_allows_normal_test_command` (23–26) | `php -l local/test.php` | allow | No forbidden token |
| `test_blocks_destructive_git` (17–21) | `git reset --hard HEAD~1` | deny `destructive` | Different list |
| `test_pre_tool_hook_denies_destructive_command` (`test_hooks.py` 38–44) | `terraform destroy` | `permissionDecision=deny` | Destructive, not production |

**No current test covers:**

- Path containing `publish` / `release` / `production` / `deploy` / `prod` (`ls`/`cat`/`echo`/`python3` of a change-package path).
- `python3 scripts/grok_approve.py production --reason "..."` must be **allowed** without a prior approval (the approval tool itself).
- Bare words only in echo/cat arguments must be allowed.
- Real side effects that must **stay** denied without approval: `git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`.
- `git push --force` remains destructive (already covered) even if production matching is narrowed.

These are the tests that must fail first before a matcher rewrite.

Prior sighting of the same bug: `engineering/changes/20260814-рабочий-релиз-v2-0-0-пакеты-и-выкат-e86e93/evidence/analysis-repo_explorer.md` line 3 and `.../evidence/security-review.md` line 3 (`\brelease\b` in `release.md` denied tools).

---

## 2. UserPromptSubmit rematch

### Call chain

| Layer | Path | Role |
| --- | --- | --- |
| Grok discovery | `.grok/hooks/adaptive.json` lines 10–15 | `python3 user_prompt_submit.py` |
| Doctor/structure | `.grok/hooks.json` lines 15–25 | `python3 .grok/hooks/user_prompt_submit.py` |
| Hook | `.grok/hooks/user_prompt_submit.py` | Reuse vs `build_route` |
| Classifier | `.grok-stack/adaptive_grok/router.py` `is_development_prompt` | The rematch predicate |
| Persist | `.grok-stack/adaptive_grok/state.py` `set_active_route` | Writes `active-route.json` + `routes/<id>.json` |
| Session restore | `.grok/hooks/session_start.py` | Re-injects leftover route; does not rematch |

`routing.json` is documentation only (“Runtime defaults live in `adaptive_grok.router`”).

### Rematch predicate (exact)

`.grok/hooks/user_prompt_submit.py` lines 14–20:

```python
existing = get_active_route(root)
if existing and prompt and not is_development_prompt(prompt, detect_repo(root)):
    context = route_context(existing)
else:
    route = build_route(root, prompt or 'development task', session_id(payload))
    set_active_route(root, route.to_dict())
    context = route_context(route)
```

Reuse happens when **all** of: there is an active route, the prompt is non-empty, and `is_development_prompt` is false.

`is_development_prompt` (`.grok-stack/adaptive_grok/router.py` lines 163–171):

```python
def is_development_prompt(prompt: str, repo: RepoProfile) -> bool:
    if FOLLOW_UP_RE.match(prompt):
        return False
    scores = _score(prompt, INTENT_KEYWORDS)
    if scores:
        return True
    lowered = prompt.lower()
    technical = any(word in lowered for words in DOMAIN_KEYWORDS.values() for word in words)
    return technical and len(prompt.strip()) > 12
```

`FOLLOW_UP_RE` (lines 50–53) is an **entire-prompt** match for:
`да|нет|ок|окей|делай|продолжай|согласен|согласна|go|continue|yes|no|вариант [abcабв123]|[abcабв123]`.

`INTENT_KEYWORDS['bugfix']` (line 15):
`bug`, `fix`, `ошиб`, `баг`, `сломал`, `не работает`, `исправ`, `regression`, `exception`, `fatal`.

**`"repair"` is not in any intent or domain list.**

`_score` (lines 88–95) does padded substring match (`f' {text.lower()} '`). `'fix' in ' repair yourself '` is false. `"repair yourself"` is not a follow-up. Length is 15 but there is no domain keyword. Therefore `is_development_prompt("repair yourself")` is **False**. Parent fact confirmed.

There is no comparison of:

- new prompt vs `route['task']`
- `session_id` vs `route['session_id']`
- route `status` (`completed` vs `routed`)
- “this is a new request” beyond the keyword heuristic

`session_start.py` lines 14–16 always re-surfaces the leftover route.

### Live lockout in this workspace

| Artifact | route_id | risk / write owner | created_at |
| --- | --- | --- | --- |
| Change package `route.json` + `routes/757a43330038.json` | `757a43330038` | medium, `general_implementer` | `23:01:17` |
| Live `.grok-stack/runtime/active-route.json` | `6e532e7417ef` | high-risk, `bitrix_implementer` | `23:01:44` |

The later UserPromptSubmit classified the architect prompt as development (it contains `test`, `secret`/`secrets`, `bitrix`, and the high-risk tokens `production`, `deploy`, `secret`). That **overwrote** the intended change-package route. A subsequent `"repair yourself"` would **keep** `6e532e7417ef` and keep `bitrix_implementer` as the only write owner.

Adding `"repair"` to bugfix keywords would rematch `"repair yourself"` but would **not** rematch other new non-follow-up prompts that lack intent/domain keywords (`please continue the work`, `look at the hooks`, `help`, `go ahead and unstick this`). Those still reuse the leftover high-risk route.

Prompts that **do** rematch today (because they contain `fix` / `bug` / a domain word): `"Fix hook policy..."`, `"исправь ..."`. That is why this change’s original user prompt created `757a43330038`, and why a later keyword-rich sub-agent prompt replaced it.

### Existing rematch tests (and the missing cases)

`tests/test_hooks.py`:

| Test | What it actually asserts | Gap |
| --- | --- | --- |
| `test_user_prompt_submit_creates_route` (18–28) | Russian Bitrix bug prompt creates a route; write owner `bitrix_implementer`; context contains `ADAPTIVE GROK ROUTE` | Happy path only |
| `test_followup_reuses_active_route` (30–36) | After seeding a route, prompt `делай` still emits `ADAPTIVE GROK ROUTE` | **Does not** assert the same `route_id` was kept. A rematch that built a new route would still pass |

`tests/test_repo_router.py`:

| Test | What it asserts | Gap |
| --- | --- | --- |
| `test_short_followup_is_not_new_development_prompt` (111–113) | `is_development_prompt('делай')` is False | Only the known follow-up |
| All other router tests | `build_route` intent/owner/risk | Never call `is_development_prompt` |

**No current test covers:**

- `is_development_prompt("repair yourself")` is True (today it is False; this should fail first if rematch is the goal).
- Hook-level: leftover high-risk route + `"repair yourself"` → **new** `route_id`, not reuse.
- Hook-level: leftover route + a new non-follow-up with **no** intent/domain keywords still rematches (parent constraint: adding `repair` is necessary but not sufficient).
- Hook-level: leftover route + true follow-up (`делай` / `continue` / `yes`) **keeps** the same `route_id` (the existing follow-up test must be tightened to assert `route_id`).
- Hook-level: a genuinely new development prompt (`Fix hook policy...`) rematches even when a leftover route exists.
- No assertion that `session_id` change or `status=completed` forces rematch (design choice still open).

---

## 3. Stop hook vs `test_stop_blocks_without_evidence`

### Intended contract (v2.0.4)

`VERSION` is `2.0.4`.

`CHANGELOG.md` lines 3–10:

- `stop_gate.py`: missing/stale evidence → **warn only**, never block stop; missing route → allow.
- `pre_tool_use.py`: exception/import failure → allow.
- Policy still blocks destructive/secret paths when it runs successfully.

`.grok/hooks/README.md` lines 5–10: same contract. “Hard lockouts (exit 2 / infinite stop loops) are intentional bugs — fixed in 2.0.4.”

### Current implementation

`.grok/hooks/stop_gate.py`:

| Condition | Lines | Emitted payload |
| --- | --- | --- |
| `_lib` import failure | 13–17 | `{}` , exit 0 |
| stack import failure / any exception | 27–29, 47–48 | `{}` |
| no route or no `required_evidence` | 31–34 | `{}` |
| `validate_evidence` returns gaps | 36–42 | `{systemMessage: "Adaptive note (non-blocking): missing/stale evidence: ..."}` — **no `decision`** |
| evidence current | 44–46 | `reset_stop_attempt`; `update_route(status='completed')`; `{}` |

`increment_stop_attempt` (`state.py` 197–205) is **unused** by any current `.py` file. Only `reset_stop_attempt` remains, on the success path.

`validate_evidence` (`.grok-stack/adaptive_grok/receipts.py` 40–52) still computes gaps (`missing receipt` / `status!=pass` / fingerprint mismatch). Those gaps are now advisory text only.

### Stale test

`tests/test_hooks.py` lines 73–80:

```python
def test_stop_blocks_without_evidence(self) -> None:
    ...
    _, data, _ = run_hook(root, 'stop_gate.py', {'cwd': str(root), 'stop_hook_active': False})
    self.assertEqual(data['decision'], 'block')
    self.assertIn('Missing/stale evidence', data['reason'])
```

Against the v2.0.4 payload this is a **KeyError** on `data['decision']`, not an AssertionError. Parent fact confirmed.

Secondary string mismatch (if the test is only half-updated): expected `'Missing/stale evidence'` (capital M) is **not** a substring of `'Adaptive note (non-blocking): missing/stale evidence: ...'`.

`test_stop_allows_current_evidence` (82–92) still matches the success path (`data == {}`, route `status=completed`). Keep it.

### Docs still advertising the old hard block

`README.md` line 110: “block Stop until required receipts exist.” That is the pre-2.0.4 contract and will confuse reviewers if the test is “fixed” back to `decision=block`.

Older analysis (`.../bf62a5.../evidence/analysis-repo_explorer.md` line 49) also documents the hard-block payload. That document is historical, not the v2.0.4 contract.

### Tests that must change

| Test | Required new behavior |
| --- | --- |
| `tests/test_hooks.py::HookTests::test_stop_blocks_without_evidence` | Rename/rewrite: missing evidence → **no** `decision=block`; `systemMessage` is non-blocking and mentions missing/stale evidence (case-insensitive); hook exit 0 |
| `test_stop_allows_current_evidence` | Keep |
| New: missing route / empty `required_evidence` → `{}` | Not covered |
| New: do **not** restore `decision=block` | Changelog is the contract |

Collected test methods in `tests/test_*.py`: **82**. The Stop-hook KeyError is the only source-level contradiction found; the suite was not re-executed here (no shell; parent reported 82 tests / 1 error, and the code produces that error).

---

## Stray hook copies at repository root

Present next to `AGENTS.md` / `VERSION` (also `__pycache__/_lib.cpython-312.pyc`, so they have been imported):

- `_lib.py`
- `pre_tool_use.py`
- `user_prompt_submit.py`
- `stop_gate.py`
- `post_tool_use.py`
- `pre_compact.py`
- `session_start.py`
- `session_end.py`
- `subagent_start.py`
- `subagent_stop.py`

Compared files (`user_prompt_submit.py`, `stop_gate.py`, `pre_tool_use.py`, `post_tool_use.py`, `_lib.py`) are byte-level copies of `.grok/hooks/*`.

They are **not** in `.gitignore`. `adaptive_grok.manifest.included_files` would package them (only `.grok-stack/runtime/`, secrets, `__pycache__`, zips are excluded). They are not part of the designed layout (hooks belong under `.grok/hooks/`). They look untracked; `git status` was not run because PreToolUse currently treats many git/path strings as production.

Why they matter:

1. `.grok/hooks/adaptive.json` commands are **bare** (`python3 user_prompt_submit.py`, `python3 pre_tool_use.py`, `python3 stop_gate.py`). README says this file is what Grok discovers. If cwd is the workspace root, Python loads the **root** copies, not `.grok/hooks/`.
2. Root `_lib.py` lines 8–12 compute `REPO_CANDIDATE = HOOK_DIR.parents[1]`. For a file at repo root that is the **parent of the repo**, so `STACK` becomes `<parent>/.grok-stack`. Canonical `.grok/hooks/_lib.py` correctly lands on the repo root.
3. Root `user_prompt_submit.py` has **no** fail-open around the `_lib` / `adaptive_grok` import. A broken STACK path can crash rematch entirely, leaving the leftover route in place.
4. Root `pre_tool_use.py` / `stop_gate.py` do fail-open on import failure, so a broken root `_lib` would **allow every tool** and **never warn on Stop** even when `.grok/hooks/` is healthy.
5. `run_hook` / doctor / `hooks.json` all point at `.grok/hooks/`. Tests cannot see a root-copy regression.

These copies should be deleted (or never created) as part of unstick; they are not an alternative implementation.

---

## Impact surface (files to change later; not edited here)

| File | Why |
| --- | --- |
| `.grok-stack/adaptive_grok/policy.py` | Narrow `PRODUCTION_COMMANDS` so path/argument text is not a side effect; keep real push/merge/publish commands gated |
| `.grok-stack/adaptive_grok/router.py` | Rematch: `repair` is not enough; invert the “reuse leftover route” predicate |
| `.grok/hooks/user_prompt_submit.py` | Only if rematch policy needs hook-level session/status checks beyond `is_development_prompt` |
| `tests/test_policy.py` | New allow/deny cases listed in §1 |
| `tests/test_repo_router.py` | `repair yourself` + other non-follow-up rematch cases |
| `tests/test_hooks.py` | Tighten follow-up `route_id` assertion; leftover-route rematch; rewrite Stop test |
| `.grok/hooks/stop_gate.py` | **Do not** restore hard block |
| `README.md` line 110 | Still documents hard Stop block |
| Repo-root hook `*.py` + `_lib.py` | Stray; delete, do not “fix” in place |

Do **not** change: `DESTRUCTIVE_COMMANDS` fail-closed, secret-read globs, Bitrix `bitrix/**` write protection, MCP `SIDE_EFFECT_TOOL` + `external-write` approval, `test_stop_allows_current_evidence`, v2.0.4 fail-open wrappers.

---

## Residual questions

1. **Which hook file does this Grok session actually execute?** `adaptive.json` (bare names → root copies) vs `hooks.json` (path-qualified → `.grok/hooks/`). Both exist; tests only cover the latter.
2. **Who created the root copies, and should packaging/doctor fail if they reappear?** `included_files()` would ship them today.
3. **Rematch rule beyond keywords:** should any non-`FOLLOW_UP_RE` prompt replace the active route? Or only when `session_id` changes / route is `completed` / prompt similarity is low? Parent says adding `repair` is not sufficient; the smallest sufficient rule is still a design decision for architect.
4. **Should `python3 scripts/grok_approve.py <scope>` be an explicit allow-list**, or is “do not match bare `production` in arguments” enough?
5. **`npm publish` / `gh release create`:** today they are denied only via bare `\bpublish\b` / `\brelease\b`. After narrowing, they need command-shaped patterns or they will become unguarded.
6. **Suite was not re-run in this explorer process.** Code inspection matches the parent’s “82 tests, 1 KeyError”. Confirm after implementation with `python3 -m unittest discover -s tests` (avoid embedding `release`/`publish`/`production`/`deploy`/`git push` in ad-hoc Bash until the matcher is fixed).
7. **Live runtime is already on the wrong route** (`6e532e7417ef` vs change `757a43330038`). Even a correct rematch fix will not rewrite `active-route.json` until the next UserPromptSubmit that the new predicate treats as development.

---

## Source-of-truth check

- Change package `engineering/changes/20260814-repair-stale-route-lockout-and-policy-path-match-757a43/` is still a draft (`state.json` status `draft`; brief/requirements/tasks/test-plan are templates).
- Active change pointer: `.grok-stack/runtime/active-change.json` → this package.
- Parent facts (bare `PRODUCTION_COMMANDS`, `repair yourself` not a development prompt, Stop fail-open vs blocking test) are confirmed by the files cited above.
