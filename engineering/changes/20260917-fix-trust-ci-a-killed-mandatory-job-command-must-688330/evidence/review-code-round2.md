# Independent code review, round 2 — issue #103 (interrupted Trust CI commands)

PASS

Round-1 findings F1/F2/F4 and test-review G-1/G-2/G-3/G-4 are all genuinely closed, each re-proven by
execution. One new, documentation-only finding (R2-1, non-blocking). No product file was edited by this review.

**Snapshot pinned and re-verified stable:** `sandbox.py b46520ff…`, `runner.py d1089aac…`, `api.py 01219f9d…`,
`test_ops.py 633db2b6…`, `test_runner.py 84b1f30d…`, `test_api.py 464fab12…`; `md5sum -c` OK at 05:15:37 UTC.
Caveat for the receipt step: at ~05:09 UTC `sandbox.py` transiently read as `4b63a994…` — a version **without**
the classifier guard, i.e. round-1 bytes — and my first mutation batch measured that (spuriously failing) copy.
The tree then returned to `b46520ff…` and has not moved. All numbers below come from a re-taken copy verified
against the md5s above, so re-check these md5s before binding any receipt.

## 1. Totality moved into the classifier (G-1/F4) — consequences measured, not read

`sandbox.py:84-85` (`isinstance(exit_code, bool) or not isinstance(exit_code, int) → return None`),
`exit_code: Any`. Only two `CommandAbort(...)` construction sites exist in the whole tree, both inside that
guarded function (`:93`, `:95`). Measured over `137.0, 143.5, -9.0, 128.0, 124.0, nan, 1e30, None, '137', '',
[], {}, object(), True, False`: **every one returns `None`, none raises**. Fuzzing `-300..300` plus `±10**20`
across both marker/no-marker branches, `to_result()['signal_number']` types seen = `{int, NoneType}` and
`exit_code` = `{int}` only, and the dict JSON-serialises clean. So the round-1 defect (`137.0` →
`signal_number: 9.0` into `result.abort`; `None`/`'137'` → `TypeError`) is gone, and **no path can put a
non-int into the stored member**.

End-to-end through `_attested_command_abort` with `[None, '137', 137.0, True, 137]`: malformed rows are skipped
and the loop is not blinded — it returns `{'exit_code': 137, 'signal_number': 9, …}`, all int/str.
`_public_result` redaction still holds (`api.py` unchanged since round 1): given a result carrying `abort` plus
command tails `SECRET`/`KILLED BY OOM`, the projection keys are `['abort','attestation','commands']` and the
serialised response contains neither `stdout_tail` nor either tail string.

The runner check at `:272-274` is now described as a second layer, and that framing is honest: **MU6 (delete
runner guard) survives green**, exactly as `test-plan.md:34` claims.

## 2. G-2 — `_terminal_failure_code('passed', …) is None`

Measured `_terminal_failure_code('passed', None) = None`, `('passed', <live abort>) = None`,
`('failed', None) = 'verification-failed'`, `('failed', abort) = 'aborted-by-signal'`. **MU11 (delete
`if status == 'passed': return None`) is now KILLED** — independently reproduced:
`FAILED (failures=2, skipped=10)`, attributed to exactly `test_passed_job_records_no_failure_code_at_all` and
`test_signed_attestation_is_replayed_after_check_publication_failure`, the two tests named in the plan. The
status vocabulary itself is unchanged from round 1 (both `store.finish` guards, frozen `status IN (…)` CHECK).

## 3. G-4 — the `\Z` anchor, and the equivalence argument

**MU4 (delete `\s*\Z`) → KILLED (failures=1)** by `test_timeout_marker_must_end_the_stored_tail`, which also
pins marker-first/mid-tail → no claim and marker+trailing whitespace → still `timeout`.
The "`\Z`→`$` is equivalent, not chased" claim is **sound, not a rationalization**, and I measured why: a
12-case differential (bare marker, `+'\n'`, `+'\n\n'`, `' \n'`, `'\t'`, `' \r\n'`, mid-string, `+'X'`, …) gave
**0 divergences** between the two anchors, because `\s*` can absorb exactly the trailing newline `$` would allow.
Mutants confirm the dependency is real and covered: `MU4b` (`\Z`→`$`, `\s*` kept) → **survives** (genuinely
equivalent); `MU4c` (`\Z`→`$` with `\s*` dropped) → **KILLED**; `MU4d` (delete only `\s*`) → **KILLED (failures=2)**.
So the premise is itself pinned — nobody has to re-derive it later.

Bonus range checks: `MU12` (`_MAX_SIGNAL_NUMBER 64→63`) → **KILLED** by `test_signal_range_boundaries_are_pinned`
(G-3 really closed); `MU13` (`_SIGNAL_BASE <` → `>=`, i.e. 128 becomes signal 0) → **KILLED (failures=16)**;
`MU14` (collapse the `failure_code` ternary) → **KILLED (failures=3)**.

## 4. F1 — the migration citation is now checkable, and correct in substance

Ran every proof the new text offers: `ls trust-ci/sql/ | wc -l` → **3**;
`ls trust-ci/src/adaptive_trust_ci/resources/*.sql | wc -l` → **3**; `git diff --name-only 2f66ba6 -- '*.sql'` →
**empty**; `ls factory/src/adaptive_factory/resources/*.sql | wc -l` → **20**, ending
`020_execution_v2_priced_usage.sql`. `change-spec.yaml:6,99`, `requirements.md:14` (`INV-002`), `release.md:15-22`
and `state.json`'s correction row all carry the measured form, and the package no longer claims
`trust-ci/sql/001-018`. Repo-wide sweep for `001-018`: remaining hits are `README.md:32`, `START_HERE.md:57`,
`CHANGELOG.md:75`, `PROJECT_STATE.json:261,352` and other change packages — all correctly the factory/PostgreSQL
set (`20260911-…/evidence/analysis-repo_explorer.md:22` even documents that `migrations.py` requires a contiguous
set and "currently 019" as the next number). One attribution slip survives — see R2-1.

## 5. F2 and F3 — wording present as claimed

`release.md:41-48` now reads "`aborted-by-signal` means **the command reached no verdict**, not 'this is not a
code problem'", keeps "Who sent the signal is not in the record", and names the triage path explicitly:
`result.abort.signal` + container/daemon logs + duration, with a kernel `SIGKILL` from the PR's own tests
exhausting sandbox memory called "a defect in the pull request that must be fixed, not re-gated away". Grep for
the contradicted phrasing returns only (a) that negating sentence and (b) my round-1 file quoting it — clean.
F3's asymmetry is disclosed in all three named places: `requirements.md:25`, `architecture.md:36`,
`test-plan.md:65-67`. `architecture.md:94-102` states the F4 correction as explicitly as the measurements
support, including "the runner-level claim 'the bool check protects the classifier' is deliberately **not** made".
`mistakes.md` gained two entries (caller-side guard described as a function property; widening a schema-capped
typed field) consistent with what I re-measured.

## 6. Re-executed on the final bytes (verbatim)

```
$ PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests 2>&1 | tail -4
----------------------------------------------------------------------
Ran 268 tests in 7.146s

OK (skipped=10)

$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest test_ops test_runner test_api 2>&1 | tail -4
----------------------------------------------------------------------
Ran 86 tests in 1.048s

OK

$ python3 -m ruff check <six changed .py files>
All checks passed!

$ git status --porcelain
 M decisions.md
 M mistakes.md
 M trust-ci/src/adaptive_trust_ci/api.py
 M trust-ci/src/adaptive_trust_ci/runner.py
 M trust-ci/src/adaptive_trust_ci/sandbox.py
 M trust-ci/tests/test_api.py
 M trust-ci/tests/test_ops.py
 M trust-ci/tests/test_runner.py
?? engineering/changes/20260917-fix-trust-ci-a-killed-mandatory-job-command-must-688330/
```

268 vs. round 1's 263 = the 5 new tests. Exactly the expected files, now including `mistakes.md`; still no
`.sql`, migration, `.github/`, config, systemd or identity file. Mutation copies were made under `/tmp` and
destroyed; the real tree's md5s were re-checked after every batch.

## Findings

- **R2-1 (non-blocking, documentation) — the corrected citation misattributes its own source.**
  `requirements.md:14` ("the `AGENTS.md` "001-018" numbering"), `change-spec.yaml:99` ("the AGENTS.md 001-018
  numbering") and `tasks.md:51` ("that factory set is what the `AGENTS.md` numbering names") attribute `001-018`
  to `AGENTS.md`. Measured: `grep -n "018" AGENTS.md` → **no match**; `AGENTS.md:130-131` speaks only of
  "versioned migrations" in general. The string lives in `PROJECT_STATE.json:261,352` (`"postgresql_migrations":
  "001-018"`), `README.md:32`, `START_HERE.md:57`, `CHANGELOG.md:75` — and `release.md:19` says
  "`AGENTS.md`/`START_HERE.md`", half-right. The substance is verified true and nothing about the code changes,
  but `tasks.md:47` claims the citation was "replaced everywhere", and this is the same one-grep-refutes class
  as issue #117 / round-1 F1. Point it at `PROJECT_STATE.json`/`START_HERE.md`.
- **R2-2 (non-blocking, hardening note) — totality covers `exit_code`, not `stderr_tail`.**
  `classify_command_abort(exit_code=124, stderr_tail=None)` still raises
  `TypeError: expected string or bytes-like object` (measured; `exit_code=137, stderr_tail=None` is fine because
  the `and` short-circuits). Unreachable today — `_attested_command_abort` hardcodes `''` and every live
  `CommandResult` tail is a `str` (`sandbox.py:_command_result`, `runner.py:468/485/635`) — but the new
  `mistakes.md` rule ("put the enforcement at that function's own boundary") argues for the same one-line
  treatment of the second recovered-JSON-looking parameter if the replay path ever starts reading stored output.

## Verified by execution (re-run here, on the pinned bytes)

Full suite and focused modules; `ruff` via `python3 -m ruff`; classifier fuzz over 16 non-int objects and
`-300..300 ±10**20` for member types; malformed-row replay through `_attested_command_abort`; `_public_result`
redaction with planted secrets; `_terminal_failure_code` 4-cell truth table; 10 mutants (MU4, MU4b, MU4c, MU4d,
MU6, MU6b, MU11, MU12, MU13, MU14) plus a both-guards-deleted case → `FAILED (failures=2, errors=9, skipped=10)`,
matching `tasks.md:43`; 12-case `\Z`/`$` differential; the five F1 counting/diff proofs; the repo-wide `018`
grep behind R2-1; `md5sum -c` before/after each batch.

## Verified by reading only

That the mutation narratives were also obtained via a "byte-exact restore verified by md5" procedure
(`test-plan.md:26`) — I reproduced the results, not their method. The claim that `grok_spec.py validate --gate`
returns `ok: true` after the 512-char length incident (`tasks.md:56-58`) — re-running the typed gate and
`scripts/grok_verify.py --mode pr` are outside this review's instructed scope. Live PostgreSQL/Docker behaviour
(the 10 skips), the deployed worker's actual image, and `GET /jobs/{id}` over real HTTP (redaction was exercised
on `_public_result` directly). Whether the transient `4b63a994…` read at 05:09 UTC was an editor, a tool, or a
concurrent writer — I only record that it happened and that final bytes are stable.
