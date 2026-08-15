# Test review — 757a43330038

Reviewer: `test_reviewer` (read-only). No application code was edited.
Change: Repair stale-route lockout and policy path matching
Date: 2026-08-14

## What was inspected

Change package:

- `engineering/changes/20260814-repair-stale-route-lockout-and-policy-path-match-757a43/{requirements,test-plan,architecture,brief,tasks}.md`
- `engineering/changes/20260814-repair-stale-route-lockout-and-policy-path-match-757a43/evidence/implementation.md`

Tests (read in full):

- `tests/test_policy.py` — invocation matcher + fail-closed gates
- `tests/test_hooks.py` — rematch, child brief, Stop warn-only, PreToolUse wiring
- `tests/test_repo_router.py` — `repair` intent + `should_reuse_active_route`
- `tests/test_structure.py` — path-qualified `adaptive.json`, no root hook scripts
- `tests/_support.py` — `run_hook` still executes `.grok/hooks/<name>`
- Surrounding suite: `test_bitrix.py`, `test_change_receipts.py`, `test_installer.py`, `test_manifest_package.py`, `test_runtime_state.py`, `test_verification_doctor.py`

Implementation they claim to cover (read, not edited):

- `.grok-stack/adaptive_grok/policy.py` — `PRODUCTION_INVOCATIONS`, `_command_chunks`, `_leading_argv`, `is_production_invocation`, `evaluate_pre_tool` order (destructive first)
- `.grok-stack/adaptive_grok/router.py` — `INTENT_KEYWORDS['bugfix']` includes `repair`; `should_reuse_active_route` is `FOLLOW_UP_RE` only
- `.grok/hooks/_lib.py` — `is_child_payload` (top-level child keys **or** `^\s*You are \w+`)
- `.grok/hooks/user_prompt_submit.py` — reuse only for child payload or follow-up; otherwise `build_route` + `set_active_route`
- `.grok/hooks/pre_tool_use.py` — thin fail-open wrapper around `evaluate_pre_tool`
- `.grok/hooks/stop_gate.py` — `systemMessage` only; no `decision=block`
- `.grok/hooks/adaptive.json`, `.grok/hooks.json`

Harness check: `tests/_support.py` `run_hook` line 50 is `script = root / '.grok/hooks' / name`. Hook tests exercise the canonical tree, not leftover root copies.

Collected methods: **95** `def test_*` across `tests/test_*.py` (matches the implementation note). Old `test_stop_blocks_without_evidence` is gone.

## Coverage vs acceptance criteria

| # | Criterion | Test(s) | Verdict |
| --- | --- | --- | --- |
| 1 | Path and echo/cat argument text allowed | `PolicyTests.test_path_text_is_not_a_side_effect` (`ls …-publish-…-github-…/release.md`); `test_echo_and_cat_arguments_are_not_side_effects` | **Covered.** These are the cases the old `\brelease\b` / `\bpublish\b` / `\bprod(?:uction)?\b` substring matcher denied. They call real `evaluate_pre_tool`, not a stub. |
| 2 | `scripts/grok_approve.py` with a scope argument allowed | `test_approve_script_is_not_blocked_by_scope_argument` (`python3 scripts/grok_approve.py production --reason "ship"`) | **Covered.** Would fail if bare-word `production` matching returned. |
| 3 | Real invocations denied without approval, allowed with it; chained `cd … && git push` denied | `test_real_side_effect_invocations_still_require_approval` (`git push`, `gh pr merge`, `docker push`, `npm publish`, `gh release create`); `test_approval_lifts_real_side_effect_invocations`; `test_chained_push_still_requires_approval` | **Covered** for the listed argv prefixes and `&&`. Older `test_blocks_production_side_effect_without_approval` / `test_allows_production_side_effect_with_approval` still pin `git push origin feature`. |
| 4 | `build_route("repair yourself")` is bugfix / `general_implementer` | `RouterTests.test_repair_yourself_is_bugfix_with_generic_write_owner` | **Covered**, including `is_development_prompt(...) is True`. |
| 5 | `should_reuse_active_route` false for non-follow-ups, true for `делай` / `continue` | `test_reuse_active_route_only_for_followups` | **Covered** at unit level for all four strings. |
| 6 | Hook rematch: leftover + repair / non-keyword → new `route_id`; follow-up keeps it | `test_repair_yourself_rematches_leftover_route` (also asserts `intent=bugfix`, `write_agent=general_implementer`); `test_non_keyword_request_rematches_leftover_route`; `test_followup_reuses_active_route` (`делай`) | **Covered.** The non-keyword hook test is the one that actually proves rematch no longer depends on `is_development_prompt` (`repair` as a keyword would have rematched under the old rule; `please inspect hook policy matching` would not). `continue` is unit-only, not hook-level. |
| 7 | Child payload / `You are …` brief does not change `route_id` | `test_child_agent_brief_does_not_replace_parent_route` | **Covered for the combined production-like payload** (`agent_id` + `agent_type` + `You are architect.…`). The two `is_child_payload` branches are not isolated. |
| 8 | Stop warns and does not set `decision=block` | `test_stop_warns_without_evidence` (exit 0, `decision != block`, `systemMessage` contains `missing/stale evidence`); `test_stop_allows_current_evidence` | **Covered.** Old hard-block test name and assertion are gone. |
| 9 | `adaptive.json` commands path-qualified; root hook scripts absent | `test_adaptive_hooks_are_path_qualified`; `test_workspace_root_does_not_host_hook_scripts` | **Covered** for `adaptive.json` and the listed root script names. `hooks.json` is path-qualified in the tree but that file is not asserted by the new test (only `commandWindows` presence). |
| 10 | Fail-closed still exists | See below | **Mostly covered; `git push --force` has no test.** |

Fail-closed checklist:

| Gate | Test | Present? |
| --- | --- | --- |
| `git reset --hard` | `test_blocks_destructive_git` | Yes — denied, reason contains `destructive` |
| `git push --force` / `git push -f` | none | **No** |
| Read of `.env` | `test_blocks_secret_read` (`config/.env`) | Yes |
| Write of `bitrix/modules` | `test_blocks_bitrix_core_edit` (+ `test_blocks_any_bitrix_core_edit`) | Yes |
| MCP create without `external-write` | `test_blocks_mcp_write_without_approval` (`mcp__github__create_issue`) | Yes |

PreToolUse wiring: `test_pre_tool_hook_denies_destructive_command` still runs `pre_tool_use.py` via `run_hook` and asserts `permissionDecision == deny` for `terraform destroy`. Policy allow/deny cases for the new matcher go through `evaluate_pre_tool` directly; that matches the test plan (`test_policy.py`) and the hook is a thin wrapper.

Tests are not vacuous: allow-cases would fail if the old substring matcher returned; deny-cases would fail if the invocation prefix list were dropped; rematch cases would fail if leftover reuse still keyed off `is_development_prompt`.

## Findings

### 1. Medium — `git push --force` is not characterized against the new matcher

- **File:** `tests/test_policy.py` (missing); implementation `.grok-stack/adaptive_grok/policy.py` lines 24–33 and 128–135
- **Evidence:** `rg 'push --force|--force' tests` returns no policy assertions. `test_blocks_destructive_git` only uses `git reset --hard HEAD~1`. `test_approval_lifts_real_side_effect_invocations` lifts `git push origin feature` after a `production` approval.
- **Why it matters:** Architecture requires destructive checks first so `git push --force` stays unconditionally blocked. The new matcher also treats `('git', 'push')` as a production invocation. If someone reorders the two checks, or lets a production approval short-circuit the whole Bash branch, `git push --force` / `git push -f` would become allow-with-approval and no test would fail. Requirements list this as an explicit edge case (“remains unconditionally destructive”).
- **Not a false-positive:** `DESTRUCTIVE_COMMANDS` still contains `r'\bgit\s+push\s+[^\n]*(?:--force|-f\b)'` and it is still evaluated first. This is a missing lock, not a demonstrated product bug.

### 2. Low — child-payload OR-paths are not isolated

- **File:** `tests/test_hooks.py` `test_child_agent_brief_does_not_replace_parent_route`
- **Evidence:** The payload sets `agent_id`, `agent_type`, **and** prompt `You are architect. Fix hook policy matching file paths.`. `_lib.is_child_payload` is true if **either** a child key is set **or** `_CHILD_BRIEF` matches. Removing only the regex, or only the key check, would still pass this test.
- **Why it matters:** The live overwrite was a child brief. The combined payload is the realistic Grok shape and *does* lock the hook contract for that shape. Isolated tests for `is_child_payload({'agent_id': 'x'})` and for a `You are …` prompt with no child keys are absent.

### 3. Low — designed matcher wrappers are untested

- **File:** `tests/test_policy.py`; implementation `_leading_argv` / `_WRAPPERS`
- **Evidence:** Architecture says drop comments, `NAME=value`, and wrappers (`sudo`, `command`, `time`, `nohup`) before prefix match. No test for `sudo git push`, `FOO=1 git push`, or `echo x # git push` (the last should stay allowed).
- **Why it matters:** Forgetting the wrapper strip would allow `sudo git push` without approval. Comment-strip failure could re-introduce false denies on documented echo/cat text that happens to include `# git push`.

### 4. Low — `continue` and leftover+follow-up are only partially hooked

- **File:** `tests/test_hooks.py`, `tests/test_repo_router.py`
- **Evidence:** `should_reuse_active_route('continue')` is asserted. Hook reuse uses `делай` on a freshly built route, not the leftover high-risk fixture used by the rematch tests. Same `should_reuse_active_route` function, so the risk is small.

Non-findings (checked, not charged):

- Wrapped shells (`bash -lc 'git push'`, `python -c`) are an accepted residual in the test plan, requirements, and implementation notes. No shell parser was added. **Not a fail reason.**
- `run_hook` still points at `.grok/hooks/`.
- Stop test was rewritten; it would fail if `decision=block` returned.
- Fail-closed `.env`, Bitrix core, MCP create, and `git reset --hard` tests are intact.

## Residual risk

- **Documented, accepted:** `bash -lc` / `sh -c` / `python -c` can hide `git push`. Token matcher also misses `/usr/bin/git push` and `git -C dist push` (argv prefix is not `git push`). Same “no shell parse” bound.
- **Follow-up tokens still attach to a leftover high-risk route.** Intended; `делай` / `continue` reuse is the product rule.
- **Unlocked:** force-push vs production-approval interaction (Finding 1). Secret/Bitrix/MCP gates are independently locked.
- **Stop:** warn-only path is locked for *missing* receipts. Stale receipts go through the same `validate_evidence` used by `ReceiptTests`; Stop is not separately driven with a stale receipt.
- Policy allow-cases are not re-asserted through `pre_tool_use.py`. A hook regression that stopped calling `evaluate_pre_tool` on Bash would still be caught by `test_pre_tool_hook_denies_destructive_command` (deny path). An extra hook-side deny on path text would not.

## Recommendation

**PASS**

The new lockout/rematch/Stop/path-match behavior is characterized by tests that execute the real policy, router, and canonical hook scripts, and that would fail on a revert to substring matching or leftover-route reuse. Fail-closed gates for secrets, Bitrix core, MCP writes, and `git reset --hard` remain. The one required fail-closed case with no test is `git push --force` against the new `git push` production prefix; that is a Medium gap to close in a follow-up, not a demonstration that this suite is inadequate for the change that landed.

Do not treat this PASS as approval of the missing force-push characterization. A one-case addition belongs with the write owner:

```python
# missing today
evaluate_pre_tool(..., command='git push --force origin main')  # deny, even after add_approval(..., 'production')
evaluate_pre_tool(..., command='git push -f')                   # deny, destructive
```
