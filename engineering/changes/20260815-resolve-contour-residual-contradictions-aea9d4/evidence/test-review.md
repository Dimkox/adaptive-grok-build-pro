# Test review — `aea9d4f3b060`

Reviewer: `test_reviewer` (read-only vs application code). Write owner: `general_implementer`.
Change: `engineering/changes/20260815-resolve-contour-residual-contradictions-aea9d4`
Date: 2026-08-15

**PASS.**

Required plan cases exist, call the real policy / hook / `_python` paths (pytest-wins is mocked as specified), and would fail on a revert of the three residuals. Suite size is **109** `def test_*` methods, matching the write-owner `unittest discover` OK.

## What was inspected

Change package:

- `engineering/changes/20260815-resolve-contour-residual-contradictions-aea9d4/{requirements,test-plan,architecture,brief,tasks}.md`
- `engineering/changes/20260815-resolve-contour-residual-contradictions-aea9d4/evidence/implementation.md`

Tests (read in full):

- `tests/test_policy.py` — wrapped-shell deny / echo-allow / approval-lift plus keep-green path/echo/cat/approve/direct-invocation
- `tests/test_repo_router.py` — `can_reuse_active_route` helper
- `tests/test_hooks.py` — same-session reuse, other-session rematch, `ready` rematch, child keep
- `tests/test_verification_doctor.py` — nested glob + pytest-wins
- Surrounding suite still present: `test_bitrix.py`, `test_change_receipts.py`, `test_installer.py`, `test_manifest_package.py`, `test_runtime_state.py`, `test_structure.py`

Implementation they claim to cover (read, not edited):

- `.grok-stack/adaptive_grok/policy.py` — `_unwrap_shell`, `is_production_invocation` (unwrap then re-chunk)
- `.grok-stack/adaptive_grok/router.py` — `CLOSED_ROUTE_STATUSES`, `can_reuse_active_route`; `should_reuse_active_route` remains `FOLLOW_UP_RE` only
- `.grok/hooks/user_prompt_submit.py` — child **or** `can_reuse_active_route`, else rematch
- `.grok-stack/adaptive_grok/verification.py` — `tests.glob('test*.py')`; pytest-wins still returns early

Harness: `tests/_support.py` `run_hook` still executes `.grok/hooks/<name>` on a `project_copy` tree (runtime wiped). Hook rematch tests exercise the canonical hook, not a stub.

## Coverage vs acceptance criteria

| # | Criterion | Test(s) | Verdict |
| --- | --- | --- | --- |
| 1 | `bash -lc 'git push origin feature'` without approval → deny, reason contains `approval` | `PolicyTests.test_wrapped_shell_push_requires_approval` | **Covered.** Real `evaluate_pre_tool`. Fail-first: this was FAIL before unwrap. |
| 2 | `bash -c "git push origin feature"` without approval → deny | same | **Covered.** |
| 3 | `sh -c 'npm publish'` without approval → deny | same | **Covered.** |
| 4 | `bash -lc 'cd dist && git push origin feature'` without approval → deny | `test_wrapped_shell_chained_push_requires_approval` | **Covered** as a deny lock. Weaker as an unwrap proof: `_command_chunks` splits on `&&` before unwrap, so the naive second chunk already matches `git push` (write owner noted it was already green). Requirement still locked. |
| 5 | Those same wrapped commands after valid `production` approval → allow | `test_approval_lifts_wrapped_shell_push` (all four strings, `add_approval(..., 'production', ...)`) | **Covered.** Already green before unwrap (no production match ⇒ already allow). The pair with the deny tests is what proves both sides. |
| 6 | `bash -lc 'echo git push origin feature'` → allow | `test_wrapped_shell_echo_is_not_a_side_effect` | **Covered.** Would fail if unwrap switched to substring `git push`. |
| 7 | Leftover `session_id=A` status=`routed`, prompt `делай`, session A → same `route_id` | `HookTests.test_followup_reuses_active_route`; helper `test_can_reuse_requires_same_session_and_open_status` | **Covered** at hook (`build_route` default `routed`) and helper. |
| 8 | Leftover session A, `делай` session B → new `route_id` | `test_followup_rematches_when_session_differs`; helper `session-2` False | **Covered.** Fail-first: leftover `route_id` was kept. |
| 9 | Same session, status=`ready` (or completed/released/cancelled/archived), `делай` → new `route_id` | Hook `test_followup_rematches_when_route_is_ready`; helper `ready` → False | **Covered for `ready`.** Other closed statuses are the same `in CLOSED_ROUTE_STATUSES` branch and are **not** asserted (see missing). |
| 10 | Child payload keeps leftover | `test_child_agent_brief_does_not_replace_parent_route` | **Covered** for the combined production shape (`agent_id` + `agent_type` + `You are architect.…`). Session is `child-1` vs leftover `leftover`, so a broken child check rematches. |
| 11 | `tests/nested/test_x.py` only → `_python` does not light `python-unittest` | `test_python_ignores_nested_unittest_without_top_level` (`_python(root) == []`) | **Covered.** Fail-first against `rglob`. |
| 12 | `pyproject.toml` + `tests/` + pytest present → `pytest`, not `python-unittest` | `test_python_pytest_wins_when_project_marker_present` (mocked `command_exists` / `_command_check`) | **Covered**, mocked as the plan required. Control flow is real `_python`. |

### Test-plan extras (keep-green)

| Plan item | Present? |
| --- | --- |
| Path / echo / cat / approve-script / direct invocation still green | Yes — `test_path_text_is_not_a_side_effect`, `test_echo_and_cat_arguments_are_not_side_effects`, `test_approve_script_is_not_blocked_by_scope_argument`, `test_real_side_effect_invocations_still_require_approval`, `test_approval_lifts_real_side_effect_invocations`, `test_chained_push_still_requires_approval` |
| `should_reuse_active_route` still FOLLOW_UP_RE-only | Yes — `test_reuse_active_route_only_for_followups` (`делай`/`continue` True; repair/non-keyword False) |
| Child brief existing test kept | Yes |
| Nested glob + pytest-wins characterization | Yes |

Tests are not vacuous: wrapped deny would pass if unwrap were dropped; session/`ready` rematch would keep the leftover `route_id`; nested glob would light `python-unittest` under `rglob`; pytest-wins would emit `python-unittest` if the early return were removed (`tests/test_ok.py` exists).

## Missing cases

Not fail reasons. Test plan’s named cases are present.

| Gap | Severity | Why it is not a fail |
| --- | --- | --- |
| Helper/hook never assert `completed` / `released` / `cancelled` / `archived` | Low | Requirements treat them as the same closed set; plan only names `ready`. Removing one name from `CLOSED_ROUTE_STATUSES` would not fail a test. |
| `can_reuse(..., non-follow-up, same session)` not asserted | Low | `should_reuse_active_route` still locks the vocabulary; hook rematch for repair/non-keyword already exists. |
| Wrapped allow/deny not re-driven through `pre_tool_use.py` | Low | Plan says `test_policy.py`. Hook is a thin wrapper; `test_pre_tool_hook_denies_destructive_command` still wires deny. |
| `zsh`/`dash`/`ksh`, `sudo bash -c`, `bash -l -c` (two flag tokens) | Low / accepted | Architecture allows those shells; residual explicitly excludes two-token `-l -c`. Not in AC. |
| pytest-wins does not assert `_command_check` argv `['pytest', '-q']` | Low | Names on real `_python` results are enough to lock the branch. |
| Marker + no pytest still running unittest | Low | Prior residual; **not** in this AC. |
| `continue` at hook with session mismatch / `ready` | Low | Plan uses `делай`. Helper + `should_reuse` cover the token. |
| Isolated child-key **or** `You are …` branches | Low | Combined payload is the live Grok shape (same as prior review). |
| `git push --force` vs production approval | Out of scope | Prior Medium gap; this change did not touch destructive order. |

## Characterization / fail-first quality

Write-owner fail-first log is consistent with the code:

- Unwrap lock is `test_wrapped_shell_push_requires_approval` (was FAIL). Chained/echo/approval-lift were already green and stay as requirement locks, not unwrap proofs.
- Rematch lock is the two new hook tests (were FAIL: leftover `route_id` kept) plus the helper (was ImportError).
- Discover-shaped glob lock is nested `test_x.py` (was FAIL via `rglob`).
- pytest-wins was already green; this change adds the missing characterization the previous contour review called out.

`FOLLOW_UP_RE` is unchanged (`test_reuse_active_route_only_for_followups`). Child still short-circuits before `can_reuse`.

## Verification evidence

Write owner recorded:

```text
python3 -m unittest discover -s tests
# Ran 109 tests in 10.216s
# OK
```

Independently counted **109** `def test_*` across `tests/test_*.py`. `python3 scripts/grok_doctor.py` is not pasted, but `test_project_doctor_has_no_failures` is inside those 109.

## Residual risk

- One quoted `-c`/`-lc` layer only. `python -c`, `os.system`, nested shells, and `bash -l -c` stay unwrapped by design (non-goals).
- Quote-unaware `_command_chunks` can still split a quoted `&&` before unwrap; chained wrapped deny is therefore double-covered (naive split **and** unwrap-then-resplit) and is not a unique unwrap test.
- Closed statuses other than `ready` share one set membership with no per-status lock.
- Stop fail-open, HIGH_RISK scoring, packaging, VERSION unchanged and untested by this change (correct).

## Recommendation

**PASS**

Adequacy matches `requirements.md` / `test-plan.md` for wrapped-shell deny/allow/approval, same-session reuse, other-session rematch, `ready` rematch, child keep, nested `test*.py` not lighting `python-unittest`, and mocked pytest-wins. Parent evidence of **109 OK** matches the method count. The only worthwhile follow-up is parametrizing `can_reuse` over the full `CLOSED_ROUTE_STATUSES` set; that is a missing lock, not an inadequate suite for what landed.
