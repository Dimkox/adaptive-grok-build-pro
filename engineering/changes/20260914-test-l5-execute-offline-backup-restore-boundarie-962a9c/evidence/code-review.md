# Code review — test(l5): execute offline backup/restore boundaries without web-stack fixture coupling

Reviewed tree: worktree `/home/pall/grok-projects/adaptive-grok-build-pro-l5-coverage`, branch
`feat/l5-runtime-execution-tests`, base `5f6f6ce`. Uncommitted working tree + untracked
`factory/tests/landing_host_fixture.py` and this change package. Reviewer: code_reviewer (read-only).

VERDICT: pass

No Critical or Major defect found. The extraction is byte-faithful, the destructive boundaries really
execute on a host with no fastapi/uvicorn/psycopg, the guard test is provably non-vacuous, and every
scope rule in `requirements.md` / `change-spec.yaml` holds. Three Minor hardening findings, none
blocking.

## Findings

### 1. Minor — the blocked-import policy is duplicated verbatim, so the two guards can drift
`factory/tests/test_landing_backup.py:43-46` (`blocked` inside the existing child) and
`factory/tests/test_landing_backup.py:72-75` (`BLOCKED` inside the new child) carry the same
9-name tuple as two independent literals. Both tests assert the *same* offline guarantee, one for
product modules and one for test support. Failure it causes: when the web surface grows (e.g. a future
`adaptive_factory.landing_metrics`), a contributor adds it to one tuple only; the other test keeps
passing and reports the boundary as covered while it is no longer enforced — a silent, reviewable-as-green
regression of exactly the class this change exists to prevent.
Minimal fix: hoist one module-level `BLOCKED_IMPORTS` tuple in `test_landing_backup.py` and interpolate it
into both child programs (e.g. `repr(BLOCKED_IMPORTS)` formatted into the `textwrap.dedent` template), so
there is a single list to audit.

### 2. Minor — the child's `assert` statements are silently disabled by an inherited `PYTHONOPTIMIZE`
`factory/tests/test_landing_backup.py:107` builds the child env as `{**os.environ, "PYTHONPATH": ...}`, and
the child program enforces every fixture-semantics check with bare `assert`
(`:85`, `:91-93`, `:96-97`, `:99`, `:100`). Failure it causes: `PYTHONOPTIMIZE=1` (a legitimate
CI/distro-hardening setting, inherited through `os.environ`) strips all child asserts, so the 0700-root,
0600-config, `live_enabled is False`, `TARGET_REPOSITORY_ID`-binding and `database_path.is_file()` checks
stop running while the test still reports `ok`. Measured:
`PYTHONOPTIMIZE=1 … test_offline_test_support_imports_no_web_stack` → `Ran 1 test … OK`. The import
tripwire itself survives `-O` (the guard raises explicitly, not via `assert`) — verified: same mutation
with `PYTHONOPTIMIZE=1` still exits 1 with `AssertionError: offline import reached fastapi`. So the
exposure is limited to AC-003's scaffolding checks. The pre-existing sibling test at
`factory/tests/test_landing_backup.py:63` has the identical pattern, so fix both together.
Minimal fix: drop the variable from the inherited env —
`env={**{k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}, "PYTHONPATH": ...}` — or replace
child-side `assert` with `if not cond: raise SystemExit(1)`.

### 3. Minor — the blocklist is name-based and misses web-stack entry points under other top-level names
`factory/tests/test_landing_backup.py:72-75` and the `sys.modules` scan at `:76-78` match only the 9 listed
top-level prefixes. `fastapi.testclient.TestClient` is a re-export of `starlette.testclient.TestClient`, and
`starlette`/`psycopg2` are not in the tuple. Failure it causes: on a host where the pinned deps *are*
installed, a re-added `from starlette.testclient import TestClient` (or `import psycopg2`) in
`landing_host_fixture.py` passes the guard while re-gating the offline suite on the same install — the
precise defect (#63) this change repairs, re-introduced in a form the tripwire cannot see. Measured on this
host: `import pydantic` under the guard → `rc=0` (not caught); `import psycopg2`/`import starlette` fail only
with `ModuleNotFoundError`, i.e. by accident of this machine, not by the guard.
Minimal fix: append `"starlette"` and `"psycopg2"` to the (single, per finding 1) tuple. Verified safe: the
helper's current transitive closure loads none of `pydantic`, `starlette`, `anyio`, `httpx`, `fastapi`,
`sqlalchemy` (measured `[]` after `import factory.tests.landing_host_fixture`), so the control child run
still exits 0.

## What I verified (commands + observed output)

1. **Extraction is byte-faithful.** `git show HEAD:factory/tests/test_landing_host.py` vs
   `factory/tests/landing_host_fixture.py`, comparing `ROOT_FIELDS` → end of `reopen_store` with `build_app`
   excluded: `difflib.unified_diff` → `IDENTICAL`. `addCleanup` registration order
   (`landing_host_fixture.py:33` then `:64`), the `mode=0o700` mkdir loop, the `chmod(0o600)` in
   `write_config` (`:58`), the synthetic-actor construction, and the `reopen_store` double-close path all
   moved unchanged. File ends with a newline, no CRLF, no tabs, max line 112 (< 120 limit).
2. **Nothing left dangling in the web-stack half.** `grep -nE 'tempfile|uuid4|SQLiteLandingJobStore|Actor\b'
   factory/tests/test_landing_host.py` → none (the removed imports are genuinely unused there);
   `PATH_FIELDS`/`ROOT_FIELDS`/`json` remain used (`:79,:86,:102,:111,:118,:134,:219`). AST check:
   `class HostFixture` bases `['LandingHostFixture']`, body only `build_app`; helper sets
   `{actors, config_path, data, root, token}` and methods `{setUp, write_config, reopen_store}`; every
   `self.*` read in the host suite resolves to helper, host-subclass (`build_app`, `run_main:324`,
   `assert_writer_released:339`) or `TestCase`. Repo-wide grep found no other consumer of the moved symbols.
3. **`ruff` clean, no new findings.** `ruff check factory/tests/landing_host_fixture.py
   factory/tests/test_landing_host.py factory/tests/test_landing_backup.py` → `All checks passed!`
   (ruff 0.16.3). Repo-wide `ruff check .` → 19 errors, all in files this change does not touch
   (`pilot/*`, `delivery/*`, `trust-ci/*`, and the two declared-pre-existing `test_autonomy.py` /
   `test_semantic_persistence.py` F401s).
4. **Backup suite executes.** `PYTHONPATH=.:/factory/src python3 -m unittest
   factory.tests.test_landing_backup -v` → `Ran 16 tests in 7.369s` (cold) / `1.044s` (warm) → `OK`, 0
   errors, 0 skips; all destructive boundaries listed `ok` (non-overwriting restore, copy-budget before root
   creation, committed-WAL snapshot, manifest + content tamper, symlink/hardlink rejection, concurrent-writer
   exclusion). Guard test alone: `Ran 1 test in 0.218s / OK`.
5. **Guard is not vacuous (mutation-tested without touching repo files).** I re-executed the child program
   extracted from the test: control → `rc=0`, stdout `offline_test_support_ok`; `+ import fastapi` →
   `rc=1`, `AssertionError: offline import reached fastapi`; `+ import httpx` → `rc=1` (httpx *is* installed
   here, so this proves the guard, not a missing package, does the work); `+ import
   adaptive_factory.landing_host` → `rc=1`. The `fullname == name or fullname.startswith(name + ".")` rule
   correctly does *not* over-block `adaptive_factory.landing_host_config` (already proven by the sibling
   child at `:53` which imports it under the same guard and exits 0). The extra `crossed()` `sys.modules`
   scan at `:85/:100` additionally catches a web-stack module pre-loaded by `sitecustomize`/`usercustomize`
   before the finder existed — good belt-and-braces. `finally: case.tearDown(); case.doCleanups()` (`:103-104`)
   runs LIFO (`store.close` before `temporary.cleanup`) and `TestCase.doCleanups` drains all cleanups, so no
   ordering or temp-dir leak defect even if one cleanup raises.
6. **Discovery ignores the helper.** `unittest.TestLoader().discover('factory/tests', top_level_dir='.')` →
   430 collected items, 0 items from `landing_host_fixture`, and the helper appears in none of the 14
   module-level `_FailedTest` entries (`test_api`, `test_execution_persistence_postgres`, `test_landing_api`,
   `test_landing_host`, `test_landing_server`, `test_models`, `test_openapi_contract`,
   `test_postgres_integration`, `test_semantic_persistence`, `test_semantic_repair_lifecycle`,
   `test_semantic_service_api`, `test_semantic_store_runtime`, `test_server`, `test_workspace` — all #57
   deps, matching `evidence/coverage-before-after.md` §3).
7. **Scope rules hold.** `git diff --name-only` → `decisions.md`, `factory/tests/test_landing_backup.py`,
   `factory/tests/test_landing_host.py`, `mistakes.md` only; `git status --short` adds just the untracked
   helper and this package. No `factory/src/**` or `delivery/src/**` change. `git diff -U0 -- factory/tests/`
   filtered for `skip|expectedFailure|def test` yields exactly one added line (`+ def
   test_offline_test_support_imports_no_web_stack`): 15 → 16 backup tests, host test names `diff` → identical
   (36 both). No new dependency, no network, no install step (child uses `sys.executable` + stdlib only).
8. **Adjacent and gating checks re-run by me.** `PYTHONPATH=.:/factory/src python3 -m unittest
   factory.tests.test_landing_publication_cli factory.tests.test_landing_sse` → `Ran 50 tests … OK`.
   `PYTHONPATH=. python3 -m unittest tests.test_architecture_fitness tests.test_landing_architecture_boundaries
   tests.test_change_spec` → `Ran 135 tests in 65.754s / OK` (the added non-`test_*` file trips no
   inventory/fitness rule).
9. **Coverage claim independently reproduced.** `coverage run --source=factory/src/adaptive_factory -m
   unittest factory.tests.test_landing_backup` + `coverage report -m --include='*landing_backup*'` →
   `factory/src/adaptive_factory/landing_backup.py 249 stmts, 34 miss, 84%`, missing-line list equal to the
   `evidence/coverage-before-after.md` §2 list. The 12% → 84% claim is real, as is its host-deps note
   (`httpx` present, `fastapi`/`uvicorn`/`psycopg`/`starlette` absent). The `.coverage` file this produced is
   gitignored (`.gitignore:40`) and `git status --short` is unchanged after my run.

## Handoff note (not a finding)

`factory/tests/landing_host_fixture.py` is still untracked. Both suites hard-depend on it at import time, so
the delivery commit must `git add` it in the same change as the two edited test files; AC-005's
`python3 scripts/grok_verify.py --mode pr` on the *committed* tree remains the parent's step and was not run
here (it writes receipts/state, outside this reviewer's read-only mandate).

## Round 2 — re-review after the write owner applied round 1 + test-review F-2/F-3

All changes are confined to `factory/tests/test_landing_backup.py` (103 insertions vs the 50 of round 1);
`git diff --name-only` → `decisions.md`, `factory/tests/test_landing_backup.py`,
`factory/tests/test_landing_host.py`, `mistakes.md`; `factory/src/**` and `delivery/src/**` still untouched;
`landing_host_fixture.py` and `test_landing_host.py` unchanged since round 1, so the byte-faithful
extraction verdict stands.

VERDICT (round 2): pass

Round 1 findings are genuinely closed, not papered over:

- **F1 closed** — one list at `factory/tests/test_landing_backup.py:22-26`, one guard prefix at `:28-39`
  concatenated in front of *both* child programs (`:65`, `:84`), so the finder is installed before any
  product or support import in each child. The `name + "."` prefix rule still spares
  `adaptive_factory.landing_host_config` (child 1 imports it at `:73` and exits 0).
- **F2 closed** — `child_env` (`:43-46`) drops `PYTHONOPTIMIZE` and both call sites use it (`:79`, `:132`).
  Proved in-process: with `os.environ["PYTHONOPTIMIZE"]="2"`, `T.child_env("x")` contains no
  `PYTHONOPTIMIZE` key; a child launched that way reports `sys.flags.optimize == 0` and its asserts fire.
- **F3 closed and effective** — re-ran the guard against each newly named package: `import starlette`,
  `import psycopg2`, `import starlette.testclient`, `import httpx`, `import fastapi`,
  `import adaptive_factory.landing_host` → all `rc=1`, `AssertionError: offline import reached <name>`.
- **Test-review F-2 closed correctly** — `:116-118` pins the six created roots literally; that set equals
  `landing_host_fixture.ROOT_FIELDS` minus the never-created `source_path` (`landing_host_fixture.py:23-26`),
  so nothing is silently dropped from the 0700 assertion.
- **Test-review F-3 implemented, with two real weaknesses** → findings 4 and 5 below.

### 4. Minor — `foreign()` cannot see anything imported after its name snapshot, so the second assertion is dead code
`factory/tests/test_landing_backup.py:92` freezes `added = sorted(set(sys.modules) - loaded)` at import
time, and `:95` iterates only `added`. The re-assertion at `:125` (`assert foreign() == [], foreign()`)
therefore re-judges the same 71 names and can never return anything new. Failure it causes: a third-party
package reached lazily during `setUp()`/`write_config()`/`reopen_store()` (the phase F-3 was added to
cover) slips through. Measured on the current tree — inserting `import PIL` inside the `try` block yields
`rc=0`, stdout `offline_test_support_ok`, while the same package imported *during* the support-module import
is reported as `('PIL', [.../site-packages/PIL/__init__.py, ...])`. Note `crossed()` at `:124` is a genuine
full `sys.modules` scan and still covers the named web/db stack in that phase, so this is a missed
detection for unnamed dependencies only, not a regression of AC-002. On this host the blind spot is
currently latent: the post-snapshot non-stdlib delta is empty (measured `POST_SNAPSHOT_NONSTDLIB []`).
Minimal fix: move the delta inside the function — `for name in sorted(set(sys.modules) - loaded):` at `:95`
— which makes the `:125` re-assertion meaningful as written.

### 5. Minor — `foreign()`'s containment test is a raw string prefix, so a symlink-aliased checkout turns it red
`factory/tests/test_landing_backup.py:102` compares `location.startswith(str(REPO) + os.sep)` against the
origin/`__path__` strings Python recorded, and `REPO` (`:85`) is `Path(__file__).resolve()`, i.e. canonical.
Any module resolved through an *alias* spelling of the same directory fails the prefix test. Reproduced
exactly: launching the same child with a sys.path entry that is a symlink to the repo
(`/proc/<pid>/cwd`, whose string differs from the resolved root) gives `rc=1` with
`AssertionError: [('factory', ['', '/proc/<pid>/cwd/factory']), ('factory.tests',
['/proc/<pid>/cwd/factory/tests/__init__.py', ...])]` — and the identical run passes (`rc=0`) once the
comparison becomes `os.path.realpath(location).startswith(os.path.realpath(str(REPO)) + os.sep)`.
Reachability in the real test: both `PYTHONPATH` (`:132-134`) and `REPO` are built from `.resolve()`, so the
spelling is self-consistent *unless* an earlier sys.path entry aliases the repo — and `-c` puts the cwd at
`sys.path[0]`, before `PYTHONPATH` (measured: `['', '<PYTHONPATH>', '/usr/lib/python312.zip', ...]`), where
`abspath` normalises `.`/`..` but does not resolve symlinks. So the concrete trigger is running the suite
from a cwd that is a symlink to the repo (`cd ~/work/proj` with `~/work/proj -> ~/projects/proj`, or a CI
workspace whose root is a symlink) — `factory` and `factory.tests` then load via the alias and only those
two names go red, which matches the observed failure set. `.//` and `/../`-style aliases are harmless
(measured `rc=0`), as Python's `abspath` collapses them.
Minimal fix: canonicalise both sides at `:102` with `os.path.realpath` (proven above; ~71 stats, no timing
cost worth naming).

### 6. Minor — the `%`-formatted guard template converts a future literal `%` into a suite-wide loader error
`factory/tests/test_landing_backup.py:39` applies `%`-formatting at module import to
`OFFLINE_GUARD` (`:28-39`). Braces are safe (this is `%`, not `.format`), and the substituted *value* is
safe (`repr()` output is not re-scanned), but a single literal `%` added anywhere in that template body —
e.g. a `# budget 50% of MAX_TOTAL` comment or a `%.2f` message someone pastes in — raises at import time:
measured `TypeError: not enough arguments for format string`. Failure it causes: `factory.tests.
test_landing_backup` becomes a module-level loader error with **0** boundary tests executed — precisely the
silent-green class of breakage issue #63 exists to eliminate, and it would be invisible in a
`factory-unit` run that never discovers `factory/tests`. The other two templates are plain
`textwrap.dedent` and are `%`/brace-immune.
Minimal fix: stop formatting the template — `textwrap.dedent("""... BLOCKED = @BLOCKED@ ...""").replace(
"@BLOCKED@", repr(BLOCKED_IMPORTS))` — or double any literal percent (`%%`).

### Independently re-run on the current tree (parent's numbers confirmed, nothing to correct)

| command | observed |
| --- | --- |
| `PYTHONPATH=.:/factory/src python3 -m unittest factory.tests.test_landing_backup` | `Ran 16 tests in 1.147s` / `OK` |
| `PYTHONPATH=.:/factory/src python3 -m unittest factory.tests.test_landing_publication_cli factory.tests.test_landing_sse` | `Ran 50 tests in 6.576s` / `OK` |
| `PYTHONPATH=. python3 -m unittest tests.test_architecture_fitness tests.test_landing_architecture_boundaries tests.test_change_spec` | `Ran 135 tests in 71.666s` / `OK` |
| `PYTHONPATH=. python3 -m unittest discover -s factory/tests -t .` | `Ran 430 tests in 23.104s` / `FAILED (errors=36, skipped=7)` — unchanged, all #57 deps |
| `ruff check factory/tests/landing_host_fixture.py factory/tests/test_landing_host.py factory/tests/test_landing_backup.py` | `All checks passed!` |
| guard child re-executed verbatim (control) | `rc=0`, stdout `offline_test_support_ok` |
| `PYTHONPATH=.:factory/src:delivery/src /opt/adaptive-l5/.../venv/bin/python -m unittest factory.tests.test_landing_backup` | `Ran 16 tests in 1.065s` / `OK` |
| same deps-complete interpreter, `-m unittest factory.tests.test_landing_host` | `Ran 36 tests in 1.090s` / `OK` |

The last two rows matter. The release venv is genuinely deps-complete (verified read-only via
`importlib.metadata`: fastapi 0.128.2, starlette 0.50.0, httpx 0.28.1, psycopg 3.3.4 + psycopg-binary
3.3.4, pypdf 6.18.1, uvicorn 0.48.0, `coverage` → `PackageNotFoundError`, Python 3.12.3), so the guard
test passing there shows `foreign()` produces **no false failure on a deps-complete host** — the concern
raised in the round-2 brief. And 36 real-FastAPI host tests passing on *this* tree closes the only caveat
in my round-1 report (AC-003 had rested on static proof because the host suite could not execute here);
`evidence/coverage-before-after.md` §7 makes the same claim and it reproduces. Neither run touched the
tracked tree (`git status --short` identical afterwards).

False-failure surface I checked and cleared in `foreign()`: every C-extension and private stdlib name the
offline chain can touch is in `sys.stdlib_module_names` (`_sqlite3`, `sqlite3`, `_socket`, `zlib`, `math`,
`select`, `_json`, `_uuid`, `readline`, `pyexpat`, `_ctypes`, `fcntl`, `termios`, `grp`, `pwd`, `mmap`,
`resource`, `_multibytecodec`, … all `True`), so `lib-dynload` origins are never judged; the
`loaded = set(sys.modules)` baseline at `:90` excludes anything a `.pth`/`sitecustomize` preloaded
(`_distutils_hack`, `site`, `coverage`), and modules installed *into* site-packages cannot cause a red
because `PYTHONPATH` precedes site-packages; a namespace `factory` (no `__init__.py`) is handled — its
`origin` is `None` and is dropped by the `if location` filter while `__path__` entries are used;
`requires-python = ">=3.11"` (`factory/pyproject.toml:8`) covers `sys.stdlib_module_names` (3.10+) and the
`dict[str, str]` annotation; the `+ os.sep` suffix correctly refuses a `/repo-evil` sibling prefix match.
`child_env` strips only `PYTHONOPTIMIZE`; other inherited `PYTHON*` knobs can only make the child fail loudly
(e.g. `PYTHONHOME`), never pass vacuously. Handoff note from round 1 (untracked helper must land in the same
commit; `grok_verify --mode pr` is the parent's step) still stands.

## Round 3 — targeted confirmation of the three round-2 fixes

Scope confirmed: only `factory/tests/test_landing_backup.py` moved (353 lines, `git diff --numstat` =
+91/−15 vs base);
`landing_host_fixture.py` is byte-for-byte the round-1 file (2506 bytes, and the `difflib` comparison against
`git show HEAD:factory/tests/test_landing_host.py` with `build_app` excluded still reports **IDENTICAL**), so
the AC-003 verdict stands unamended. `git diff --name-only` → `decisions.md`, the two test files,
`mistakes.md`; no `factory/src/**` or `delivery/src/**`.

VERDICT (round 3): pass — one new Minor finding (7), non-blocking.

**(3) `.replace` token — closed, and not collidable in practice.** `:33` holds the token, `:39` does
`.replace("@BLOCKED@", repr(BLOCKED_IMPORTS))`; `grep -c '@BLOCKED@'` = 2 (token + the argument string), the
substituted constant contains no residual token, `compile(T.OFFLINE_GUARD, …)` succeeds, and no `%(`/`%%`
remains anywhere in the file. The ordering (dedent *then* replace) is what makes it indentation-safe, and the
value can never be multi-line — `repr` of a str tuple is one line (measured: 239 chars, no embedded newline)
— so a future name
added to `BLOCKED_IMPORTS` cannot reflow the template. `@` is not legal in any Python identifier, so a
collision requires pasting the literal token into the template; and `.replace` is single-pass, so even a
name containing `@BLOCKED@` would not recurse. Their M8 framing (old form → `TypeError: not enough arguments
for format string` at module import = the #63 loader-error class) matches my round-2 measurement exactly.

**(1) per-call delta — closed, and it cannot be starved by the `loaded` snapshot.** `loaded` at `:90` is
taken *before* the support-module import, so it is a floor, not a ceiling: `set(sys.modules) - loaded`
grows monotonically and every later `foreign()` call sees strictly more. The frozen `added` binding is gone
(`:95`). Reproduced independently: `import PIL.Image` inserted before the *first* `foreign()` (`:109`) →
`rc=1`, and inserted after `reopen_store()` (`:128`) → `rc=1`, both with
`AssertionError: [('PIL', ['…/site-packages/PIL/__init__.py', '…/site-packages/PIL']), ('PIL.ExifTags', …)]`
— I counted the flagged entries at exactly **10**, which is their M6 number.

**(2) realpath and the STDLIB ordering — no false red, but see finding 7.** The name filter at `:96` runs
*before* the location test, and that ordering is load-bearing: a builtin's `spec.origin` is the literal
string `'built-in'` (and `'frozen'` for `importlib._bootstrap`), which `realpath` would rewrite to
`<cwd>/built-in` and reject — so without `:96` every builtin/frozen module would be a guaranteed false
failure. A namespace package is still judged only by its `__path__` (origin `None`), and it passes from an
inner cwd too (measured: pristine child with `cwd=<repo>/factory` → `rc=0`). realpath cannot turn a
genuinely in-repo module into a failure: `REPO_REAL` (`:92`) is itself realpath'd, so alias spellings
collapse onto each other, and an in-repo path that does not traverse an outward symlink stays inside. Their
M7 shows the realpath form is also *strictly better* in the opposite direction (see below), so the fix was
the right call.

Failing closed for a module with neither origin nor `__path__` is the right call for a tripwire — such a
module is by construction unattributable, which is exactly what this check exists to stop on, and
`bad.append((name, locations))` at `:106` already prints both. It is also not reachable from anything the
helper can import today: `grep -n 'sys.modules\[' factory/src delivery/src factory/tests/__init__.py
factory/tests/landing_host_fixture.py` returns nothing, and `__main__` (spec-less under `-c`) predates the
`loaded` baseline.

**(4) their M6/M7/M8 rows are correctly worded.** M6 attributes the gap to the post-import phase and its
number reproduces (10 modules). M7 is worded as the *bypass of the earlier raw-prefix compare* and is
detected by the realpath form — it does **not** claim to reproduce my finding-5 trigger (a symlinked cwd
causing a false red), and I confirm I could not reproduce that one here either; my round-2 evidence for it
remains the `/proc/<pid>/cwd` sys.path probe, correctly labelled as such. M8 is the finding-6 mechanism and
class verbatim. The §4 honesty notes also check out: the three `factory/tests/__pycache__/*.opt-1.pyc` files
they disclose do exist (gitignored bytecode only, no tracked content changed), and `landing_host_fixture.py`
is unchanged as they claim.

### 7. Minor — `foreign()` realpath's the empty sentinel, so a module with no origin and no `__path__` is judged against the child's cwd
`factory/tests/test_landing_backup.py:102` computes `os.path.realpath(getattr(spec, "origin", None) or "")`,
and `os.path.realpath("")` returns the **current working directory**, so the `""` placeholder that the
`if location` filter at `:105` was designed to discard is turned into a real path before the filter sees it.
The consequence is that `foreign()`'s verdict on a spec-less, path-less module now depends on where the run
was launched from — measured with an injected `types.ModuleType("zzspecless")`: `cwd=<repo>` → flagged,
`AssertionError: [('zzspecless', ['<repo>'])]` (the bare root has no trailing separator, so the prefix test
fails); `cwd=<repo>/factory` → `rc=0`, **admitted**, because `<repo>/factory` starts with `<repo>/`;
`cwd=/tmp` → flagged. Not reachable by any legitimate import in this closure (see (2) above), so the
pristine child is green at every cwd I tried — but the tripwire has been converted from deterministic
fail-closed into a cwd-dependent fail-open, which is the wrong direction for the guarantee AC-002 asserts.
Minimal fix: realpath only a real origin, keeping the sentinel empty so `:105` drops it —
`origin = getattr(spec, "origin", None)` then `locations = [os.path.realpath(origin)] if origin else []`.

### Re-run for this round (light, per the in-progress combined verification)

| command | observed |
| --- | --- |
| `… -m unittest …LandingBackupTests.test_offline_test_support_imports_no_web_stack` | `Ran 1 test in 0.236s` / `OK` |
| `PYTHONPATH=.:/factory/src python3 -m unittest factory.tests.test_landing_backup` | `Ran 16 tests in 1.193s` / `OK` |
| `ruff check` on the three files | `All checks passed!` |
| helper byte length / extraction fidelity vs HEAD | 2506 bytes / `IDENTICAL` |

Coverage was re-measured by me rather than borrowed, with the data file kept out of the worktree
(`COVERAGE_FILE=/tmp/l5r3-review-cov`, `PYTHONDONTWRITEBYTECODE=1`):
`landing_backup.py` 249 stmts / 34 missed / **84%** with the missing-line list
`42, 93, 104, 110, 113, 130, 137, 153, 171, 174, 217, 226, 252, 254, 259, 262, 272, 296, 304-319, 323`
(identical to round 1, so the two rounds of test-only edits moved no executed boundary) and
`landing_host_config.py` 47 stmts / 7 missed / **80%** (`25, 31, 33, 39, 55, 58, 83`) — both parent numbers
confirmed, nothing owed. The worktree's pre-existing gitignored `.coverage` (dated 04:15, before this round)
was not written by this run and was left untouched; `git status --short` afterwards is unchanged.
`PYTHONDONTWRITEBYTECODE=1` was used for every run above. Handoff
notes still standing: the untracked `factory/tests/landing_host_fixture.py` must land in the same commit, and
finding 7 is the only new code change I would ask for before merge.

## Round 4 — confirmation of the finding-7 hunk only

Hunk under review: `factory/tests/test_landing_backup.py:100-107` (comment `:100-102`,
`origin`/`locations` at `:103-104`, the `__path__` comprehension at `:105-106`, the containment test at
`:107`). The edit is confined to this file —
`git diff --numstat` = +93/−15 (was +91/−15), 355 lines (was 353) — and
`landing_host_fixture.py`/`test_landing_host.py`/`factory/src/**`/`delivery/src/**` are untouched, so every
earlier verdict stands. `ruff check factory/tests/test_landing_backup.py` → `All checks passed!`.

VERDICT (round 4): pass — finding 7 closed; one new Minor (8), latent and non-blocking.

**(a) Finding 7 is closed, and closed cwd-independently.** My own matrix, re-running the guard child
verbatim with an injected `types.ModuleType("zzspecless")` (`__spec__` None, no `__path__`):
`cwd=<repo>` → `FLAGGED: AssertionError: [('zzspecless', [])]`; `cwd=<repo>/factory` → `FLAGGED` (round 3
gave `rc=0`/admitted here, which *was* the finding); `cwd=/tmp` → `FLAGGED`. The reported `locations` is now
`[]` rather than a cwd path, i.e. an unattributable module reads as unattributable. Control child stays green
at all three cwds, and the real suite is cwd-independent:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:/factory/src python3 -m unittest factory.tests.test_landing_backup`
→ `Ran 16 tests in 1.074s / OK` from `<repo>` and `Ran 16 tests in 1.104s / OK` from `<repo>/factory`
(matching the parent's `1.012s`). Their `os.path.realpath('')` → `'<repo>'` mechanism note is exact
(measured the same).

**(b) The `if location` filter at `:107` is now structurally dead.** After the fix `locations` can only ever
be built from `os.path.realpath(...)`, and `realpath` never returns `''` (measured: `realpath('')` → the cwd,
`realpath('anything')` → non-empty), so no element can be falsy and the filter drops nothing. Harmless, but
it is the reason the next case slips through: an empty `__path__` entry is realpath'd *into* the cwd before
the filter can see it.

**(c) Yes, one fail-open path of the same class remains — finding 8.** Two inputs still resolve against the
cwd: an empty `__path__` entry, and any **non-absolute** `origin` (importlib sentinels `'built-in'`,
`'frozen'`, `'unknown'`, or a relative path). Measured with the same child: `__path__ == [""]` →
`ADMITTED (green)` at `cwd=<repo>/factory` but `FLAGGED: [('zzemptypath', ['<repo>'])]` / `[('/tmp')]` at the
other two cwds; and a module built via `importlib.machinery.ModuleSpec(...)` with `origin = "built-in"` →
`ADMITTED (green)` at `cwd=<repo>` **and** `<repo>/factory`, `FLAGGED: [('zzsent', ['/tmp/built-in'])]` at
`/tmp`. So the verdict for such a module is still a function of where the run was launched.
Reachability today: none. Real in-repo and third-party modules always carry an absolute `origin`
(`FileFinder` abspaths each `sys.path` entry, so even a relative `PYTHONPATH` element or `''` at
`sys.path[0]` yields absolute origins), namespace portions are absolute for the same reason, and the only
sentinel origins belong to builtins/frozen modules whose top-level name is caught by the `STDLIB` filter at
`:96` before the location test — which is why I rate this Minor rather than Major: it needs a custom or
frozen-style loader reporting a bare sentinel, or a hand-mutated `__path__`, neither of which the helper's
import closure can produce.
Minimal fix, symmetric to theirs and cwd-independent by construction — test the candidate *before* realpath:
`locations = [os.path.realpath(origin)] if origin and os.path.isabs(origin) else []` and
`... for entry in (getattr(module, "__path__", None) or []) if str(entry)` (which also revives the `:107`
filter or makes it safely removable). Taking it or recording it as accepted debt are both defensible; I would
not block the receipt on it.

**(d) Nothing else in `foreign()` is cwd-sensitive.** `REPO_REAL` (`:92`) is derived from
`Path(__file__).resolve()` and realpath'd, so alias/symlink spellings of the repo collapse onto it (round-2
finding 5's false red is gone, and their M7 shows the outward-symlink bypass is gone too); the `loaded`
baseline at `:90` is cwd-independent; `STDLIB`/`crossed()` are pure name tests; and `child_env` removes the
one interpreter knob that could change the child's semantics. Confirmed by the pristine control being green
from three different cwds.

**(e) Review-current for fingerprint-bound receipts: yes, with two conditions.** Conditions: (1) bind the
receipt to the tree *after* the in-progress combined verification finishes — `find . -newermt
'2026-09-14 05:20' -not -path './engineering/*' -not -path './.git/*'` shows nothing written by a reviewer run
outside the evidence directory (no new `__pycache__` entries, and the pre-existing `.coverage` is still dated
04:15, not rewritten by this round's `COVERAGE_FILE=/tmp/l5r3-review-cov`); the only post-05:20 touches are
the parent's own `decisions.md`/`mistakes.md` logging, and per AGENTS.md any further repo edit re-stamps
local evidence; (2) `factory/tests/landing_host_fixture.py` is still untracked — a fingerprint taken without
it would certify a tree that cannot import, so it must be staged/committed in the same change before
`python3 scripts/grok_verify.py --mode pr` records the receipt. Findings 1–7 are all verified closed in code
and by measurement; finding 8 is the only open item, latent.

## Round 5 — disposition of the finding-8 hunk (bounded; nothing else re-audited)

Hunk: `factory/tests/test_landing_backup.py:100-109` — rationale comment `:100-103`, `origin` `:104`,
isabs-gated origin location `:105`, `__path__` comprehension with `if str(entry) and
os.path.isabs(str(entry))` `:106-108`, containment test with the dead `if location` filter removed `:109`.
Edit confined to this file (`git diff --numstat` +95/−15, 357 lines); helper, host suite and both `src` trees
untouched, so all earlier verdicts carry. `ruff check factory/tests/test_landing_backup.py` → clean.

VERDICT (round 5): **pass — finding 8 closed, hunk is clean, review complete.**

**(1) Finding 8 is closed, and I reproduced the matrix independently.** Six non-attributable inputs injected
into the guard child, each at `cwd=<repo>`, `<repo>/factory`, `<repo>/factory/tests`:
`__path__=[""]`, `__path__=["factory"]` (relative), `origin="built-in"`, `"frozen"`, `"unknown"`,
spec-less+path-less → **FLAGGED in all 18 cells**, now reporting the honest empty location set
(`AssertionError: [('zza', []), ('zzb', []), ('zzc', []), ('zzd', []), ('zze', []), ('zzf', [])]`, identical
at every cwd — two of these were cwd-dependent in round 4). Positive control in the same harness — an
in-repo absolute `__path__` entry → `admitted` at all three cwds, so the gate does not over-reach.

**(2) No cwd-sensitive or fail-open path is left in `foreign()`.** Every element of `locations` is now
`realpath(non-empty absolute)`, hence non-empty and derived from a path that cannot be redirected by the cwd;
an empty `locations` makes `not any(...)` true, so unattributable modules fail closed deterministically;
the only other path input, `REPO_REAL` (`:92`), comes from `Path(__file__).resolve()` passed as `argv[1]`,
and `loaded`/`STDLIB`/`crossed()` are pure name tests. Control is green across the configurations that could
plausibly break it, including the sharpest stress of the new gate — a **relative** `PYTHONPATH`, which must
still yield absolute origins: guard test `OK` from `cwd=<repo>` with `PYTHONPATH=.:/factory/src` and with
`PYTHONPATH=.:factory/src`, from `<repo>/factory` with `PYTHONPATH=..:../factory/src`, and from
`<repo>/factory/tests`; `factory.tests.test_landing_backup` → `Ran 16 tests in 0.970s / OK`. The false-red
test with the entire web/db stack importable also reproduces: on the release venv (fastapi 0.128.2, starlette
0.50.0, httpx 0.28.1, psycopg 3.3.4, uvicorn 0.48.0, pypdf 6.18.1)
`factory.tests.test_landing_backup factory.tests.test_landing_host` → `Ran 52 tests in 1.977s / OK`.
One asymmetry worth recording but **not** a defect: a non-`str` `__path__` entry would stringify to
`"b'…'"`, fail `isabs`, be dropped, and thus be *flagged* — that direction stops the run rather than
admitting a module, and CPython only yields `str` path entries, so it is unreachable.

**(3) The tree is review-current for fingerprint-bound receipts**, with the same two mechanical conditions as
round 4 (they are not code findings): stamp the receipt only after the in-progress combined pass finishes, and
stage `factory/tests/landing_host_fixture.py` in the same commit before the fingerprint is taken — a receipt
over a tree missing the helper would certify a state that cannot import. All eight findings across five
rounds are now closed in code and each was confirmed by measurement.

**(4) On your transparency note — yes, I consider that disposition acceptable, and it is mine to state.** If a
later round surfaces another latent, unreachable-by-construction nit of this class, recording it as accepted
debt in `tasks.md` rather than extending the loop is the right call for this change, because every remaining
variant I can construct requires a caller to *fabricate* a `sys.modules` entry or run under a frozen/custom
loader, and the two guarantees AC-002 actually names — the web/db blocklist and the fixture-behaviour
assertions — are enforced by cwd-free, `-O`-proof mechanisms. For the debt entry to stay honest it must record
three things: the predicate it concerns (`foreign()`'s location containment), the exact reachability
precondition that makes it latent (no real importer produces a relative or sentinel `origin`, nor a
non-`str`/empty `__path__` entry), and the one-line shape of the fix — then it is re-derivable by the next
reviewer instead of being mistaken for a live hole. I would not ask for a further round on that class, and I
would not treat its absence from the code as a reason to withhold the receipt. Closing the review here.
