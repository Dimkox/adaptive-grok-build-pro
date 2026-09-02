# Task 4 terminal/M4 and integrity remediation report

Status: **DONE_WITH_CONCERNS**

Product commit: `d4b9d17ac42013c75b64c0d3ce9b8e4f57123b97`

## Root cause

The first M5 bridge persisted a factual terminal result without making that transaction the sole authority for the corresponding M4 release. It also trusted duplicated result/evidence digests at the SQL capability boundary and returned a body without independently cross-checking the requested digest and redundant immutable row projection.

This allowed the M5 terminal and caller-selected M4 outcome to diverge, permitted noncanonical direct-function inputs, and made privileged row corruption observable as a different result instead of failing closed. Finalization also acquired task/run before capacity while M4 cancel/reconcile used capacity before task, leaving a lock-order inversion.

## RED evidence

Initial disposable command:

```bash
python3 factory/tests/run_disposable_exit.py
```

Initial result: `Ran 123 tests` with `6 errors`. The first failures were at the finalizer-to-`WorkspaceResultV1` boundary because the persisted contract had no derived `m4_status`, `failure_class`, or `failure_reason`; the database also left the M4 run/allocation/capacity live instead of releasing it in the result transaction.

Additional regression tests reproduced and then guarded:

- pre-finalization legacy `release` could select an M4 outcome independently of the M5 terminal;
- direct `factory_runtime` calls could submit forged/missing/null/fractional snapshot or result facts;
- result-row HEAD or primary digest corruption was not independently rejected on read;
- cross-run manifest/terminal substitutions needed composite foreign keys;
- an ordinary finalize/cancel race did not prove the capacity-before-task lock order, so the final test holds `global:writer`, queues cancel first and finalize second, proves both sessions are lock-waiting through `pg_stat_activity`, then checks the exact cancellation/stale-finalizer outcomes.

## Changed files

- `factory/src/adaptive_factory/resources/013_execution_plane.sql`: closed snapshot/result validation, SQL-derived domain hashes and M4 disposition, composite integrity constraints, capacity-before-task finalization, atomic result/run/attempt/task/capacity mutation, and least-privilege helper grants.
- `factory/src/adaptive_factory/store.py`: M5 legacy-release denial, factual result fields, atomic event/audit recording, fixed lock order, requested-digest and immutable-row verification.
- `factory/src/adaptive_factory/execution_contracts.py` and `factory/contracts/schemas/workspace-result.v1.json`: closed factual M4 disposition and structured failure correlation.
- `factory/src/adaptive_factory/brokers.py`: typed terminal failure class/reason/diagnostic preservation without mapping stringification.
- `factory/tests/test_execution_contracts.py` and `factory/tests/test_postgres_integration.py`: canonical, mapping, rollback, forgery, corruption, cross-run FK, M4 parity, and deterministic concurrency regressions.
- `engineering/changes/20260901-implement-a-new-m5-ai-agent-execution-feature-on-37b05f/{tasks.md,evidence/remediation-review-findings-61db79f.md}`, `decisions.md`, and `mistakes.md`: durable slice state, design ruling, and workflow lessons.

## GREEN evidence

Fresh disposable PostgreSQL 17, API, role, and restart suite:

```bash
python3 factory/tests/run_disposable_exit.py
```

Result: `Ran 125 tests in 53.297s` — `OK`; restart probe reported `PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected`, followed by the disposable exit PASS.

Executable architecture:

```bash
python3 scripts/grok_architecture.py validate
python3 scripts/grok_architecture.py drift --json
```

Both returned `{"findings": [], "ok": true}`.

Root architecture and structure regression:

```bash
UV_PROJECT_ENVIRONMENT="$(mktemp -d)" uv run --project factory \
  python -m unittest tests.test_architecture_fitness tests.test_architecture_model tests.test_structure -v
```

Result: `Ran 148 tests in 124.722s` — `OK`.

Final contract-only check after the last invalid-type guard:

```bash
UV_PROJECT_ENVIRONMENT="$(mktemp -d)" uv run --project factory \
  python -m unittest factory.tests.test_execution_contracts -v
```

Result: `Ran 9 tests in 0.401s` — `OK`. `git diff --check` passed, and the product commit contained no `.venv`, bytecode, or cache artifact.

## Residual risks and blockers

- The exact-`61db79f` independent reviews remain historical FAIL evidence; this slice does not create a PASS review or receipt.
- Structured secret/reasoning redaction plus trusted note/artifact workspace attestation, M5-aware orphan/cancel recovery, and nested schema/OpenAPI closure remain separate remediation slices.
- The shipped fake Git broker remains deliberately unable to attest a live result. The test-only deterministic trusted snapshot broker proves source behavior but is not live OS/Git evidence.
- This host still lacks the required rootless isolation toolchain and user namespaces are unavailable; that OS-isolation exit remains `BLOCKED` pending a dedicated rootless host.
- No provider/network execution, unit activation, external write, final verifier/receipt, M5 exit, push, PR, merge, or deployment was performed or claimed.
