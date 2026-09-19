# Independent code review — issue #103 (killed mandatory Trust CI command)

PASS

Route `68833064bec9` · branch `fix/trust-ci-killed-status` · base `2f66ba6` · reviewed the uncommitted tree;
nothing committed, pushed or edited by this review.

## 1. Classifier vs. the conventions it interprets — verified against the code that mints them

`ContainerExecutor.run` (`sandbox.py:180-253`) mints exactly three forms, and the classifier (`:66-89`)
interprets exactly those: `127` at `:199`/`:223` (runtime missing, `OSError` spawn) → not an abort;
`124` + `stderr += f'\ncommand timed out after {spec.timeout_seconds}s'` at `:245-247` → abort only with the
marker; `int(process.returncode or 0)` at `:248` (container `128+n`, or negative when the client itself is
signalled) → abort. Measured boundary table (real calls, not assertions quoted from the diff):

```
     0 -> None      96 -> None     128 -> None      137 -> ('signal','SIGKILL',9,'aborted-by-signal')
     1 -> None      97 -> None     129 -> SIGHUP    143 -> SIGTERM
   124(+marker) -> ('timeout',None,None,'aborted-by-timeout')   161 -> SIG33 (unmapped fallback)
   124/125/126/127 -> None       192 -> SIGRTMAX    193 -> None   255 -> None   256 -> None
    -1/-2/-6/-9/-15/-64 -> signal aborts;  -65/-124/-256 -> None
    True -> None   False -> None
   124 marker mid-string  -> None      (regex is `\Z`-anchored, correct)
```

`128` itself is correctly **not** signal 0 (`_SIGNAL_BASE < exit_code` is strict, `:78`) and the `1..64` bound is
right for both branches: `192` = `SIGRTMAX`, `193` rejected, `-64` accepted, `-65` rejected. Synthetic in-runner
codes `96` (`runner.py:482`, typed-spec) and `97` (`runner.py:634`, source-integrity) stay
`verification-failed` — measured, and pinned by `test_source_integrity_failure_is_not_reported_as_an_abort`.

Marker-under-truncation, re-executed end-to-end through `_command_result`/`_tail` (not just the regex):

```
max_output_bytes 1024 tail_len 512 -> aborted-by-timeout
max_output_bytes 200000 tail_len 90030 -> aborted-by-timeout
real SIGKILL returncode: -9 -> aborted-by-signal
```

The marker is appended to `stderr` **before** `_tail` keeps the last bytes, so truncation can only cut the front.
`policy.py:249` bounds `max_output_bytes` to `[1024, 10_000_000]` — ≥512 bytes per stream vs. a ~31-byte marker —
so the claim holds structurally, not just by test. `timeout_seconds` is `int` (`policy.py:25`), so the
`[0-9.]+s` form is safe (a float rendering also matches).

The bool claim is **overstated as written**: `isinstance(exit_code, bool)` lives in `runner.py:266`, not in the
classifier, and `classify_command_abort(exit_code=True)` returns `None` on its own (`True < 0` false,
`128 < True` false, `True == 124` false). The guard is correct defense-in-depth against a JSON `true` arriving
via `item.get('exit_code')` on the replay path, but it is not load-bearing — finding F4.

## 2. Fail-closed direction — confirmed

`status` is unchanged everywhere: `_terminal_failure_code` reads status, never writes it; both `store.finish`
implementations still reject anything outside `{passed, failed, needs_approval, cancelled, dead}`
(`store.py:161`, `:411`), matching the frozen `status IN (...)` CHECK at `sql/001_schema.sql:11-14` and the
packaged copy. `failure_code text` is unconstrained (`001_schema.sql:20`) — verified. Measured:
`_terminal_failure_code('passed', <non-None abort>) = None`, and the reverse combination is unreachable —
`status == 'passed'` requires every command `status == 'pass'`, which `_live_command_abort` filters out.
`_complete_check` still derives `conclusion` from `passed` alone (`runner.py:682-686`), so the new `title` can
only rename a `failure`. `retry()` / `requeue_for_approval()` key on `attempts`/`status`, never on
`failure_code`, and no in-tree reader greps `verification-failed` (grep: only `tests/`, `mistakes.md`,
`decisions.md`) — an abort cannot widen success or trigger a rerun. `engineering/contracts/openapi/trust-ci.v1.json`
does not enumerate the job body or freeze `result` (`additionalProperties: false` appears only on
webhook/approval/error schemas) → the additive `result.abort` needs no contract change.

## 3. Replay path — real, with one disclosed asymmetry

`CommandResult.attestation_dict()` (`models.py:398-405`) always carries `exit_code`, so signal death **is**
provable on replay. Measured: a stored row with `exit_code` absent or `None` yields `None` →
`verification-failed` (fails safe). A timeout abort cannot be recovered, because `_attested_command_abort`
(`runner.py:283-288`) hardcodes `stderr_tail=''`:

```
LIVE  verdict : aborted-by-timeout
stored row    : {'name': 'root-unittest', 'status': 'fail', 'exit_code': 124, ...}   # no stderr in signed rows
REPLAY verdict: None  -> verification-failed
```

A timeout can never be *fabricated* on replay (empty tail can't satisfy the `\Z`-anchored marker). The
asymmetry **is** disclosed — `runner.py:284` docstring and `architecture.md:33-34` ("signed rows carry no
output, so only signal death is provable"). Reachable only in the crash window between `record_attestation`
and `finish` (`requeue_for_approval` touches `needs_approval` rows only, `store.py:559`); it loses the
`result.abort` member and the stored tails. Acceptable — finding F3.

## 4. Scope discipline — confirmed

`git diff --name-only` is exactly `decisions.md`, `trust-ci/src/adaptive_trust_ci/{api,runner,sandbox}.py`,
`trust-ci/tests/{test_api,test_ops,test_runner}.py`; `api.py` is the claimed single line. Nothing matches
`migration|\.sql|\.github|holdout|policy`, and `sql/`/`resources/` copies stay byte-equal
(`test_packaged_migrations_match_deployment_migrations`, `test_ops.py:242`). No identity file changed
(`VERSION`, `README.md`, `CHANGELOG.md`, `PROJECT_STATE.json`, `START_HERE.md` → `NONE`). Zero `.py` files under
`engineering/changes/20260917-…/` (`find` → nothing), so `FIT-DECLARED-NETWORK-ONLY` is unreachable. No stored
job is rewritten: no SQL, backfill, `UPDATE` or `DELETE` anywhere in the diff; PR #102 job `47d397ab…` untouched.
`release.md` states source-only delivery and that post-merge jobs still record `verification-failed` until a
separately authorized image rebuild — consistent with `AGENTS.md`.

## 5. Re-executed commands (verbatim tails)

Canonical invocation for this tree is `make trust-ci-test` → `PYTHONPATH=trust-ci/src python3 -m unittest
discover -s trust-ci/tests` (`Makefile:18-19`). The invocation suggested in the brief **is wrong here**: without
`PYTHONPATH=trust-ci/src`, and with `-t trust-ci`, the tests package cannot resolve its own helper module.

```
$ python3 -m unittest discover -s trust-ci/tests -t trust-ci 2>&1 | tail -5
----------------------------------------------------------------------
Ran 53 tests in 3.559s

FAILED (errors=16)
  (each: "ModuleNotFoundError: No module named '_support'")

$ PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests 2>&1 | tail -4
----------------------------------------------------------------------
Ran 263 tests in 7.189s

OK (skipped=10)

$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest test_ops test_runner test_api 2>&1 | tail -3
Ran 81 tests in 0.994s

OK

$ PYTHONPATH=trust-ci/src:trust-ci/tests python3 -m unittest test_ops.CommandAbortClassificationTests -v
  11 tests, all ok, incl. test_real_signalled_process_return_codes_are_interpreted_on_this_platform,
  test_sandbox_timeout_marker_survives_output_truncation, test_bare_124_without_the_sandbox_marker_is_...
Ran 11 tests in 0.306s

OK

$ python3 -m compileall -q trust-ci/src trust-ci/tests && ~/.local/bin/ruff check <six changed .py files>
compileall OK
All checks passed!
```

## Non-blocking findings

- **F1 — `change-spec.yaml:99` misnames the migration set.** It asserts "Deployment migrations
  `trust-ci/sql/001-018` … stay byte-identical". Measured: `ls trust-ci/sql/*.sql | wc -l` → `3`
  (`001_schema.sql`, `002_operational_indexes.sql`, `003_database_roles.sql`); the `001`-`018` numbering belongs
  to `factory/src/adaptive_factory/resources/`, which already reaches `020_execution_v2_priced_usage.sql`.
  `release.md` repeats "`001`-`018`". The substance is true (no migration path is touched) — fix the citation.
- **F2 — `release.md` alert guidance is contradicted by this change's own risk record.** It tells operators
  "any `aborted-by-signal` row is an infrastructure event, not a code defect — … do not 'fix' the pull request."
  `architecture.md:84-85` and `brief.md:61-62` state that an **in-container** OOM (bounded by `--memory`,
  `sandbox.py:141-142`) also renders as `137` — including one caused by the pull request's own test code — and
  would be labelled `aborted-by-signal`. The gate verdict is unaffected, so this is triage misdirection, not a
  trust weakening; soften the sentence. (`architecture.md:97` cites "`brief.md`" for an "explicit OOM limit"
  while `brief.md:61-62` records it as a *residual*; worth aligning.)
- **F3 — replay loses the timeout class** (§3). Disclosed and fail-safe; if it ever matters, read
  `result->commands[*].stderr_tail` from the row being re-finished, not only the signed rows.
- **F4 — bool guard is redundant** (§1). Correct and harmless; the write-up should not present it as the thing
  that rejects `True`.

## What I did not verify

- `python3 scripts/grok_verify.py --mode pr` and the root repository suite (out of scope by instruction; only
  `trust-ci/tests` was re-run).
- Live PostgreSQL behaviour: the 10 skips are Docker `postgres-integration`. `finish` CHECK compatibility was
  verified by reading `sql/001_schema.sql:11-14` and `store.py:411`, not by a live write. Likewise no container
  was launched — `137`/`-9` came from a local signalled process plus direct classifier calls.
- Consumers of `failure_code` outside this repository (external dashboards/alerts are not in-tree).
- `test_reviewer`'s scope beyond "are these tests real and non-vacuous" — mutation testing and coverage
  attribution belong to that review.
