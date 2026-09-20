# Issue #158 — child reaping: spawner ruling, design decision, measured arms

Branch `fix/trust-ci-child-reaping`, baseline HEAD `90078959ff816068af374ad42f4bb80fdbaec866`.
Written by the implementation owner. No commit, no push, no receipt recorded here.

## 1. The spawner: both the issue body and my own correcting comment were wrong about the site

The measurement in my comment is right; the inference drawn from it is not. The inference
("every spawn in the tree uses `start_new_session=True`, therefore it is not `workspace._git`")
is invalid because it reads live-host evidence against **HEAD** while the host runs the
**deployed** revision.

### 1.1 The worker is PID 1 of its own PID namespace — it is the kernel reaper, by role

```
$ grep -E '^(NStgid|NSpid|NSpgid|NSsid|PPid)' /proc/1234679/status
NStgid: 1234679 1
NSpid:  1234679 1
NSpgid: 1234679 1
NSsid:  1234679 1
PPid:   1234114
$ ps -o pid,ppid,pgid,sid,stat,comm -p 1234114
1234114 ... containerd-shim        # /usr/bin/containerd-shim-runc-v2 -namespace moby -id 748bd0a104b2...
$ ps --ppid 1234679 -o pid,ppid,pgid,sid,stat,etime,comm
 527342 1234679 1234679 1234679 Z  1-01:03:39 git
 964198 1234679 1234679 1234679 Z    23:59:02 git
1467439 1234679 1234679 1234679 Z    22:33:10 git
1595657 1234679 1234679 1234679 Z    22:10:17 git
```

* Each zombie has a **two-level** `NStgid`/`NSpid` (`527342 11`, `964198 804`,
  `1467439 1858`, `1595657 2123`) → the zombie lives in the *worker's* PID namespace.
* The worker has **no live children at all** — only these four zombies. Nothing else runs in
  that namespace, so no sandbox container ran inside it.
* Uid of worker and zombies is identical: `10001` (the worker image's `trustci` user).

PID 1 of a PID namespace is where the kernel reparents orphans. An adopted child that exits is
a zombie **until the worker calls `waitpid()`** — no call site can reap it, because the process
that forked it is gone. This, not "a missing `wait()`", is the defect.

### 1.2 The `pgid == sid == worker` signature identifies the *deployed* revision, not a non-workspace spawner

```
$ docker ps --format ... | grep adaptive-trust-ci-worker-1
748bd0a104b2  5f2ab9fb137c  adaptive-trust-ci-worker-1  2026-08-25 14:23:10 +0000 UTC  Up 37 hours
$ docker image inspect 5f2ab9fb137c --format '{{.Created}} {{json .RepoTags}}'
2026-08-25T13:47:27.901042866Z ["adaptive-trust-ci-worker:pr7-c4d1ce7", ...]
$ git log -S'start_new_session' --format='%h %ad %s' --date=iso -- trust-ci/src/adaptive_trust_ci/workspace.py
8599d45 2026-09-04 11:31:48 +0300 Integrate M4-M9 control plane and product identity 2.0.13 (#22)
```

The running image is built from `c4d1ce7` (2026-08-25), **ten days before**
`start_new_session=True` reached `workspace.py`. At `c4d1ce7` the git path is:

```python
# git show c4d1ce7:trust-ci/src/adaptive_trust_ci/workspace.py  (_git, _git_output, _commit_exists)
process = subprocess.run(['git', *args], cwd=self.path, text=True, capture_output=True,
                         check=False, timeout=300, env=self._git_env(authenticated=authenticated))
```

No `start_new_session` → every `git` the worker spawns is in the **worker's own process group and
session**, exactly what the four zombies show. That `_git_env` at `c4d1ce7` also lacks
`core.fsmonitor=false`, `core.hooksPath=/dev/null` and `GIT_CONFIG_GLOBAL=/dev/null` (all three
are present at HEAD) and sets `HOME` to the checkout, so a helper/daemon `git` process —
`git remote-https`, `git index-pack`, `git fsmonitor--daemon`, all `comm=git` — can be forked by
the reaped `git` and outlive it. Its parent is then gone, it is adopted by PID 1 (the worker), it
exits, and it stays in the PID table forever.

**Ruling: the leak owner is the worker's own trusted git path (`workspace.GitWorkspace`, called
once or more per job), amplified by the worker's PID-1 reaper role.** Not a call site that
forgot a `wait()`, and not the holdout bundle.

### 1.3 The holdout bundle does **not** run in the worker process

* `runner.py:310` is the only worker-side holdout action: `verify_bundle(self.policy.holdout.path,
  self.policy.holdout.digest)` → `holdout.py:bundle_digest`, pure `pathlib`/`hashlib`, no spawn.
  `worker.py:62-79` only resolves/validates holdout paths.
* Holdout *commands* (`runner.py:440-450`) go through `JobRunner._run_command` →
  `self.executor_factory(self.policy.sandbox).run(...)` → `ContainerExecutor.run` →
  `docker run ... --volume {host_holdout}:/holdout:ro` (`sandbox.py:88`), i.e. into the sandbox
  container, with `holdout_path` passed only as a bind mount.
* `compose.yaml`: the worker reaches the engine over `DOCKER_HOST: tcp://docker-engine:2375`, so
  executed containers live in the `adaptive-trust-ci-docker-engine-1` namespace tree, never in the
  worker's PID namespace — which is precisely why the leaked `git` processes cannot be attributed
  to `holdout.example/change_spec_validate.py:71`. That line is still the only in-repo `git`
  invocation without a new session, but it is bundle content and it runs under `/holdout` inside
  the sandbox. No holdout bundle content was changed here.
* Whole-package evidence: `subprocess.Popen|subprocess.run` appears in `src/adaptive_trust_ci/`
  only in `workspace.py`, `sandbox.py` and `backup.py` (Arm 4 turns this into an enforced test).

## 2. Design decision: loop-boundary `waitpid(-1, WNOHANG)` drain, no SIGCHLD handler

`trust-ci/src/adaptive_trust_ci/reap.py` (new) provides `reap_adopted_children()`, wired to the
worker's existing boundaries: `worker.run()` (top of the loop, and after each job) and
`LeaseKeeper.check()` (the mid-job boundary the runner already calls between phases).

**No `SIGCHLD` handler is installed, and none should be.** `subprocess` collects status with
`waitpid()` on a *specific* pid. A handler running `waitpid(-1, WNOHANG)` can harvest the status
of a child that a `Popen.wait()`/`communicate()` is still owed, and CPython's `Popen._try_wait`
maps the resulting `ECHILD` to `sts = 0` — a failed or killed command reported as a passing one,
which is exactly the #103/#132 misclassification family. A handler also fires asynchronously in
the main thread at arbitrary bytecode boundaries, i.e. between `Popen` construction and its
`wait()`. This hazard is *measured*, not asserted (Arm 2b): the naive sweep harvested the tracked
pid and its `Popen.wait()` then returned `0` instead of `7`.

Why the drain cannot steal a status, in the shipped form:

1. Every function in the package that creates a child and reaps it before returning is decorated
   with `@guarded_spawn` (`workspace._run_bounded_process`, `sandbox.ContainerExecutor.run`,
   `sandbox._remove_container`, `backup._run`), so an in-flight `Popen` always implies a
   non-zero spawn counter.
2. `reap_adopted_children()` checks that counter and performs the `waitpid(-1, WNOHANG)` loop
   **under the same lock**, and that lock is held by `spawn_in_progress()` while a child is being
   born. So a sweep can neither overlap a tracked child nor lose a race with a newly created one.
   When anything is in flight the drain declines and the next boundary re-runs the same
   non-blocking sweep — no status is ever consumed twice, and nothing blocks.
3. Both reaping points are **main-thread**. The `LeaseKeeper` renewal loop in `__enter__` runs on
   its own thread and is deliberately *not* a reaping point: draining there would race a
   `Popen.wait()` issued by the main thread.
4. `SIGCHLD` is neither ignored nor handled by the service and a test asserts importing and
   calling the reaper leaves it `SIG_DFL`. Measured on the live worker
   (`/proc/1234679/status`): `SigIgn: 0000000001001000` → signals 13 (SIGPIPE) and 25 (SIGXFSZ);
   `SigCgt: 0000000100004002` → signals 2 (SIGINT), 15 (SIGTERM) and 33. SIGCHLD is signal **17**,
   i.e. mask bit 16 (`0x10000`), absent from both words — so the accumulation is a missing reap by
   the reaper, not a signal-mask artefact (issue #158's own disposition paragraph reaches the same
   conclusion; its bit annotations list signals 13/25/2/15, which is correct).
   Ignoring `SIGCHLD` would be worse than a handler: it makes `waitpid` return `ECHILD` for every
   child and `subprocess` fabricate `0` for all of them.
5. Exit statuses of *adopted* orphans are unobservable to any consumer (their spawner is dead), so
   discarding them is safe. That is the asymmetry the whole design rests on.

Not changed, on purpose: attestation format and fields, check name/policy epoch, holdout bundle
content, PostgreSQL schema or durable state, runner isolation, `_classify_post_kill_process_group`
(`absent`/`zombie_only`/`live`/`unknown`), exit-status classification, signal handling, and all
secret/key handling. `trust-ci/runtime/**` was never read (only the operator container/image
metadata from `docker ps` / `docker image inspect`).

## 3. The arms (`trust-ci/tests/test_reaping.py`, 14 tests) and their measured results

Arm 1 reproduces the production mechanism in a disposable process: it makes itself a subreaper
(`prctl(PR_SET_CHILD_SUBREAPER)`, which gives an unprivileged test the same adoption PID 1 gets
for free), spawns through the worker's *own* git helper `workspace._run_bounded_process` running
`/bin/sh -c 'sleep 0.3 & exit 0'` (a helper that outlives its spawner, the `git remote-https`
shape), waits until an exited child has actually been adopted, calls the reaping boundary, then
re-scans `/proc` for `state == 'Z'` and `ppid == self`.

| Arm | Test | Measured |
| --- | --- | --- |
| 1 | `test_lease_boundary_reaps_adopted_child` | green: `adopted` length 1 (non-vacuous), `remaining == []` |
| 1 | **red-before-green**, same test copied into a throwaway clone at `90078959` | **FAIL** `AssertionError: Lists differ: [715981] != []` (behavioural, not an import error — the file never imports `reap` at module level) |
| 1 | `test_control_without_a_reaping_boundary_keeps_the_zombie` | green: adopted 1, remaining 1 — a zombie never clears by itself; **also green on the pristine tree** (it is a characterisation, not a fix assertion) |
| 1 | `test_worker_loop_boundary_reaps_and_still_returns_after_one_pass` | green: `worker.run(once=True)` reaches the boundary and still returns 0 |
| 2 | `test_drain_preserves_the_return_code_of_a_tracked_child` | green: tracked `Popen.wait() == 7` while the main thread swept in a loop; `declined` grew; `spawns_in_progress() == 0` afterwards |
| 2b | `test_naive_unbounded_sweep_does_steal_the_status` | green: naive `waitpid(-1, WNOHANG)` returned the tracked pid and its `wait()` no longer reported 7 — the measured justification for the guard; **green on the pristine tree too** (the hazard is CPython's, not ours) |
| 2 | `test_sweep_declines_entirely_while_any_spawn_is_in_progress` | green: returns 0, `reaped` counter unmoved |
| 2 | `test_timeout_path_still_classifies_as_timeout_and_releases_its_guard` | see arm 3 |
| 3 | `test_timeout_path_still_classifies_as_timeout_and_releases_its_guard` | green: `WorkspaceError ... exceeded its timeout` unchanged, guard released, no `declined`/`errors` drift |
| 3 | `test_heartbeat_failure_still_raises_after_reaping` | green: same message `job lease heartbeat failed: database is down`, drain called exactly once |
| 3 | `test_sigchld_disposition_is_never_taken_over` | green: `SIG_DFL` before and after |
| 3 | `test_missing_runtime_classification_is_unchanged` | green: `exit 127` + `required sandbox runtime not found` unchanged through the decorator |
| 4 | `test_every_spawn_call_site_is_inside_a_guarded_region` | green here, **FAIL on the pristine tree** (all four sites are unguarded there) |
| 4 | `test_guarded_sites_are_exactly_the_worker_spawn_helpers` | green: the spawn inventory is exactly the four helpers; green on both trees by design |
| 4 | `test_run_is_really_wrapped_by_the_spawn_guard` / `test_real_spawn_through_the_decorated_helper_reaps_its_child_and_releases_the_guard` | green: `ContainerExecutor.run` really is wrapped, a real child exits `3` and is reaped, `spawns_in_progress() == 0`, no `Z` child of the test process left |

`ContainerExecutor.run` had **no test coverage before this change** (`test_ops.py` only builds
argv), so the decorator on the docker/podman path would otherwise have shipped unverified; the two
arm-4 tests above close that gap, using a stub runtime instead of Docker.

Breakdown on the pristine tree, for reference: 3 ok — exactly the three characterisations
(no-boundary control, the naive-theft hazard, the spawn inventory), 3 FAIL — the behavioural red
(arm 1 reap, `test_run_is_really_wrapped_by_the_spawn_guard`, arm 4 guarded-site coverage), 8 ERROR
(`ModuleNotFoundError: adaptive_trust_ci.reap`).

Arm 3 covers the #103/#132 lineage: the cancellation/abort classification is `absent` /
`zombie_only` / `live` / `unknown` plus `exit 124` timeouts, and those tests in
`test_workspace.py` all still pass (see §4). `aborted` does not exist in this tree yet —
`#103` and `#132` are both still OPEN on GitHub, so "must not shift" is enforced as "the existing
kill/timeout/post-kill classification and messages are byte-identical".

### Stronger red/green pair: real PID 1, not emulation

`unshare --user --map-root-user --pid --fork` and plain `unshare --pid --fork` are both denied on
this host (`Operation not permitted`), so the same scenario was run as **actual PID 1** in a
disposable container built from the *deployed* image (`5f2ab9fb137c`, `--network none`, repo
mounted read-only, no env/keys/volumes from the service), calling the unchanged public API
`LeaseKeeper(...).check()`:

```
### RED: deployed-era code (pristine 90078959) as real PID 1 ###
pid_is_1 True | adopted_zombies [8]
after_lease_boundary [8]
### GREEN: fixed code as real PID 1 ###
pid_is_1 True | adopted_zombies [8]
after_lease_boundary []
```

Identical scenario, identical call, opposite outcome — the difference is the fix.

## 4. Verification (canonical invocations, printed)

Gate invocation found in the repo, not guessed: `Makefile:19` (`trust-ci-test`) and
`trust-ci/README.md:398`.

```
$ cd <worktree> && PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest discover -s trust-ci/tests
Ran 257 tests in 17.236s
OK (skipped=10)

# baseline: pristine clone of 90078959ff..., same invocation, without the new test file
Ran 243 tests in 6.677s
OK (skipped=10)
```

+14 tests, same 10 skips (PostgreSQL integration needs a live test stack), zero regressions.

```
$ git diff --numstat            # insertions only; no pre-existing line, and no assertion, deleted
2  0  trust-ci/src/adaptive_trust_ci/backup.py
9  0  trust-ci/src/adaptive_trust_ci/lease.py
3  0  trust-ci/src/adaptive_trust_ci/sandbox.py
9  0  trust-ci/src/adaptive_trust_ci/worker.py
2  0  trust-ci/src/adaptive_trust_ci/workspace.py
$ git diff --check              # clean, exit 0
$ git status --short            # + untracked reap.py and test_reaping.py
```

Ruff: `trust-ci/pyproject.toml` carries **no** `[tool.ruff]`, so the root config applies —
confirmed with `ruff check --show-settings trust-ci/src/adaptive_trust_ci/reap.py` →
`Settings path: ".../ruff.toml"`.

```
$ ruff check <the 6 touched src files> trust-ci/tests/test_reaping.py
All checks passed!
$ ruff check .                  # 23 pre-existing errors, none in this change's files
Found 23 errors.                # pilot/, factory/tests/, delivery/, plus pre-existing
                                # trust-ci/src/adaptive_trust_ci/lookup.py:3 F401 (verified
                                # identical on the pristine 90078959 clone; lookup.py is untouched)
$ python3 -m compileall -q trust-ci/src trust-ci/tests && echo ok
ok
```

Live-host confirmation (no restart, no signal sent to the service):

```
$ ps -eo ppid,stat | awk -v p=1234679 '$1==p && $2 ~ /^Z/' | wc -l
4
```

Still 4, as expected: these four entries predate the fix and **can only be cleared by restarting
the worker**. The worker is a running service this session did not start, so it was not touched —
restarting it (and re-measuring the `ps` count across several check runs, issue #158 Done-when 4)
is the **operator's** action after deploy, not something claimed here.

## 5. Not verified / open

* The exact `git` subcommand behind each zombie cannot be named: a zombie has no readable
  `/proc/<pid>/cmdline` or `exe`, and the deployed container rootfs is not visible from this
  mount namespace (the worker's `cwd`/`exe` readlinks are empty for this user). What is proven is
  the spawner *class* and the adoption mechanism (§1.1–§1.2).
* `python3 scripts/grok_verify.py --mode pr` and the route-selected review agents were **not**
  run: this contour owns only the product change and this file, `.grok-stack/**` and `factory/**`
  are live in other contours, and any local receipt would go stale the moment the controller
  writes. No receipt is claimed.
* Reaping under a *real* `git fetch` orphan was not exercised end-to-end (needs network +
  credentials + the stack); Arm 1/§3 reproduce the same kernel mechanism through the worker's own
  spawn helper, and the §3 container run reproduces it as PID 1 with the deployed image.
* `reap_stats()` (`sweeps`/`reaped`/`declined`/`errors`) is exposed but **not** plumbed into
  `/metrics`: `OperationalMetrics` is a frozen payload and changing it is out of budget. Wiring
  it up, or an operator `ps`-based post-deploy assertion, is the named follow-up.
* `README.md`/`CHANGELOG.md`/`VERSION` untouched (no commit authority in this contour); they will
  need to match the tree before release.

## 6. Attack first, in this order

1. **`LeaseKeeper.check()` as the mid-job reaping point.** It is the main-thread boundary, and the
   heartbeat thread is excluded on purpose. Anyone who later drains on that thread invalidates the
   no-theft argument — the counter is the backstop, the thread rule is the primary guarantee.
2. **Guarded-site completeness.** Arm 4 recognises `Popen/run/call/check_call/check_output` and the
   `guarded_spawn`/`spawn_in_progress` names only. A future `os.posix_spawn`, `os.system`,
   `loop.subprocess_exec`, or a spawn in a third-party dependency bypasses the enumeration and
   would silently reintroduce the theft window.
3. **The counter is conservative, not precise.** `ContainerExecutor.run` holds the guard for the
   whole command, so mid-job drains decline during every sandbox phase; the effective reaping
   happens in the git phases and at the loop boundary. Growth is bounded at one sweep per job —
   correct for #158, but it is *not* a prompt reap during a long command. If a reviewer wants
   per-pid precision instead of a global decline, that is a design change, not a bug.
4. **`_terminate_process` still accepts `zombie_only`** (`workspace.py:208-213`) without reaping
   those group members, and `_process_group_exists` keeps `os.killpg(pgid, 0)` succeeding while
   they exist, so a cancelled git call still burns its 0.25 s + 1 s grace before the drain ever
   sees them. Left untouched because that classification is #103/#132 territory.
5. **The one `RLock` held across the sweep.** A finishing spawn's decrement waits for the sweep;
   the sweep is `WNOHANG` and exits as soon as nothing has exited, so it is bounded — but it is a
   lock inside the worker's hot path and deserves a hostile read.
