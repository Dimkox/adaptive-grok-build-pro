# Measured execution evidence — before / after (SIG-001, SIG-002)

Host: python 3.12.3, **no** `fastapi`, `uvicorn`, `psycopg` or `pypdf` installed (`httpx` is present, so the
offline guarantee is enforced by the subprocess meta-path guard, not by absence). Commands run from the
worktree root; `PYTHONPATH=.:factory/src:delivery/src` for the coverage runs.

## 1. Collectability of the offline boundary suite (SIG-001)

| | command | result |
| --- | --- | --- |
| before | `python3 -m unittest factory.tests.test_landing_backup` | `Ran 1 test ... FAILED (errors=1)` — `ModuleNotFoundError: No module named 'fastapi'`, **0** boundary tests executed |
| after | `python3 -m unittest factory.tests.test_landing_backup` | `Ran 16 tests in 1.081s` / `OK` — **0** loader errors |

## 2. Per-module coverage of the L5 runtime (SIG-002)

Three bases, each measured in this session with
`COVERAGE_FILE=<scratch> coverage run --source=factory/src/adaptive_factory …` then
`coverage report -m` (no coverage data written into the repository):

- **A — before, whole-suite basis:** `git archive HEAD` exported to a clean scratch tree, then
  `unittest discover -s factory/tests -t .` (the state a reviewer reproduces from `main`).
- **B — after, single-suite basis:** this tree, `unittest factory.tests.test_landing_backup` alone —
  what this suite by itself now reaches.
- **C — after, whole-suite basis:** this tree, `unittest discover -s factory/tests -t .` — comparable to A.

| module | A: before, whole suite | B: after, this suite only | C: after, whole suite |
| --- | --- | --- | --- |
| `landing_backup.py` (249 stmts) | **12%** (210 missed) | **84%** (34 missed) | **84%** (34 missed) |
| `landing_host_config.py` (47 stmts) | **22%** (32 missed) | **80%** (7 missed) | **80%** (7 missed) |
| `landing_sqlite_store.py` (329 stmts) | 82% (45 missed) | 44% (167 missed) | 83% (39 missed) |
| `landing_artifact_retention.py` (136 stmts) | 80% (18 missed) | 24% (93 missed) | 80% (18 missed) |

The headline is A→C: the destructive-boundary module goes 12%→84% and its config loader 22%→80% on the
whole-suite basis, while `landing_sqlite_store.py` and `landing_artifact_retention.py` are unchanged
(82→83%, 80→80%) because other suites already reached them. Column B is lower for those two modules
**by construction** — a single suite reaches less than the whole run — and an earlier revision of this file
presented B's 44%/24% as the "before" values, which was wrong. The `test_review` round caught it
(see `test-review.md` F-1); the table above is re-measured, not inherited.

Uncovered `landing_backup.py` lines after the change (34): 42, 93, 104, 110, 113, 130, 137, 153, 171, 174,
217, 226, 252, 254, 259, 262, 272, 296, 304-319, 323 — the argparse/CLI entry (`adaptive-landing-state`,
`factory/pyproject.toml:16`) and the residual `__main__` plumbing, which is the follow-up slice named in
issue #63 requirement 2, not a regression here.

## 3. Whole-executed-suite effect

| | `python3 -m unittest discover -s factory/tests -t .` |
| --- | --- |
| before (main) | `Ran 415 tests ... FAILED (errors=37, skipped=7)` |
| after (this tree) | `Ran 430 tests ... FAILED (errors=36, skipped=7)` |

Exactly **+15 executed tests and −1 loader error**; no error names a file touched by this change.

Re-measured on the final tree (`2026-09-14`, this worktree): `Ran 430 tests in 22.374s /
FAILED (errors=36, skipped=7)`. The 36 errors decompose by raised exception as **22 `psycopg` +
11 `fastapi` + 3 `uvicorn`** = 36, so every remaining error is a pre-existing dependency gap (#57), not a
subtest failure. 14 of them are module-level loader errors: `test_api`, `test_execution_persistence_postgres`,
`test_landing_api`, `test_landing_host`, `test_landing_server`, `test_models`, `test_openapi_contract`,
`test_postgres_integration`, `test_semantic_persistence`, `test_semantic_repair_lifecycle`,
`test_semantic_service_api`, `test_semantic_store_runtime`, `test_server`, `test_workspace`.
`test_landing_backup` is no longer in that set, which is the point of the change; `test_landing_host` still is,
because it legitimately imports `fastapi.testclient` for `build_app`.

### Focused checks on the final tree (re-measured after every review round)

| command | result |
| --- | --- |
| `python3 -m unittest factory.tests.test_landing_backup -v` | `Ran 16 tests in 1.231s` / `OK` |
| `… coverage report` on that run | `landing_backup.py` 249/34 **84%**, `landing_host_config.py` 47/7 **80%**, missing-line lists verbatim as §2 column C |
| `python3 -m unittest factory.tests.test_landing_publication_cli factory.tests.test_landing_sse` | `Ran 50 tests in 6.103s` / `OK` |
| `python3 -m unittest tests.test_landing_architecture_boundaries tests.test_change_spec tests.test_architecture_fitness` | `Ran 135 tests in 71.195s` / `OK` |
| `python3 -m unittest discover -s tests` (root suite, no coverage) | `Ran 654 tests in 359.004s` / `OK` |
| `python3 -m unittest discover -s factory/tests -t .` | `Ran 430 tests in 22.918s` / `FAILED (errors=36, skipped=7)` |
| `ruff check` on the three touched files | `All checks passed!` |
| `bandit -c bandit.yaml -r` on the two new/changed test files | clean, exit 0 |
| deps-complete interpreter: `factory.tests.test_landing_backup factory.tests.test_landing_host` | `Ran 52 tests in 2.029s` / `OK` |

The last row is the false-red control for the hardened guard: it runs the offline suite and the real-FastAPI
host suite together where the entire web stack is importable, so a containment rule that over-matched would
fail there rather than here. All rows above were re-measured after the round-4/5 finding-8 fix.

## 4. Guard is not vacuous (mutation log)

Mutations were applied only to scratch copies (`/tmp/l5mut-*`, `/tmp/l5r3-*` via `cp -a factory`; note
`landing_backup` also imports `adaptive_delivery`, so `delivery/` must be copied alongside it or 15 of the 16
tests error for a purely environmental reason that is not a defect). No repository file was modified by a
mutation. Each case runs only `test_offline_test_support_imports_no_web_stack`.

| # | mutation (`landing_host_fixture.py` unless noted) | expected | observed |
| --- | --- | --- | --- |
| M0 | none — control, with the stub directory on the **parent's** path | pass | `Ran 1 test … OK` |
| M1 | `import starlette` (web-stack under a name the old list lacked) | fail loudly | `AssertionError: offline import reached starlette` |
| M2 | `import PIL` (third-party, on **no** blocklist) | fail loudly | `AssertionError: [('PIL', […/site-packages/PIL/__init__.py, …]), ('PIL._version', […])]` |
| M3 | `target.chmod(0o600)` removed, run with `PYTHONOPTIMIZE=1` | fail (not silently pass) | `FAILED (errors=1)` |
| M4 | `publication_state_path` dropped from `ROOT_FIELDS` | fail | `FAILED (errors=1)` |
| M5 | `from fastapi.testclient import TestClient` re-added | fail loudly | `FAILED (failures=1)` — `offline import reached fastapi` |
| M6 | child program: `import PIL.Image` **after** the helper import | fail (round-3 fix) | `AssertionError` listing 10 `PIL.*` modules resolved from site-packages |
| M7 | in-repo symlink `evadepkg → ~/.local/…/site-packages/PIL`, imported by the child | must not pass | with `realpath`: `FAILED` on `[('evadepkg', […/site-packages/PIL/__init__.py, …])]`; with the earlier raw-prefix compare: **`OK`** — containment was bypassable |
| M8 | a literal `%` added inside the guard template (test file) | must not break collection | old `%`-formatting: `TypeError: not enough arguments for format string` at **module import** — exactly the #63 loader-error class; `.replace()`: imports fine |
| M9 | an injected module with no `__spec__` and no `__path__`, evaluated at three working directories | must fail closed identically | pre-fix-7 (`realpath(origin or "")`): `FLAGGED` at `<repo>` and `/tmp` but **`admitted` at `<repo>/factory`** — cwd-dependent fail-open, because `os.path.realpath("")` *is* the cwd; post-fix: `FLAGGED` at all three, and the control suite `Ran 16 … OK` from both `<repo>` and `<repo>/factory` |
| M10 | six non-locatable inputs (`__path__=[""]`, relative `__path__=["factory"]`, `origin` of `"built-in"`/`"frozen"`/`"unknown"`, spec-less+path-less) × three working directories | every cell fails closed, no legitimate in-repo module fails open the other way | pre-fix-8: two cells were cwd-dependent (`__path__=[""]` admitted at `<repo>/factory`; sentinel origins admitted at `<repo>` and `<repo>/factory`); post-fix: **FLAGGED in all 18 cells**, an in-repo absolute `__path__` entry still `admitted`, the guard green from `<repo>`, `<repo>/factory` and `<repo>/factory/tests`, and on the deps-complete interpreter `test_landing_backup` + `test_landing_host` → `Ran 52 tests … OK` (no false red with the whole web stack importable) |

Two reproduction notes. The guard fires when a blocked name is *requested*, so M1 and M5 need no installed
`starlette`/`fastapi` in the child — but they do need the mutant importable by the **parent**, because the
parent imports `landing_host_fixture` during collection and would otherwise die with `ModuleNotFoundError`
before the child runs (hence the stub directory on the parent's path; M2 needed no stub — Pillow is genuinely
installed on this host, which makes it the stronger case). And M3/M4 abort in the parent `setUp` before the
child runs (the private-mode and root-existence contracts are also enforced by `load_host_config`), so they
prove the property is enforced loudly but not the child-side assertion specifically. The `-O` exposure is
therefore measured directly instead: with a parent at
`sys.flags.optimize == 1`, the old `env={**os.environ, …}` child reported `optimize: 1`, `rc=0`,
`asserts stripped: True`; the child built by `child_env()` reports `optimize: 0`, `rc=1`,
`AssertionError raised: True`. Those `-O` comparisons ran in the worktree itself (not a copy), which is why
three `*.opt-1.pyc` files sit in `factory/tests/__pycache__/`: gitignored bytecode caches, no tracked content
changed, and `landing_host_fixture.py` remains byte-identical to the reviewers' round-1 snapshot.

## 5. Review rounds applied to this change

Round 1: `code-review.md` pass with 3 Minor, `test-review.md` **fail** on one evidence defect. Round 2: code
review pass with 3 further Minor — each of which was introduced by the round-1 fixes — and test review
**pass**, with all 12 §2 percentages reproduced independently. Rounds 3–5: the reviewer kept auditing the
repair code itself, finding one new Minor each time (a dead second assertion, then a cwd-dependent fail-open
introduced by the realpath hardening, then two more inputs of the same class), confirming each fix in the
next round. Every finding below is closed in code and pinned by its own mutation.

- code-review 1 (two drifting copies of the blocklist) → one module-level `BLOCKED_IMPORTS`, interpolated
  into both child programs via `OFFLINE_GUARD`.
- code-review 2 (`PYTHONOPTIMIZE` silently strips child asserts) → `child_env()` drops it; measured above.
- code-review 3 (blocklist missed `starlette`/`psycopg2`) → both added (M1 proves the entry bites).
- test-review F-1 (false "before" percentages in §2) → §2 re-measured on three explicit bases (A/B/C).
- test-review F-2 (0700 assertion iterated the fixture's own tuple) → root names pinned literally (M4).
- test-review F-3 (name-only denylist cannot see other third-party packages) → `foreign()` location rule:
  every module the helper import loads must resolve to the stdlib or inside the repository (M2). Its known
  boundary is stated, not hidden: a *vendored* in-repo third-party package is invisible to it by design,
  because the enforced invariant is "no external web/db stack", not "no third-party code at all".
- test-review F-4 (AC-003 rested on static proof because the host suite cannot run here) → resolved
  by execution in §7: the whole factory suite runs green on a deps-complete interpreter, on both trees.
- code-review 4 (the second `assert foreign()` was dead code — `added` was a frozen snapshot) → `foreign()`
  recomputes `set(sys.modules) - loaded` on each call, so the post-`setUp` assertion is live. This also
  closes test-review N-1 (a third-party import deferred inside a method escaped the guard): measured M6.
- code-review 5 (containment compared raw strings) → `os.path.realpath` on both sides. Their trigger was a
  symlinked checkout going **red**, which I could not reproduce (green either way here); what I did reproduce
  is the opposite and worse direction — a false **green** via an in-repo symlink into site-packages (M7).
- code-review 6 (`%`-formatted guard template can break at import) → `.replace("@BLOCKED@", …)` (M8).
- code-review 7 (the realpath fix itself turned deterministic fail-closed into cwd-dependent fail-open,
  because `realpath("")` is the working directory) → an absent origin now contributes no location at all, so
  such a module is flagged identically from every directory (M9). Found by the reviewer in round 3, in the
  code the round-2 fix introduced.
- code-review 8 (round 4: two inputs still reached `realpath` unresolved — an empty or relative `__path__`
  entry, and any non-absolute `origin` such as `"built-in"`/`"frozen"`/`"unknown"`, which real `FileFinder`
  output never produces) → `os.path.isabs()` gates both sides before `realpath`, the structurally dead
  `if location` filter is removed, and the whole predicate is now cwd-independent by construction (M10:
  18/18 cells fail closed, legitimate in-repo paths unaffected, and 52 tests `OK` on the deps-complete
  interpreter). Taken rather than booked as debt, because it is the same defect class as 7.

## 6. What is still not executed (unchanged by this change)

`landing_host.py` 9%, `landing_server.py` 21%, `landing_publication_cli.py` 46%, `landing_media.py` 74%,
`landing_pdf_worker.py` 0% (child-interpreter execution plus `skipUnless` on pinned `pypdf` 6.18.1).
16 of `landing_backup.py`'s 34 remaining uncovered statements are the shipped `adaptive-landing-state`
console-script entry (`factory/pyproject.toml:16` → `landing_backup:main`), so the operator CLI path is
still never executed. `.coveragerc` `fail_under = 74` measures only `.grok-stack/adaptive_grok` + `scripts`,
so none of these numbers gates anything yet — enforcement is issue #63 requirement 2 / #51
`factory-unittest-all`, kept out of scope by FORBID-003.

**AC-003 is certified by execution, not static proof — see §7.** The percentages in this section belong to
the dependency-incomplete local environment (the one `python3` here provides, and the one the recorded
coverage numbers were taken in); §7 shows the same tree fully green where the pinned deps exist.

## 7. Deps-complete environment: the web-stack half really runs, and is unchanged

This host has no web/db packages in its system `python3`, but the installed L5 release ships a complete
virtualenv. It was used **read-only as an interpreter**: nothing was installed into it and no coverage data
was written into the repository, verified afterwards by
`find /opt/adaptive-l5 -maxdepth 4 -newermt '-40 minutes' -printf '%TT %p\n'` returning no entries. For
orientation: the release directory is dated 03:24 UTC (when PR #82 was deployed) and
`adaptive-l5.service` has been active since 03:25 UTC — neither was altered by these runs.

```
/opt/adaptive-l5/releases/5f6f6ce1ecb0cef8e1b3910b037af983c5fb8f8a/venv/bin/python  →  Python 3.12.3
  fastapi 0.128.2 · httpx 0.28.1 · psycopg 3.3.4 (+binary) · pypdf 6.18.1 · uvicorn 0.48.0 — coverage is
  NOT installed there
```

The five web/db versions above match their `factory/uv.lock` pins exactly (`factory/uv.lock:76-77`, `114-115`,
`138-139`, `324-325`, `376-377`), so this is not an arbitrary interpreter with "some" web stack — and
`PYTHONPATH=.:factory/src:delivery/src` means the **source under review** ran, not the release's installed
copies (resolution confirmed: `adaptive_factory` and `factory.tests.test_landing_host` come from the worktree,
`fastapi` from the venv). Two honest limits on using it as evidence: the venv is not lock-exact across all 21
entries (`anyio` is 4.15.1 there against the 4.14.2 pin at `factory/uv.lock:45-46`; `tzdata` is correctly
absent behind its `sys_platform == "win32"` marker at `:143`), and it is host state that a clean checkout
cannot reproduce. So §7 is **corroboration** of §2/§3, not a substitute for them — and it is deps-complete,
not DB-complete: of the 144 skips I counted on this tree, 143 are `FACTORY_TEST_DATABASE_URL` /
`FACTORY_FRESH_CLUSTER_DATABASE_URL` gates and 1 is `PdfWorkerWithoutParser` (skipped precisely *because*
pinned pypdf is present: `'pinned pypdf 6.18.1 present; unavailable branch cannot run'`), giving
**569 executed + 144 skipped = 713**.

| command (`PYTHONPATH=.:factory/src:delivery/src <venv>/bin/python -m unittest …`) | base tree (`git archive HEAD`) | this tree |
| --- | --- | --- |
| `factory.tests.test_landing_host` | `Ran 36 tests in 0.899s` / `OK` | `Ran 36 tests in 0.870s` / `OK` |
| `factory.tests.test_landing_pdf_worker` | — | `Ran 8 tests in 0.999s` / `OK (skipped=1)` |
| `discover -s factory/tests -t .` | `Ran 712 tests … OK (skipped=144)` | `Ran 713 tests … OK (skipped=144)` |

Two things follow. First, AC-003 holds under execution: the 36 real-FastAPI host tests pass identically
before and after the fixture extraction, on an interpreter where they actually run — so the subclassed
`HostFixture` really is behavior-preserving, not merely textually identical. Second, **+1 test and zero
outcome changes** in the whole deps-complete suite, which is the expected signature of adding exactly one
test method — the reviewers' per-test-id diff showed exactly one added id,
`test_offline_test_support_imports_no_web_stack`, and an empty diff of the host suite's 36 test names.
Nothing outside `test_landing_host.py` and `test_landing_backup.py` consumes the moved symbols: the search
for an external importer of the old fixture path returns zero hits, and `HostFixture`/`ROOT_FIELDS`/
`PATH_FIELDS` appear only in those two suites plus the new helper (the unrelated `RULE_PATH_FIELDS` in
`architecture.py` is a different thing).

The `Ran 415 → 430` / `errors=37 → 36` figures in §3 and every percentage in §2 are measured in the
dependency-incomplete environment, because that is what `python3` and the recorded gate run provide here;
they are not claimable in this environment, since `coverage` is absent from the release venv and installing
it would mutate installed state.
