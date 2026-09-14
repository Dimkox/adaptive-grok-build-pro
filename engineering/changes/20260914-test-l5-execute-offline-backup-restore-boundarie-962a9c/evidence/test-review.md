# Independent test/evidence review — offline L5 backup/restore boundary suite

VERDICT: fail (one blocking evidence defect, F-1; the test code itself is sound — no re-implementation needed)

Reviewed tree: worktree `/home/pall/grok-projects/adaptive-grok-build-pro-l5-coverage`, HEAD `5f6f6ce`,
uncommitted working tree. Host: Python 3.12.3, `httpx` 0.28.1 present; `fastapi`, `uvicorn`, `psycopg`,
`pypdf` absent; `coverage` 7.15.4. All measurements re-run by this review; coverage data written only to
`/tmp/review-testreview-9001/` via `COVERAGE_FILE` (`git status --porcelain` identical before and after).

## Findings

1. **MAJOR — F-1: §2 "before" column mixes two measurement bases and one value is not a measurement.**
   `evidence/coverage-before-after.md:24-27` claims before = `landing_sqlite_store.py` "329 stmts, 44%" and
   `landing_artifact_retention.py` "136 stmts, 24%". Neither matches the stated basis ("executed factory
   suite"): `coverage run --source=factory/src/adaptive_factory -m unittest discover -s factory/tests -t .`
   on a `git archive HEAD` copy of the base tree measures **82%** (39→45 miss) and **80%** (18 miss)
   respectively — the same basis that produces §5's numbers (all five §5 values reproduce exactly from that
   data file, which proves the basis). Under the only other plausible basis (base tree, `unittest
   factory.tests.test_landing_backup`, loader error) they are **12%** and **24%**. 44% is simply the *after*
   single-suite value copied into the before cell. Impact: a reader concludes the change did not move
   `landing_sqlite_store` "reached through reopen_store", when in fact suite-wide that module went 82%→83% and
   the 44% is only this suite's slice. Minimal fix: label each row's basis and set the before cells to
   82% / 80% (or add an explicit "this suite only, base tree: 12% / 24%" column). Rows 1-2 (`landing_backup`
   12%, `landing_host_config` 22%) are safe — they reproduce under **both** bases.
2. **MINOR — F-2: the guard's private-root assertion is self-satisfying.**
   `factory/tests/test_landing_backup.py:90-92` iterates `landing_host_fixture.ROOT_FIELDS` — the same tuple
   that drives `mkdir(mode=0o700)` (`landing_host_fixture.py:44-46`). Running the child script verbatim
   (extracted by AST, `/tmp/.../child.py`) against each tuple-shrink mutant printed `offline_test_support_ok`
   for dropping `output_path`, `scratch_path`, `quarantine_path` and `publication_state_path`: the fixture
   stops creating that private root and the assertion shrinks with it. It is still caught *by side effect*
   only — the enclosing `LandingBackupTests.setUp` → `load_host_config` errors
   (`SettingsError: closed landing host configuration required`), so `FAILED (errors=1)` for all four. Same
   shape for `assert case.data["live_enabled"] is False` / `assert config == case.config_path`: the first pins
   a real default (mutant `"live_enabled": True` → `FAILED (failures=1)`), the second is trivially true.
   Minimal fix: pin the contract in the child — `assert landing_host_fixture.ROOT_FIELDS == ("state_path",
   "quarantine_path", "source_path", "scratch_path", "output_path", "publication_state_path",
   "control_repository")` and `assert set(landing_host_fixture.PATH_FIELDS) - set(landing_host_fixture.ROOT_FIELDS)
   == {"actors_file", "socket_path"}`.
3. **MINOR — F-3: the guard is a named denylist, but the helper's docstring promises "standard library plus
   offline-safe product modules" only.** Mutating the helper to `from PIL import Image` with an *importable*
   stub placed on the child's PYTHONPATH left the guard green (`Ran 1 test ... OK`), while the same trick with
   an importable `fastapi` stub is caught. `pypdf` (pinned in this repo) and `adaptive_factory.landing_media` /
   `landing_pdf_worker` are not in `BLOCKED`, so a future helper import of them reintroduces exactly the
   dependency-gated collection failure this change removes — undetected on any host where those wheels exist.
   AC-002 as written lists only the nine blocked names, so this is hardening, not a spec violation. Minimal
   fix: in the child, snapshot `sys.modules` before the import and reject any newly loaded top-level module
   whose root is not in `sys.stdlib_module_names | {"adaptive_factory","adaptive_delivery","factory"}`.
4. **MINOR — F-4: AC-003 is verified by inspection and static analysis only, never by a green host run.**
   `factory.tests.test_landing_host` remains a module-level loader error on this host (confirmed in the
   discover log), so the 36 test methods that consume the extracted fixture execute nowhere in this change's
   evidence. I could not find a lost assertion by reading, and static checks are consistent (ruff F821 clean;
   every `self.<attr>` the host module reads is provided by the fixture or the subclass; the helper collects
   0 tests, so discovery is unaffected) — but "no host test body weakened" is currently an argument, not a
   measurement. Minimal fix: add one line to the evidence noting the host suite is deps-gated here and that
   AC-003 rests on the lossless-move proof below (or run it once on a deps-complete host before merge).

## Verified as sound (no finding)

- **Lossless extraction.** Line-set diff of `git show HEAD:factory/tests/test_landing_host.py` (551 lines) vs
  the new file (509) plus `landing_host_fixture.py` (65): every removed line appears verbatim in the helper;
  the only helper lines absent from HEAD are the module docstring and
  `from adaptive_factory.landing_renderer import TARGET_REPOSITORY_ID`. `def test_` counts: host 36 → 36,
  backup 15 → 16. No `skip`, `skipUnless`, `expectedFailure`, deleted test or relaxed assertion in
  `git diff HEAD -- factory/tests` (`grep -n "skip\|expectedFailure\|- *def test"` → no hits). Product tree
  untouched: `git diff --name-only HEAD` = `decisions.md`, `mistakes.md`, the two test modules; only
  `factory/tests/landing_host_fixture.py` added.
- **AC-002 mutation behaviour (my own experiments, in a scratch copy — the real worktree was never mutated;
  `diff -q` against a saved copy confirms it).** Control with an importable `fastapi` stub and unmodified
  helper: `OK`. M1 helper re-adds `from fastapi.testclient import TestClient`: `FAILED (failures=1)`, child
  stderr `AssertionError: offline import reached fastapi` at `find_spec` — so the guard is loud on a
  full-stack host, not just here. M2 `chmod(0o600)` deleted: `FAILED (errors=1)`,
  `SettingsError: private file must be an owned regular mode-0600 file`. M3 roots created `mode=0o755`:
  `FAILED (failures=1)` (child assertion). §4's negative control reproduces verbatim.
- **Cannot hang CI.** Both guard tests pass `timeout=20` to `subprocess.run`; an analogous 120 s child under
  the same call raised `TimeoutExpired after 20.0s` with no orphan process. Child temp state is released in a
  `finally` (`case.tearDown(); case.doCleanups()`). Guard tests add ~0.4 s to the suite (16 tests in 1.1 s).
- **No stray artifacts** (all coverage data in `/tmp/review-testreview-9001`); the child PYTHONPATH of repo
  root + `factory/src` is sufficient (`factory/tests/__init__.py:1-9` supplies `delivery/src` in-process).

## Remaining untested production risk (do not read L5 backup/restore as fully exercised)

- **The shipped CLI entry is 0% executed.** 16 of the 34 uncovered statements in `landing_backup.py` are
  `main()`'s body (`304-312`, `314-319`) and its `__main__` hook (`323`) — argparse surface, the
  `needs_human` / `snapshot_unavailable` degradation and exit code 2, and `--manifest-sha256 or ""` feeding
  `restore_snapshot`. `factory/pyproject.toml:16` publishes this as the `adaptive-landing-state` console
  script; no test imports `landing_backup.main` or runs `python3 -m adaptive_factory.landing_backup`. (The
  fail-closed digest regex at `landing_backup.py:244` *is* covered through direct `restore_snapshot` calls.)
- The other 18 uncovered statements are failure-branch targets (42, 93, …, 296; 19 partial branches), i.e.
  mid-copy I/O error, budget exhaustion during the copy rather than the reservation, and per-entry unlink
  rollback are still unexercised.
- **The real-FastAPI host path stays dark here**: `landing_host.py` 9%, `landing_server.py` 21%,
  `landing_publication_cli.py` 46%, `landing_media.py` 74%, `resources/landing_pdf_worker.py` 0% (measured
  unchanged on both trees). The extracted fixture's behaviour under those 36 host tests is unverified by
  execution (F-4), as is `restore_snapshot` against a `live_enabled=true` config (fixture is always offline).
- Enforcement is still absent: `.coveragerc` `fail_under = 74` covers only `.grok-stack/adaptive_grok` +
  `scripts`, so none of these numbers gates anything yet (#63 req 2 / #51, out of scope by FORBID-003).

## Reproduced measurements

| claim in `coverage-before-after.md` | measured by this review | match |
| --- | --- | --- |
| before `unittest factory.tests.test_landing_backup`: `Ran 1 test`, `errors=1`, `ModuleNotFoundError: No module named 'fastapi'`, 0 boundary tests | identical, at `before/factory/tests/test_landing_host.py:17` | MATCH |
| after same command: `Ran 16 tests` / `OK` / 0 loader errors | `Ran 16 tests in 1.099s` / `OK`, 16 collected, no skip | MATCH |
| `landing_backup.py` before 249 stmts / 12% / 210 missed | 249 / 12% / 210 (both discover and single-module basis) | MATCH |
| `landing_backup.py` after 249 / 84% / 34 missed | 249 / 84% (83.99%) / 34 | MATCH |
| `landing_host_config.py` before 47 / 22% / 32 | 47 / 22% / 32 | MATCH |
| `landing_host_config.py` after 47 / 80% / 7 | 47 / 79.7% (80%) / 7 — `25, 31, 33, 39, 55, 58, 83` | MATCH |
| `landing_sqlite_store.py` before 44% | 82% (base discover) / 12% (base single-module); 44% is the after value | **MISMATCH (F-1)** |
| `landing_sqlite_store.py` after 44% via `reopen_store` | 44% this suite only; 83% whole suite after | MATCH |
| `landing_artifact_retention.py` before 24% | 80% on the stated (discover) basis; 24% only single-module | **WRONG BASIS (F-1)** |
| `landing_artifact_retention.py` after 24% | 136 / 93 / 24% | MATCH |
| uncovered `landing_backup.py` lines "(34): 42, 93, … 304-319, 323" | `coverage report -m` string reproduces verbatim; `coverage json` gives `304-312, 314-319` (313 is a continuation of the 312 statement) so 34 statements ↔ 35 rendered line numbers | MATCH (cosmetic) |
| discover before `Ran 415`, `errors=37, skipped=7` | exactly that | MATCH |
| discover after `Ran 430`, `errors=36, skipped=7` | exactly that (26.0 s vs claimed 22.4 s) | MATCH |
| "+15 executed tests, −1 loader error" | 415→430 = +15; 37→36 = −1 | MATCH |
| 22 `psycopg` + 11 `fastapi` + 3 `uvicorn` = 36 | parsed all 36 ERROR blocks: `{'psycopg': 22, 'fastapi': 11, 'uvicorn': 3}` | MATCH |
| 14 module-level loader errors, listed names; `test_landing_backup` absent; `test_landing_host` present | 14 `unittest.loader._FailedTest` errors, name-for-name identical, backup absent, host present | MATCH |
| `test_landing_publication_cli` + `test_landing_sse`: `Ran 50` / `OK` | `Ran 50 tests in 5.822s` / `OK` | MATCH |
| `tests.test_landing_architecture_boundaries` + `tests.test_change_spec`: `Ran 34` / `OK` | `Ran 34 tests in 0.903s` / `OK` | MATCH |
| `tests.test_architecture_fitness`: `Ran 101` / `OK` | `Ran 101 tests in 65.628s` / `OK` | MATCH |
| `ruff check` on the three files: `All checks passed!` | `All checks passed!` | MATCH |
| §4 negative control `AssertionError: offline import reached fastapi` | reproduced (also with an importable stub, M1) | MATCH |
| §5: host 9%, server 21%, publication_cli 46%, media 74%, pdf_worker 0%, unchanged | 9%, 21%, 46%, 74%, 0% from the base discover data; host/pdf_worker identical after | MATCH |
| host 36 / backup 15→16 test methods, no skips | 36 / 15 → 36 / 16; no `skip`/`expectedFailure` | MATCH |
| host facts: Python 3.12.3, `httpx` present, `fastapi`/`uvicorn`/`psycopg`/`pypdf` absent | all confirmed | MATCH |

Summary: 24 numeric/factual claim groups checked — **22 reproduced exactly**, 1 unreproducible
(`landing_sqlite_store` before = 44%), 1 recorded on the wrong basis (`landing_artifact_retention` before =
24%). Every headline claim (16 tests OK, 84%, 80%, 430/36/7, +15/−1, 22+11+3, 14 loader errors, 50/34/101
focused runs, ruff) is true. Fixing F-1's two table cells and its column label turns this review to pass.

## Round 2 (re-verification after the evidence rewrite, the F-2/F-3 hardening, and the §7 deps-complete run)

**VERDICT: pass.** F-1 is corrected and every §2 value now reproduces; F-2 and F-3 are fixed in a way that
**bites under my own mutations**, not just in wording; F-4 is now closed by execution (§7) rather than by
declaration. Remaining items are nits (N-1…N-6), none blocking. Re-measurement scratch:
`/tmp/review-testreview-r2/{base,mut}` (`git archive HEAD` export + `cp -a factory delivery`), all coverage
data via `COVERAGE_FILE=/tmp/review-testreview-r2/.cov{A,B,C}`; `git status --porcelain` unchanged; my runs
wrote **no** `.coverage` into the worktree (the gitignored `./.coverage` there is dated 04:15:54 UTC, before
this round, and was not modified by me — its mtime is proof), and my deps-venv runs used
`PYTHONDONTWRITEBYTECODE=1` (plain runs did refresh gitignored `__pycache__/*.pyc`, as any local test run
does); `/opt/adaptive-l5` not written (verified below); `diff -q` confirms my mutation tree still equals the
real tree after every experiment.

### Findings

- **F-1 CLOSED.** §2 now states three explicit bases and all 12 numbers reproduce exactly (table below).
- **F-2 CLOSED, child-side proof added.** The 0700 loop now iterates six pinned root names
  (`test_landing_backup.py:113-117`). I captured the **real** child program by patching `subprocess.run`
  under the guard test (argv `[python, -c, code, <repo>]`, env `PYTHONPATH=<repo>:<repo>/factory/src`,
  `timeout=20`, no `PYTHONOPTIMIZE`) and ran it standalone in the scratch tree. New results, all child-side
  (round 1's escape is gone): `mkdir(mode=0o700)`→`0o755` → `AssertionError: state_path`; skipping creation
  of one root → `FileNotFoundError: .../scratch_path`; and the same captured child run against an **unmutated**
  helper still prints `offline_test_support_ok`, so these failures are mutation-specific and not the child
  blowing up on its own fixture. At suite level the skip-root mutant gives `FAILED (failures=1)` — a
  *failure*, so the parent `setUp` did not pre-empt the child, exactly what §4's own caveat said it could
  not show for M3/M4.
- **F-3 CLOSED.** `foreign()` fires on a real installed third-party package: `import certifi` in the helper →
  `AssertionError: [('certifi', ['/home/pall/.local/lib/python3.12/site-packages/certifi/__init__.py', …]),
  ('certifi.core', […])]`; `import PIL` → `AssertionError: [('PIL', [.../site-packages/PIL/__init__.py, …]),
  ('PIL._version', […])]` — the same shape §4/M2 records (Pillow really is installed here, so M2 needed no
  stub). Name-blocklist additions bite too: `import starlette` and `import psycopg2` →
  `offline import reached starlette` / `…psycopg2`; `from fastapi.testclient import TestClient` →
  `FAILED (failures=1)` (M5). Control with those directories present and nothing imported → `OK`.
  `-O` hardening verified end-to-end: with a **child-only** mutant (`frozenset({TARGET_REPOSITORY_ID})` →
  `frozenset()`) the guard test fails **both** normally and with `PYTHONOPTIMIZE=1` in the parent, while the
  captured child env has no `PYTHONOPTIMIZE`; and running that same captured child under `python3 -O`
  silently prints `offline_test_support_ok` for all three mutants — i.e. `child_env()` is load-bearing, and
  §4's measured claim is true.
- **F-4 CLOSED by execution (§7).** I reproduced it independently (see table).

### Nits (non-blocking)

- **N-1:** `foreign()`'s `added` set is snapshotted once, at import. Mutating `reopen_store()` to lazily
  `import certifi` leaves the guard **green** (the deferred module is not in `added`, and `certifi` is not
  name-blocked). §4/§5's wording ("every module the helper **import** loads") does not overclaim, so this is
  only a coverage gap. Fix: recompute `added` (or take a fresh diff) inside the second `foreign()` call.
- **N-2:** a third-party package **vendored inside the repository** is invisible to the location rule — my
  `factory/src/PIL/__init__.py` stub made `import PIL` pass, while the identical import resolving to
  site-packages failed. Also, `child_env()` overwrites `PYTHONPATH`, so the §4 preamble's "stubs on
  `PYTHONPATH`" is not literally how M0/M2 became visible; the recorded M2 output can only come from a
  location outside the repo (site-packages), which is what I measured. Suggest one clarifying clause.
- **N-3:** the §4 M1 row is reproducible only because the mutated module stays importable by the **parent**
  (the parent imports the helper at module level). With `import starlette` and nothing on disk anywhere, the
  observed signature is a collection `ModuleNotFoundError`, not `offline import reached starlette` — still
  loud, different mechanism. Worth a parenthetical so a reproducer isn't surprised.
- **N-4 (§7 wording):** "`no module other than `test_landing_host.py` itself matches
  `grep -rn "test_landing_host import" --include=*.py .`" — on this tree that exact command returns **zero**
  hits, so the clause's stated self-match does not exist. Its conclusion is nonetheless true, which I checked
  a different way: the only files mentioning `HostFixture`/`ROOT_FIELDS`/`PATH_FIELDS` are the two test
  modules plus the helper (`.grok-stack/adaptive_grok/architecture.py:63` is the unrelated
  `RULE_PATH_FIELDS`), and no rule or inventory entry is keyed on the host test module. Suggest rewording to
  "grep for the moved symbols finds only these three files".
- **N-5 (§7 completeness):** the interpreter is deps-complete but **not** DB-complete, and §7 does not say
  so: 142 of the 144 skips are `test_postgres_integration` (71), `test_execution_persistence_postgres` (68),
  `test_runtime_capability_postgres` (2) and one pdf-worker case. So the 712/713 figure evidences "no
  regression in what this environment can execute", not that the Postgres paths ran. §7 already states the
  skip contents "were not investigated", so this is one clarifying clause rather than a defect.
- **N-6 (§4 procedure provenance):** §4 says the mutation runs touched only `/tmp/l5mut-*`, "never in the
  worktree". Host state shows at least one `-O` run imported the **worktree** copies:
  `find . -name "*.opt-1.pyc"` returns 14 files under `factory/src/adaptive_factory/__pycache__/` plus 3 under
  `factory/tests/__pycache__/`, all stamped 04:16:14–04:16:15 UTC, and `opt-1` bytecode exists only if a
  process with `optimize == 1` imported those exact paths. Their scratch is real and present
  (`/tmp/l5mut-1789360375/{stubs,repo}`, with `stubs/{starlette,PIL}/__pycache__` showing the stubs were
  imported), so this is a narrow exception, not a false claim — and the content is provably clean:
  `factory/tests/landing_host_fixture.py` is byte-identical to the snapshot I took during round 1
  (`diff -q` → IDENTICAL at the start of round 2). Suggest one clause: "the `-O` probes were also run against
  the unmutated worktree" (if M3's mutation was applied there, say so — content-neutral, but the procedure
  sentence should be exact). Related refinement to N-2: their quoted M2 origin
  `.../site-packages/PIL/__init__.py` cannot come from `stubs/PIL` (outside the child's `PYTHONPATH`); it
  comes from the **real Pillow installed on this host**, which is exactly what my own M2 reproduction hit — so
  the result stands and only its attribution needs the tweak.

### Reproduced measurements — §2 (A/B/C), §6 and §7

| claim | my measurement | match |
| --- | --- | --- |
| A `landing_backup.py` 12% (210 missed) | base tree discover: 249/210/12% | MATCH |
| A `landing_host_config.py` 22% (32) | 47/32/22% | MATCH |
| A `landing_sqlite_store.py` 82% (45) | 329/45/82% | MATCH |
| A `landing_artifact_retention.py` 80% (18) | 136/18/80% | MATCH |
| B `landing_backup.py` 84% (34) | 249/34/84% (`Ran 16 tests` / `OK`) | MATCH |
| B `landing_host_config.py` 80% (7) | 47/7/80% | MATCH |
| B `landing_sqlite_store.py` 44% (167) | 329/167/44% | MATCH |
| B `landing_artifact_retention.py` 24% (93) | 136/93/24% | MATCH |
| C `landing_backup.py` 84% (34) / host_config 80% (7) | 84%/34 and 80%/7 | MATCH |
| C `landing_sqlite_store.py` 83% (39) / retention 80% (18) | 329/39/83% and 136/18/80% | MATCH |
| §2 "uncovered lines … 304-319, 323" | `coverage report -m` string identical | MATCH |
| §6 "16 of the 34 uncovered statements are the console entry" | `coverage json`: 34 missing, 16 in 304-319/323, 18 elsewhere | MATCH |
| §1/§3 base 415 / errors=37 / skipped=7; this 430 / 36 / 7 | 415/37/7 and 430/36/7 re-run this round | MATCH |
| §3 focused: 16 OK, 50 OK, 34 OK, 101 OK, ruff clean | 16 OK, `Ran 50 tests in 6.567s` OK, `Ran 34` OK, `Ran 101 tests in 70.189s` OK, `All checks passed!` | MATCH |
| §7 interpreter: venv python 3.12.3; fastapi 0.128.2 / httpx 0.28.1 / psycopg 3.3.4 / pypdf 6.18.1 / uvicorn 0.48.0; no `coverage` | all read from that venv via `importlib.metadata`; `coverage` and `pytest` ABSENT | MATCH |
| §7 base tree: `test_landing_host` `Ran 36 … OK` | `Ran 36 tests in 1.039s / OK` | MATCH |
| §7 this tree: `test_landing_host` `Ran 36 … OK` | `Ran 36 tests in 0.919s / OK`; and the 36 test **names** are identical between trees (`diff` of the `-v` id lists → no output) | MATCH |
| §7 discovery: base `Ran 712 … OK (skipped=144)`, this `Ran 713 … OK (skipped=144)` | 712/OK/skipped=144 and 713/OK/skipped=144 | MATCH |
| §7 "one added test, zero outcome changes" | per-test id diff base↔this: exactly one addition, `test_offline_test_support_imports_no_web_stack`; status counts 569 ok + 144 skipped, **0** FAIL/ERROR | MATCH |
| §7 `test_landing_pdf_worker` `Ran 8 … OK (skipped=1)` | `Ran 8 tests in 1.056s / OK (skipped=1)` | MATCH |
| §7 read-only: `find /opt/adaptive-l5 -maxdepth 4 -newermt '-40 minutes'` empty | empty on my re-run too; I widened it to `-newermt '2026-09-14 03:26:00'` (after the release dir's 03:24:47 mtime and `adaptive-l5.service` ActiveEnterTimestamp 03:25:35 UTC) → **still empty**, so nothing was installed or touched | MATCH (stronger) |
| §7 lock correspondence claim (five names) | `factory/uv.lock` fastapi 0.128.2 (:76-77), httpx 0.28.1 (:114-115), psycopg 3.3.4 (:138-139), pypdf 6.18.1 (:324-325), uvicorn 0.48.0 (:376-377) = venv versions; the cited line numbers are right | MATCH |

**Ruling on the two addendum questions.** (1) *Legitimate, with one caveat worth adding.* The interpreter is
not an arbitrary venv: its five libraries equal the `factory/pyproject.toml:9` / `factory/uv.lock` direct
pins, it is the interpreter of the deployment built from this very base SHA (`5f6f6ce…`), and the run used
`PYTHONPATH=.:factory/src:delivery/src` so the **source under review** was executed and not the release's own
installed copies — I confirmed the resolution: `adaptive_factory` → `…/…-l5-coverage/factory/src/adaptive_factory/…`,
`factory.tests.test_landing_host` → the worktree file, `fastapi` → the venv, and in the base tree
`adaptive_factory` → `/tmp/review-testreview-r2/base/factory/src/…`. The caveat: across **all 21** lock
entries the venv is not lock-exact — `anyio` is 4.15.1 there vs 4.14.2 in `factory/uv.lock:45-46`
(`tzdata 2026.3` is absent but marker-gated `sys_platform == 'win32'` (`factory/uv.lock:143`), so that one is
correct). A one-line statement — "direct pins exact, one transitive (anyio) newer than the lock" — makes the
claim airtight without weakening it. Citing a deployed release's venv is also a *host-state* dependency: it is
not reproducible on a clean checkout, so §7 should stay framed as corroboration for AC-003, with the
system-interpreter numbers in §2/§3 remaining the reproducible record. (2) *No measured result in §7 is
overclaimed* — every count, version, timestamp and outcome I checked reproduces (table above), including
"identical" at the per-test-name level and zero FAIL/ERROR lines. The only imprecisions are wording, recorded
as N-4 and N-5, and neither changes what §7 establishes.

**Round 2 summary.** 22 further claim groups checked (§2's 12 numbers, §6's two, §3/§1 re-runs, §7's 8):
**all 22 match**; nothing measured in the rewritten file failed to reproduce. Round 1's single blocking defect
(F-1) is closed, its two hardening findings (F-2, F-3) now fail loudly under my own mutations, and F-4 is
closed by execution. Outstanding production risk is unchanged from round 1: the shipped `adaptive-landing-state`
CLI (`landing_backup:main`, 16 of the 34 uncovered statements), the mid-copy failure branches, and the
Postgres-backed paths (skipped, not executed) still have no coverage — all of it declared follow-up
(#63 req 2) rather than claimed here.
