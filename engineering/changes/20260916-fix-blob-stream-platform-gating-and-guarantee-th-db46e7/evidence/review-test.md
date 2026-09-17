PASS

# Test review — fix/blob-stream-cleanup (closes #109)

Reviewed as independent test_reviewer. Only artifacts: `git diff 05b69c7fbb1de7d7bc43f54863dd6cc95fdaa5f3..8b4d82a6e215936360d34e176b1d2bb84b1896c6`
(production `.grok-stack/adaptive_grok/architecture_diff.py`, 3 hunks / 21 lines; `tests/test_architecture_fitness.py`, +106 lines / 3 arms).
Note: the code review was done against `22f4926d0a560ef5d5fef1b811a0dd263a57f27c`; `22f4926` and HEAD `8b4d82a` have the **identical tree** `ee74854254b12e00b6b3e9d929954fbf88299612` (amend only fixed the commit-message `'m` typo the reviewer flagged — HEAD message now reads `'streamed blob setup failed'` verbatim). The issue #109 public correction is real: `gh api repos/Dimkox/adaptive-grok-build-pro/issues/109/comments` → one comment, `2026-09-17T00:06:48Z`, `Dimkox`, explicitly retracting the false `os.name == "posix"` dispatch claim.
Host: Python 3.12.3, git 2.43.0. All experiments in `/tmp/109-base` and `/tmp/109-fix` (created with `git archive | tar -x`); the worktree `adaptive-grok-build-109` was never mutated (read-only `git show/diff/log` only).

Sandbox construction (exactly reproducible):
```
rm -rf /tmp/109-base /tmp/109-fix && mkdir -p /tmp/109-base /tmp/109-fix
git -C /home/pall/grok-projects/adaptive-grok-build-109 archive 05b69c7fbb1de7d7bc43f54863dd6cc95fdaa5f3 | tar -x -C /tmp/109-base
git -C /home/pall/grok-projects/adaptive-grok-build-109 archive 8b4d82a6e215936360d34e176b1d2bb84b1896c6 | tar -x -C /tmp/109-fix
cp /home/pall/grok-projects/adaptive-grok-build-109/tests/test_architecture_fitness.py /tmp/109-base/tests/test_architecture_fitness.py
# verified: md5(/tmp/109-base/.../architecture_diff.py)=73d37ed6f7e87ff1b681442338059ce4 == `git show 05b69c7:...architecture_diff.py | md5sum`
# verified: md5(/tmp/109-fix/.../architecture_diff.py)=72d71ae8a4e1231f0091ca31cc025c85 == `git show 8b4d82a:...architecture_diff.py | md5sum`
```

## 1. Red/green matrix — established by EXECUTION (closes code-review Limit (a))

Each arm run individually from `/tmp/109-base` (HEAD test file, base module):
`cd /tmp/109-base && python3 -m unittest tests.test_architecture_fitness -k <arm> -v`

| Arm | Result on base | Failure mode (verbatim tail) |
|---|---|---|
| `test_stream_git_blob_setup_failure_is_typed_and_stops_child` | RED (ERROR) 0.040 s | `File "/tmp/109-base/.../architecture_diff.py", line 524, in _stream_git_blob / selector = selectors.DefaultSelector() … RuntimeError: simulated selector setup failure` — raw RuntimeError escapes where the test demands `ArchitectureError`; additionally leaked 1 live `sleep 120` (count 3→4) |
| `test_stream_git_blob_stops_child_on_unnamed_exception` | RED (FAIL) 0.035 s | `line 2705 … AssertionError: unexpectedly None : child survived an exception the handlers do not name` + live orphan proven: `3602626 1 00:00 sleep 120` (ppid=1). `assertRaises(RuntimeError)` itself passed on base — RED comes purely from the new-guard property |
| `test_profile_worktree_blob_closes_directory_when_descriptor_close_fails` | RED (FAIL) 0.035 s | `line 2737 … AssertionError: 4 not found in [3, 3] : directory fd leaked behind a failing descriptor close` — close list shows only two fd-3 closes; directory fd 4 never attempted |

All three arms PASS on `/tmp/109-fix` (see §2). The three reds are orthogonal: each pins exactly one of the three hunks (proved in §4/M3).

## 2. Green run + leak measurements (closes code-review Limit (b))

Full module on fix: `cd /tmp/109-fix && time python3 -m unittest tests.test_architecture_fitness`
→ **`Ran 109 tests in 70.157s` / `OK`** (claim 106→109 confirmed; wall 1m10.5s). `pgrep -xc sleep` before=after=3 (pre-existing foreign ones; no delta).

Per-arm leak probe (in-process, `/tmp/leak_probe.py`, runs the 3 arms in one interpreter, snapshots `/proc/self/fd`, direct children via `ps --ppid`, system `sleep 120` count before/after each arm). On `/tmp/109-fix`:
```
baseline: fds=4 children=1 sleep120=0
ARM ...setup_failure_is_typed_and_stops_child: PASS in 0.039s | fds 4->4 (new: []) | children 1->1 | sleep120 0->0
ARM ...stops_child_on_unnamed_exception:       PASS in 0.037s | fds 4->4 (new: []) | children 1->1 | sleep120 0->0
ARM ...closes_directory_when_descriptor...:    PASS in 0.036s | fds 4->4 (new: []) | children 1->1 | sleep120 0->0
END: fds=4 children=1 sleep120=0 rc=0          (whole probe wall 1.344s)
```
(the only "new child" per row was the probe's own transient `ps`). **Zero leaked children, zero leaked fds, ~37 ms/arm — no 120-second wall-clock penalty**, because the fake children are real `sleep 120` processes that the finally-guard SIGKILLs and `wait()` reaps before the arm ends.

Identical probe on `/tmp/109-base` (control): arms 1+2 each left a **live unreaped `sleep 120`** (`system sleep120 0->1`, `1->2`; pids 3638848, 3638861 listed as direct children); arm 3 left the process holding **2 extra fds** (`fds 4->6`, new `['4','5']`) because its red assertion aborts before the test's own `real_close` cleanup. Leaks confirmed by execution, differential green-vs-base quantified. After the probe the leftover `sleep 120`s were killed; note two kills during cleanup were pre-existing `sleep 120`s (pids 3598636/3600529, ≤4 min old, same self-terminate-≤120 s signature as the code reviewer's concurrent-gate orphans) and, from an over-broad cleanup loop, one foreign `sleep 10` (3638394) was also killed — a transient shell nap of another session, no data impact; disclosed for transparency. Long-lived `sleep 86400`s were untouched. Stray `sleep 120`s seen once between steps self-terminated within their window (re-check found none).

## 3. Determinism — 5× per arm on `/tmp/109-fix`

`for i in 1..5: python3 -m unittest tests.test_architecture_fitness -k <arm>` — **15/15 OK, no flake.**
- arm 1: 0.039 / 0.033 / 0.037 / 0.044 / 0.040 s (wall 0.18–0.21 s)
- arm 2: 0.039 / 0.045 / 0.039 / 0.040 / 0.039 s (wall ~0.21 s)
- arm 3: 0.038 / 0.037 / 0.035 / 0.038 / 0.031 s (wall 0.18–0.23 s)

No timing/clock/order dependency: arm 1's fake selector raises at construction, arm 2's raises on the first `select()` call (unconditional, and `get_map()` is non-empty so the loop is entered), arm 3 never reaches the stream loop; none can drift into the 30 s `_GIT_TIMEOUT_SECONDS` deadline. Arms pass both isolated (`-k`) and in full-suite ordering.

## 4. Mutation results (mutants applied only inside `/tmp/109-fix`, module restored to pristine `72d71ae…` after each; final `md5sum` == `git show 8b4d82a` blob, and post-restore subset run `OK`)

| # | Mutation (on green code) | Outcome | Evidence |
|---|---|---|---|
| M1 | **stop child but MASK original exception**: widen `except (OSError, subprocess.TimeoutExpired)` → `except Exception` (mid-loop escapes become ArchitectureError) | **CAUGHT** | arm 2 ERROR: unexpected `adaptive_grok.architecture.ArchitectureError: Git blob stream failed: packages/midstream.bin: simulated unnamed mid-loop failure` instead of RuntimeError |
| M6 | **swallow entirely**: append `except Exception: _stop_process(process)` (no re-raise) | **CAUGHT** | arm 2 ERROR — the swallowed flow falls through the `finally` to `if returncode:` and raises `UnboundLocalError: cannot access local variable 'returncode'`, which is not the expected `RuntimeError`. (arm 1 stays green here because the setup-wrap already types its exception; division of labor is correct) |
| M3 | **wrap setup but keep OLD finally** (delete `if process.poll() is None: _stop_process(process)`) | **CAUGHT** | arm 2 FAILED (failures=1), arms 1+3 green — exactly the intended pinning: hunk 3 is guarded by arm 2, hunk 2 by arm 1 |
| M2 | **swap close order** in `_profile_worktree_blob` (`os.close(directory)` in try, `os.close(descriptor)` in finally) | **SURVIVED** | all 3 arms OK. The swapped variant still attempts both closes and still closes `directory` when descriptor fails, so the tested property holds; what it changes (which error is primary / which close is the protected one) is untested. See Finding 2 |
| M4 | **rename wrap message** `"streamed blob setup failed: …"` → `"blob io failed: …"` | **SURVIVED** | arm 1 OK — `assertIn("setup", str(exc).lower())` is satisfied by the *cause* text `{exc}` = the fake's own "simulated selector setup **setup** failure". The message assertion is vacuous against a rename. See Finding 1 |
| M5 | **drop the poll() guard** (unconditional `_stop_process(process)` at end of finally) | **SURVIVED** | full module still `Ran 109 tests / OK (70.134 s)`; the 6 pre-existing stream/profile tests ok. Nothing pins "no killpg after reap". See Finding 3 |

Answers to the specific honesty questions: a stop-but-mask implementation is caught (M1/M6, via exception-identity asserts); a directory-before-descriptor variant passes (M2, argued above as a defensible-but-different fix); a setup-wrap without the old-finally replacement fails (M3).

## 5. Suite isolation

No network: git usage inside the arms is local only (`init -q -b main`, `config user.*`, `add`, `commit`, `rev-parse`) in a `tempfile.TemporaryDirectory` registered with `testcase.addCleanup(self._temp.cleanup)` (pre-existing `file://`-clone test elsewhere in the module also non-network). The production-side `_git_environment()` is sealed (`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_TERMINAL_PROMPT=0`, minimal PATH). Real `git` binary is required, but only by the *fixture* (repo creation + oid resolution before any patch); `DIFF.subprocess.Popen` is patched so the code-path under test never executes `git cat-file` — same convention as all 106 pre-existing arms. Monkeypatches (`DIFF.subprocess.Popen`, `DIFF.selectors.DefaultSelector`, `DIFF._open_worktree_file`, `DIFF.os.close`) are `with`-scoped context managers, restored per arm; full-suite ordering stays green. Files touched: tmpdir + read of `schemas/*.json` from the repo copy. Cleanup verified live: probe children/fds back to baseline; fake `sleep` children reaped (no `ps --ppid` residue, no orphans after green runs). One residual: on RED (base) runs arm 3's own cleanup line `real_close(captured["descriptor"])` is skipped by the failing assert — relevant only to pre-fix trees, inherent to red-state tests.

## Findings

1. **Suggestion — `assertIn("setup", …)` in arm 1 is toothless against message regression (M4 survived).** The appended `from exc` cause text ("simulated selector setup failure") always contains "setup", so renaming the wrap message to anything — even dropping the documented `"streamed blob setup failed"` promise from the issue/commit — keeps the arm green. Concrete failure scenario: a future refactor changes the message to `"blob io failed"`; the #109 contract with the CLI surface (typed, identifiable setup error) silently erodes while the suite stays green. Fix: assert the literal `self.assertIn("streamed blob setup failed", str(raised.exception))` or match on the start (`str(...).startswith(...)`).
2. **Nice-to-have — close-order swap (M2) survives.** A variant protecting `descriptor` instead of `directory` passes all three arms. Both orders guarantee two close *attempts*, but error primacy flips (a descriptor failure would then replace an in-flight directory failure). If the asymmetry matters (the issue text flags it), add a mirror assertion (force directory-close failure, assert descriptor in `closed`). Not a defect in the shipped fix — the shipped order is the one matching the leak the issue describes.
3. **Nice-to-have — the `poll() is None` guard is unpinned (M5 survived).** Removing it keeps 109/109 green, yet it is the line that prevents `os.killpg` on an already-reaped (pid-reusable) process group. A cheap pin exists: patch `DIFF._stop_process` with a counter and assert 0 calls on a success-path test (e.g. the streamed-binary verify arm).
4. **Informational — green-code leak discipline verified.** The `sleep 120` fakes are SIGKILLed+reaped inside the arms (0.036–0.039 s each; per-arm probe 0 new children/0 new fds); the orphans observed on this host all reproduce from base/mutant trees and self-terminate ≤120 s. No suite-timeout coupling: arms never approach `_GIT_TIMEOUT_SECONDS`.

## Commands and evidence (full re-run recipe)

1. Sandbox setup: block at top. 2. Red matrix: `cd /tmp/109-base && python3 -m unittest tests.test_architecture_fitness -k <arm> -v` (three arms; outputs quoted in §1). 3. Green: `cd /tmp/109-fix && python3 -m unittest tests.test_architecture_fitness` → `Ran 109 tests in 70.157s / OK`; leak probe: `python3 /tmp/leak_probe.py /tmp/109-fix` (script snapshot: fds via `/proc/self/fd`, children via `ps --ppid`, orphans via `pgrep -x sleep`). 4. Determinism: 5× `-k <arm>` loop (§3). 5. Mutations: string replacements against `/tmp/109-fix/.grok-stack/adaptive_grok/architecture_diff.py` as described in §4, module md5-restored to `72d71ae8a4e1231f0091ca31cc025c85` after each. 6. Issue trail: `gh issue view 109 …` (body contains the false os.name sentence) + `gh api repos/…/issues/109/comments` (public correction present, pre-merge). Worktree untouched: only `git show/diff/log/archive` were issued against `/home/pall/grok-projects/adaptive-grok-build-109`; `scripts/grok_verify.py` not executed (a gate was observed running: pid 3578581).

## Limits

- Red/green and mutations executed on Linux/POSIX only (CPython 3.12.3, git 2.43.0); the issue's Windows-pipe premise was not and cannot be executed here — tests fake the setup failure, which is the correct POSIX proxy.
- M2 "survives" is a statement about the test's pinning scope, not a claim the shipped order is wrong.
- Leak numbers are for these arms on this host; a concurrent verify gate and other sessions run on this machine and produced transient `sleep 120`s I did not author (deltas were measured only around my own single-process probes, which exclude them).
- During the review window the worktree acquired uncommitted additions to `decisions.md`/`mistakes.md` (+14 lines, factory process records about #109). They are **not mine** — every command I issued against `adaptive-grok-build-109` was `ls`/`git show|diff|log|status|rev-parse|cat-file|archive` (read-only); all writes happened in `/tmp`. HEAD stayed `8b4d82a`, and the shipped tree content I tested is byte-identical to what §Commands pins via md5.

## Summary

Both gaps the code reviewer declared are now closed by execution: all three new arms were run against the base module and go red for three distinct, quoted reasons (raw setup RuntimeError, surviving unreaped child, leaked directory fd), with the leak differentially measured (2 live orphan children and 2 open fds per base probe vs. exactly 0 around the fixed code). The fix is green (109/109, 70 s), deterministic (15/15 isolated arm runs, ~37 ms/arm, no clock or ordering dependency), and honest against the dangerous mutations: exception masking and full swallowing are caught by exact exception-identity asserts, and each production hunk has its own killer arm. Three surviving mutants amount to test-strength nits (vacuous substring message check, unpinned close-order alternative, unpinned poll-guard), none of which misrepresent the shipped behavior — PASS.
