# A killed Trust CI command must not read as a verification failure (#103)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260917-fix-trust-ci-a-killed-mandatory-job-command-must-688330`
Route: `68833064bec9` (intent bugfix, standard, medium risk, write owner `general_implementer`)
Base: `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`

## Problem

[Issue #103](https://github.com/Dimkox/adaptive-grok-build-pro/issues/103): an operator SIGKILLed the runner
container of a live gate job (PR #102 head `123ac93c`, job `47d397ab-9b58-463e-a01e-7bdd33897725`). The durable
record says `status=failed failure_code=verification-failed`; the only trace of the kill is
`result->commands[*].exit_code = 137` on `repository-verification`, and nothing interprets it. Because this
repository's whole merge model is that durable record, an agent reading it may "fix" a defect that never
existed, or declare a head bad when the measurement simply died. The issue also notes the real cause for that
head was a `git diff --check` failure the local preflight had already named.

Two places flatten the signal, both in `trust-ci/src/adaptive_trust_ci/runner.py` at base `2f66ba6`:

- `runner.py:517` — `failure_code=None if status == 'passed' else 'verification-failed'`: every non-passing
  run, killed or genuinely failing, gets the same code.
- `runner.py:345` — the attestation-replay branch hardcodes `'verification-failed'` for any stored
  non-passing attestation, so a re-claim of a killed job rewrites even a correct classification away.

The producer keeps the evidence but not the meaning: `sandbox.py:180` stores
`int(process.returncode or 0)` (so the container client's `137`/`143`, or a negative `subprocess` return code
when the client itself is signalled, are preserved verbatim) and `sandbox.py:202` collapses
`status='pass' if exit_code == 0 else 'fail'`.

## Outcome

`status` stays inside the frozen vocabulary; the terminal *cause* becomes distinguishable in the row, in the
API and in the check run, without a migration:

| Stored record | Meaning |
| --- | --- |
| `status=failed`, `failure_code=aborted-by-signal`, `result.abort={kind:signal, signal:SIGKILL, signal_number:9, exit_code:137, command:repository-verification}` | the measurement was destroyed by a signal; nothing was verified |
| `status=failed`, `failure_code=aborted-by-timeout`, `result.abort={kind:timeout, exit_code:124, …}` | the sandbox deadline killed the command; nothing was verified |
| `status=failed`, `failure_code=verification-failed`, no `result.abort` | unchanged: a command actually ran and said no |

The App-owned check keeps a non-success `failure` conclusion and additionally names the cause
(`Trust CI run aborted: SIGKILL in <command>`), so an aborted run certifies nothing in either direction.

## Scope

### In scope

- One pure exit-status interpreter in `sandbox.py` next to the conventions it reads
  (`classify_command_abort`, `CommandAbort`), covering signal death as `128+n` (n in 1..64) and as a negative
  `subprocess` return code, plus the sandbox's own `124` deadline when its stderr marker corroborates it.
- Deriving the terminal `failure_code` from it in both runner branches (live and replay) and adding the
  additive `result.abort` JSON member.
- Check title/summary text; `abort` added to the read-API redaction allowlist.
- Tests for every interpreted class plus contradictory controls.
- Round-2 review closure: the classifier is total against the values a stored JSON attestation can actually
  hold (`null`, a string, a float, a bool — none of them may raise or mint a fractional `signal_number`), the
  timeout claim is anchored to the end of the stored tail, the signal range is pinned at 129/192/193, and a
  passed run is proven to carry no `failure_code` at all.

### Out of scope (deliberately, not silently)

- **The deployed Trust CI service is not updated by this commit** and the already-stored PR #102 job row is
  not rewritten: no backfill, no SQL, no destructive operation (see `release.md`).
- Distinguishing an in-container **OOM** kill from an outside **SIGKILL**: both reach us as `137`, and
  `docker run --rm` removes the container before anything could read `OOMKilled`. Recorded as a residual
  limit; `result.abort.signal` says `SIGKILL`, which is true for both.
- Issue #103's secondary hazard (three concurrent `scripts/grok_verify.py` invocations; advertising
  `--no-record` as the runner's marker; refusing manual signalling of a job whose `lease_owner` the operator
  cannot name). Untouched here; it needs its own route.
- Infrastructure exits `125`/`126`/`127` (daemon refused / not executable / not found) still record
  `verification-failed`. They are neither a verdict nor a kill; renaming them is a separate vocabulary task.
- Job `status` vocabulary, migrations, metrics labels, and any check `conclusion` value.

## Constraints

- Backward compatibility: no new `status` value (`001_schema.sql` has a CHECK over
  queued/leased/running/passed/failed/needs_approval/cancelled/dead); `failure_code` is unconstrained `text`;
  `result` is `jsonb`, so `abort` is additive. Readers that test `status == 'passed'` or compare against
  `verification-failed` behave exactly as before, and neither new code can read as success.
- Data/privacy: `result.abort` holds only policy command name, exit code, signal name/number and kind — never
  command output. The `/jobs/{job_id}` redaction test still proves `stdout_tail`/`stderr_tail` are absent.
- Performance: one pass over at most `1 + len(commands) + len(holdout commands)` results per job.
- Operational: nothing to deploy for the source tree to be correct; the fix takes effect on the CI host only
  when the maintainer rebuilds/relaunches the worker image from a commit that contains it.
