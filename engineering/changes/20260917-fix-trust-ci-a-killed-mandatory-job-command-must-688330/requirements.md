# Requirements — interrupted Trust CI commands (#103)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [x] `AC-001` Given a mandatory command whose process died from a signal (container client `137`/`143`/`130`/`161`, or a negative `subprocess` return code `-9`/`-15`/`-2`/`-1`), when the job finishes, then `status` stays `failed`, `failure_code` is `aborted-by-signal` (not `verification-failed`), and `result.abort` names kind, command, raw exit code, signal name and signal number.
- [x] `AC-002` Given the sandbox's own deadline killed the command (`124` plus the marker `ContainerExecutor.run` appends), then `failure_code` is `aborted-by-timeout`, `abort.kind` is `timeout` and no signal is claimed; given a bare `124` without that marker, the record is unchanged (`verification-failed`, no `abort`).
- [x] `AC-003` Every other failing outcome keeps `failure_code=verification-failed`: ordinary exit `1`, synthetic `96` (typed spec) and `97` (source integrity), and out-of-range codes `0/125/126/127/128/193/255/-65/-1000`.
- [x] `AC-004` A re-claimed job replaying a stored attestation keeps the interrupted class derived from that attestation's signed command rows (`result.replayed` stays true); a replayed pass still records `failure_code=NULL`.
- [x] `AC-005` `GET /jobs/{job_id}` exposes `failure_code` and the additive `result.abort`, and still omits `stdout_tail`/`stderr_tail` and their content.
- [x] `AC-006` The App-owned check reports the abort in title and summary while its conclusion stays `failure`.
- [x] `INV-001` Classification is pure and total at its own boundary on **both** recovered inputs — `classify_command_abort` returns no claim for a `None`/string/float/bool `exit_code` (never raises, never mints `signal_number: 9.0` for `137.0`) and never coerces a non-string `stderr_tail` (`None`, list, `bytes`, an object with `__str__`) into a timeout corroboration, while a signal kill is still reported from the exit status alone; the check in `runner._first_command_abort` is a second independent layer. A passed status can never carry any `failure_code` (`_terminal_failure_code('passed', …) is None`, proven end-to-end by `test_passed_job_records_no_failure_code_at_all` and by the passed-replay assertion).
- [x] `INV-002` No migration, no schema change: `git diff --name-only 2f66ba6 -- '*.sql'` is empty — covering all three numbered-SQL sets in the tree: the three `trust-ci/sql/*.sql` deployment files, their three packaged copies (`test_packaged_migrations_match_deployment_migrations`), and `factory/src/adaptive_factory/resources/` (20 files today, **18 at tag `v2.0.13`**: `git ls-tree -r --name-only v2.0.13 | grep -c 'factory/src/adaptive_factory/resources/.*\.sql'` → `18`). That factory set is what the `"001-018"` string counts where it really appears — `PROJECT_STATE.json → current_unreleased_change.frozen.postgresql_migrations` (line 261, plus archived copies at 352/625 and `active_delivery.integrated_stack.migrations` at 889), `README.md:32`, `START_HERE.md:57`, `CHANGELOG.md:75` — and **not** `AGENTS.md` (`grep -c "018" AGENTS.md` → `0`). The distinction lives in the existing unconstrained `failure_code text` and an additive member of the existing `result jsonb`.
- [x] `FORBID-001` An aborted measurement never records `verification-failed` on either path, and no abort class can read as success or as `passed`.
- [x] `FORBID-002` No new `status` value, no new migration, no backfill, no rewrite of the stored PR #102 job row.

## Failure and edge cases

- Exit code is exactly `128`: not a signal (no signal 0) → unchanged.
- `193` (= 128+65) and `-65`: outside Linux's 1..64 signal range → unchanged, no invented signal name.
- Unmapped signal number 33 → rendered `SIG33` instead of raising.
- Output truncation: the timeout marker is appended last and `_tail` keeps the end, so the claim survives; proven under a 100-byte budget.
- A stored attestation whose command rows lack `exit_code` or hold a non-integer (a hand-built or future-schema row) → skipped safely, falls back to `verification-failed`.
- **Disclosed asymmetry (round-2 review F3):** the `aborted-by-timeout` class needs the stderr marker, but an attestation's signed command rows carry no output at all. So a timed-out job classified live as `aborted-by-timeout` falls back to `verification-failed` if that same job is ever replayed after a re-claim, while a signal kill keeps its class on both paths (`exit_code` alone proves it). The fallback direction is fail-safe — a replayed timeout is still `status=failed` with a non-success cause and a non-success check — but the *cause text* is less specific on that one path. Not fixed: restoring it would mean widening the signed attestation format (a contract change with its own policy/holdout consequences), which is out of scope for a source-only bugfix.
- The worker process itself being killed leaves no record at all; that path was already distinguishable via lease expiry → `attempts-exhausted-after-worker-loss` (`001_schema.sql`) and `infrastructure-attempts-exhausted` (`store.py`). Unchanged.
- In-container OOM renders as `137` and is recorded as `aborted-by-signal/SIGKILL`; separating OOM from an outside kill is explicitly not delivered (see `brief.md`).

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs: none named for `trust-ci/**` exit-status semantics; `AGENTS.md` data rules (versioned migrations only, bounded and observable backfills, destructive SQL forbidden without human-signed approval) decided the shape of the fix.
- Canonical-example deviations and evidence: none.
- Intentional debt created, repaid, or accepted: accepted debt — OOM vs outside SIGKILL stay merged in one class, and infrastructure exits `125/126/127` still share `verification-failed`.

## Non-functional requirements

- Security: no new secret, PII or output surface; `result.abort` is derived from policy names and process statuses, and the read API stays an allowlist that still redacts command output.
- Reliability: fail closed — every new value is a non-success terminal cause, the check conclusion is unchanged, and branch protection keeps binding the same App-owned check name.
- Performance: one bounded pass over the job's command results at finish time.
- Observability: `SIG-001` — `trust_ci_jobs.failure_code` becomes separable in SQL (`select failure_code, count(*) … where status='failed' group by 1`), in `GET /jobs/{job_id}` and in the check title; the Prometheus `adaptive_trust_ci_jobs{status=…}` labels are intentionally unchanged because `status` did not change.
