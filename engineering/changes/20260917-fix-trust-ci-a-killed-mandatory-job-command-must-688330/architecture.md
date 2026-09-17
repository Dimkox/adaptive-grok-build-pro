# Architecture — record an aborted Trust CI command as interrupted (#103)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

## Current behavior

`ContainerExecutor.run` (`trust-ci/src/adaptive_trust_ci/sandbox.py`) launches each mandatory command as
`docker run …`, waits, and turns the process status into a `CommandResult`: `exit_code =
int(process.returncode or 0)` (line 180) and `status='pass' if exit_code == 0 else 'fail'` (line 202). The
sandbox's own deadline overwrites the code with `124` and appends `command timed out after Ns` to stderr
(lines 176-178). `JobRunner.process` then reduces the whole list to `status = 'passed' | 'failed'` and calls
`store.finish(..., failure_code=None if status == 'passed' else 'verification-failed')`
(`runner.py:517`), while the replay branch hardcodes the same code at `runner.py:345`. Exit codes 96 (typed
spec error) and 97 (`<command>:source-integrity`) are synthetic values minted in `runner.py`, never process
statuses.

## Proposed behavior

Exit-status meaning is interpreted in `sandbox.py`, the module that mints the conventions, so producer and
reader cannot drift again:

```
classify_command_abort(name=, exit_code=, stderr_tail=) -> CommandAbort | None
    exit_code is not a plain int (None, str, float, bool) -> None (no claim)  # totality lives here
    stderr_tail is not a str (None, list, bytes, any object) -> treated as '' : no timeout corroboration
    exit_code < 0                      -> signal  -exit_code (1..64)   kind=signal
    128 < exit_code <= 128 + 64        -> signal  exit_code - 128      kind=signal
    exit_code == 124 and stderr tail ends with the sandbox timeout marker -> kind=timeout
    otherwise                          -> None (no claim)
CommandAbort.failure_code -> 'aborted-by-signal' | 'aborted-by-timeout'
CommandAbort.to_result()  -> {kind, command, exit_code, signal, signal_number, failure_code}
```

`runner.py` gained five module-level helpers — `_first_command_abort` (carries its own type check as a second
independent layer in front of the pure call), `_live_command_abort` (over `CommandResult`s with stderr),
`_attested_command_abort` (over a signature-verified attestation's command rows, which carry no output, so
only signal death is provable there and a live timeout classification falls back to `verification-failed` —
disclosed in `requirements.md`), `_terminal_failure_code` and `_abort_check_title`. `_complete_check` accepts
an optional `title`.

Data flow for one terminal job: `command_results` → first non-passing row that is provably an abort →
`status='failed'` (unchanged) + `failure_code` from the abort class + additive `result['abort']` → the same
`details` dict is what `PostgresStore.finish` writes into `trust_ci_jobs.result` (jsonb) and
`failure_code` (text). The signed attestation is unchanged in shape and still says `status='failed'`; the
classification is derived from it on replay rather than stored in it, so no signature format or policy digest
moves.

## Components and boundaries

Changed: `sandbox.py` (classification), `runner.py` (derivation at the two finish sites + check text),
`api.py` (one key in the `_public_result` allowlist). Unchanged: `store.py`, `models.py`, `metrics.py`,
`worker.py`, `github.py`, `policy.py`, `signing.py`, `holdout.py`, `workspace.py`, every SQL file, every
config file. No new module, no new dependency, no new service, queue or table.

## API and event contracts

`engineering/contracts/openapi/trust-ci.v1.json` declares no job schema and no `failure_code` enum, so the
vocabulary is source-side only; the endpoint's response object is the `Job` dataclass dict, which already
carried `failure_code`. The additive `result.abort` member is a strictly optional JSON object; old clients
ignore it.

## Governance context

- Applicable rule IDs: none in `governance/` bind `trust-ci/**` process-exit semantics; `AGENTS.md` data
  rules (versioned migrations only, no destructive SQL) and the source-of-truth order were the binding
  constraints.
- Applicable canonical example IDs/versions: none.
- Open or overdue debt IDs: none created. The unmade distinction between OOM and outside SIGKILL, and the
  unclassified `125/126/127` infrastructure exits, are named in `brief.md` as residual limits.
- Expected governance handoff or receipt impact: `verification`, `code_review`, `test_review` receipts bound
  to the final fingerprint; `trust-ci/**` is inside the `governance` approval-rule glob of
  `trust-ci/config/policy.example.json`, so the deployed policy will likely demand a human-signed
  `governance` approval for the exact PR head before the App check turns green.

## Bitrix-specific impact

None: this repository is generic Python, no Bitrix tree, no `local/`, no core path, no cache or agent.

## Decisions

1. Express the distinction through `failure_code` + `result.abort`, never through `status`. `status` has a
   frozen CHECK and adding a value needs a migration; `failure_code` is unconstrained text and is already the
   column that carries causes (`approval-required`, `superseded-head`, `policy-digest-mismatch`, …).
2. Put the interpreter in `sandbox.py`, not in a new module or in the runner. The absence of exactly this
   coupling is the defect: `124` and the marker are minted in `ContainerExecutor.run` and were interpreted
   nowhere.
3. Fail closed rather than guess. `124` alone is not claimed as a timeout because a command may exit `124`
   itself — the sandbox's own stderr marker is required. 137 stays `SIGKILL` even though an in-container OOM
   also renders as 137, because both mean "no verdict was reached"; the class never asserts who swung the
   signal.
4. Preserve the distinction on attestation replay too, otherwise a re-claimed job would rewrite its own
   correct record — the same bug in a second place, reachable whenever check publication fails after
   `record_attestation`.
5. Check conclusion stays `failure`. A run that never finished must not certify anything, and GitHub readers
   and branch protection already treat `failure` as blocking.
6. Totality is the classifier's own contract, not a favour from its caller (round-2 review G-1). Round 1 kept
   a single `isinstance` guard in `runner._first_command_abort`, which made that guard load-bearing and its
   deletion an unobserved mutation survivor, while `classify_command_abort(exit_code=None)` raised
   `TypeError` and `exit_code=137.0` produced a bogus `signal_number: 9.0` that would have been written into
   `result.abort`. The type rejection now lives inside `classify_command_abort`, and
   `runner._first_command_abort` keeps its check as a second, independent layer: either one alone is
   sufficient, each is pinned by its own test, and the runner-level claim "the bool check protects the
   classifier" is deliberately **not** made — it is defense-in-depth, nothing more.
7. The same totality argument was applied to the second recovered input after round-2 review (R2-2):
   a non-string `stderr_tail` (`None`, `list`, `bytes`, any object with `__str__`) is normalised to "no
   corroboration" rather than coerced or fed to `re.search`, so a timeout is never claimed from a value the
   sandbox did not write and the classifier cannot raise on it — while a signal kill, which needs no
   corroboration, is still reported. Deciding against `str()` coercion is deliberate: it would let a
   marker-shaped `__str__` manufacture an abort class.

## Risks and mitigations

- A real in-container `137` (OOM, or a script that exits 137 deliberately) now records `aborted-by-signal`
  instead of `verification-failed`. Still non-success and still blocking; the stored
  `result->commands[*].stderr_tail` keeps the raw evidence for a human. Mitigated by the explicit OOM limit in
  `brief.md`.
- The classification reads only `exit_code`/`stderr_tail`, so an output-redaction change or a new sandbox
  runtime that renders signals differently would silently stop classifying. The platform test
  `test_real_signalled_process_return_codes_are_interpreted_on_this_platform` pins the negative-return-code
  contract by actually signalling a process, and
  `test_sandbox_timeout_marker_survives_output_truncation` pins the marker-under-truncation contract.
- New vocabulary could be typosquatting-ambiguous for a grep-based reader. `aborted-by-*` shares no prefix with
  existing codes, and the tests assert the exact strings.
