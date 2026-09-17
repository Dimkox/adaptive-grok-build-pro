PASS

# Code review — fix/blob-stream-cleanup (closes #109)

- Reviewed: `git diff 05b69c7fbb1de7d7bc43f54863dd6cc95fdaa5f3..22f4926d0a560ef5d5fef1b811a0dd263a57f27c` (base full SHA differs from the briefed `05b69c767e27…`; prefix `05b69c7` resolves unambiguously to the direct parent).
- Production diff: `.grok-stack/adaptive_grok/architecture_diff.py` only (3 hunks at lines 480, 523, 568; 21 changed lines). Tests: +106 lines, 3 arms. Remainder is package paperwork.
- Route: read-only review; no tree mutation performed.

## 1. Stop-guard semantics — verified, no realistic masking

Final `_stream_git_blob` (lines 504–590) traced end-to-end:

- **Success**: `process.wait(timeout=…)` (556) sets returncode → `poll()` is not None → guard (571–572) no-op → `if returncode:` git/truncation paths unchanged.
- **Typed paths**: `except ArchitectureError` (557) and `except (OSError, TimeoutExpired)` (560) already called `_stop_process` (wait reaps) → guard is no-op; codes `io`/`timeout`/`limit` untouched.
- **Any-escape (BaseException, ValueError, RuntimeError…)**: no handler names it → guard stops the child. This is the fix; pre-fix the finally only closed pipes and the child survived unreaped (nobody-waits zombie, or orphan).
- **Could `_stop_process` inside the finally REPLACE the original exception?** Semantically yes (any raise in finally replaces the in-flight exception, original kept as `__context__`), but no reachable trigger exists: `os.killpg` fails only with ESRCH (caught; and unreachable here — `poll()==None` proves the child is live-or-unreaped-zombie, so the pgid exists since no other process can reap it) or EPERM (impossible: same-cred own child) or EINVAL (fixed SIGKILL). `process.wait()` after SIGKILL cannot raise — it returns on reap; worst case a D-state child delays it, which is a hang, not masking, and is pre-existing at all four older `_stop_process` call sites (except-handlers, lines 558/561, and inside `_run_capped`). Verdict on the parent's question: **not Important** — no swallowing wrapper added; note that wrapping only the finally guard would leave the identical theoretical exposure in the untouched except-branch calls, and the exact guard already exists verbatim in `_run_capped` (153–154) — the diff conforms `_stream_git_blob` to that house pattern, which is the right consistency call. The inner setup wrap uses `except Exception` (not BaseException), so KeyboardInterrupt still escapes raw but is now covered by the guard.
- One same-class residual (pre-existing ordering, not introduced): a raise from `selector.close()`/`stream.close()` earlier in the finally would skip the guard; no realistic trigger (close of read-only pipe object, selector close of a live selector).

## 2. killpg/start_new_session coupling — verified

`_stop_process` (66–71) uses `os.killpg(process.pid, SIGKILL)`, correct only because the real `Popen` passes `start_new_session=True` (line 516): the child is its own pgid/sid leader. Without it the child would sit in the parent's group and `killpg(pid)` would ESRCH→pass→`wait()` could block forever. Both tests' `fake_popen` also spawn with `start_new_session=True` (confirmed live: leaked foreign `sleep 120` show `pgid==sid==pid`). In the BoomSelector arm the `Popen` statement precedes the setup block, so a real child exists before setup fails — kill applies. No zombie leak: `_stop_process.wait()` reaps before the `poll()` assertions; empirically an isolated re-run of the two arms leaked **0** fresh children.

## 3. Nested close in `_profile_worktree_blob` — verified, acceptable

`finally: try: os.close(descriptor) finally: os.close(directory)` (482–486). Single descriptor failure → the descriptor error still propagates unchanged (previously also raw OSError, not ArchitectureError — no error-identity regression) and the directory fd is now guaranteed closed (pre-fix it leaked). Both fail → directory error propagates, descriptor error is `__context__` — acceptable: fd hygiene first, double-close-failure is EBADF-class only. Truncation/staleness checks sit after the finally, unchanged.

## 4. Invariants — held

`_run_capped` outside all diff hunks (function spans 74–156). No added `import`, no `os.name`/`sys.platform`/`hasattr` in code diff (added-line grep matches only package prose). No new dependencies (requirements untouched). AC-004 honored: public correction of the false os.name-dispatch claim is on issue #109 (comment 2026-09-17T00:06:48Z, `gh api issues/109/comments`).

## 5. Tests honest

- **BoomSelector**: `code=='io'` ✓; `'setup' in message.lower()` ✓ ("streamed blob setup failed: packages/stoppable.bin: simulated selector setup failure"); exactly 1 spawn; `poll()` not None after context exit ✓. Red pre-fix: raw `RuntimeError` would fail `assertRaises(ArchitectureError)` (base code confirmed to lack the wrap).
- **SelectBoom**: `get_map()` non-empty → loop entered; `select()` raises `RuntimeError` on the first call — deterministic, no infinite-loop risk (unconditional raise each call; even a reordering that let select return would bound out via the 30 s `_GIT_TIMEOUT_SECONDS` deadline). This arm alone exercises the **new** finally guard (no except clause names `RuntimeError`) — proves guard, not handler, stops the child.
- **spy**: forces descriptor-close failure; asserts `captured["directory"] in closed` (the leak detection, red on pre-fix sequential closes); other fds get `real_close`; cleanup `real_close(descriptor)` after patch teardown — no fd/ResourceWarning leak.

## 6. Scope — clean

`git diff --name-only` = `architecture_diff.py` + `tests/test_architecture_fitness.py` + 11 package files under the db46e7 dir. Nothing else.

## Findings

1. **Minor** — Commit message typo: `ArchitectureError(code=io) 'm streamed blob setup failed'` — stray `'m`; intended `'streamed blob setup failed'`. Docs-only; amend or leave, no artifact impact. (`git log -1 --format=%B 22f4926d`)
2. **Nice-to-have** — Theoretical finally-masking window and post-guard close ordering described in §1; unreachable triggers, identical pre-existing pattern in `_run_capped`; hardening would have to wrap all `_stop_process` call sites in a separate change, correctly out of #109 scope.

## Commands and evidence

- `git diff 05b69c7..HEAD` (+ per-file) — hunks at 480/523/568; `_run_capped` untouched.
- `python3 -m unittest tests.test_architecture_fitness -k profile -k stream -v` → **Ran 6 tests … OK** (2.4 s; includes 3 pre-existing oversized-stream tests: truncated-stream refusal, streamed-binary verify, binary-marker-anywhere → truncation/limit semantics preserved).
- `python3 -m unittest tests.test_architecture_fitness` → **Ran 109 tests … OK** (72 s; matches claimed 106→109).
- Isolated `-k test_stream_git_blob` re-run + `ps -o etimes` fresh-child diff → before=1, after=1 → **0 leaked children from green code**.
- `git show 05b69c7:…architecture_diff.py` — pre-fix finally/handlers confirmed: red-state traces for all three arms established statically (tree not mutated).
- `gh api repos/Dimkox/adaptive-grok-build-pro/issues/109/comments` — AC-004 correction present, pre-merge.

## Limits

- Red-on-base verified by static trace against the base file plus one live leaked-children differential, not by executing the new tests against reverted code (read-only mandate).
- Three orphaned `sleep 120` (00:32:17 UTC, ppid=1) appeared during my full-module window; proven not mine (identical earlier targeted run left zero; isolated re-run leaked zero) — a concurrent session ran these arms against a pre-fix tree, exactly the leak this fix closes; self-terminate ≤120 s.
- External Trust CI check-run on the exact head SHA and merge authority are out of scope for this local review.

## Summary

Fix is minimal, mirrors the proven `_run_capped` pattern, and each of the three regression arms fails on the base code for a different defect (raw setup exception, unnamed-escape child leak, directory-fd leak). Full module 109/109 green; zero child leaks from the fixed code under live observation. **PASS** — one Minor commit-message typo, one Nice-to-have theoretical note.
