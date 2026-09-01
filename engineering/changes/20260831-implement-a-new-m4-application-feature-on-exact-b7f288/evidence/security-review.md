# M4 round-5 security review — PASS

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head: `f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Full reviewed diff: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Round-5 delta: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Round-5 fix commit: `f82134de35e531a8b3bbf235ad480254ba40f1fe` (parent `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`)
- Reviewer: route-selected read-only `security_reviewer`
- Verdict: **PASS**
- Critical findings: **0**
- Important findings: **0**
- Moderate findings: **0**

No Critical, Important, or Moderate security finding remains. This report is local exact-tree evidence only. It is not merge authority and cannot replace the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check on the exact pull-request head.

## Severity-ordered findings

No findings.

## Round-4 residual closure: allocation release authority

Migration 008 revokes runtime UPDATE authority on `factory.capacity_allocations` (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). This closes round-4 Moderate M-1: a runtime credential can no longer forge either release or restoration of `capacity_allocations.released_at`.

The supported PostgreSQL test verifies both the effective privilege and actual denial:

- `has_column_privilege('factory_runtime', 'factory.capacity_allocations', 'released_at', 'UPDATE') = false` (`factory/tests/test_postgres_integration.py:637-641`).
- Runtime attempts to set `released_at=clock_timestamp()` and `released_at=NULL` both raise `InsufficientPrivilege` (`factory/tests/test_postgres_integration.py:643-657`).
- Existing counter INSERT/UPDATE, allocation INSERT, immutable intake/event/audit, and cross-schema denials remain in the same effective-role regression (`factory/tests/test_postgres_integration.py:626-657`).

Legitimate release remains available only through `factory.capacity_release(uuid)`, a `SECURITY DEFINER` function with `SET search_path=pg_catalog,factory`, schema-qualified relations, run-closed validation, ordered counter locks, underflow rejection, allocation release and counter decrement in one transaction (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:127-157`). PUBLIC execute remains revoked and runtime execute remains explicitly granted (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:160-169`).

The store was correctly adapted to the least-privilege role: it no longer requests direct row locks on `capacity_allocations`, which require UPDATE privilege, while the database-owned capacity functions retain the authoritative locks and transitions (`factory/src/adaptive_factory/store.py:523-575`). Positive cancel, supersede, reconciliation and completion lifecycle tests pass, so the revoke does not create a release or availability regression.

## Live-allocation fence enforcement

`_lock_grant` now requires `a.released_at IS NULL` in addition to the existing run ID, task ID, authenticated owner, fence, packet digest, live run state, lease/deadline and current task projection checks (`factory/src/adaptive_factory/store.py:581-599`). That single locked boundary is used by:

- heartbeat before lease extension (`factory/src/adaptive_factory/store.py:600-617`);
- release before attempt, run, task and capacity transitions (`factory/src/adaptive_factory/store.py:618-689`);
- budget reservation before any reservation or task accounting write (`factory/src/adaptive_factory/store.py:691-756`);
- usage observation before reservation settlement, usage insertion or accounting changes (`factory/src/adaptive_factory/store.py:758-893`).

The removed direct `FOR UPDATE OF a` does not weaken concurrency. Capacity allocation/release is serialized by the fixed-search-path definer functions' ordered counter locks; release also locks the live allocation before changing it (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:56-77,127-157`). Run/task row locks continue to serialize worker state transitions. A released or missing allocation therefore causes `FenceError` before any new worker mutation.

The new PostgreSQL regression deliberately hides an allocation using migration-owner authority, then proves heartbeat, release, reserve, and usage all reject the holder; readiness becomes `not_ready`; reconciliation refuses inconsistent capacity; restoring the owner-created fault permits normal usage and completion (`factory/tests/test_postgres_integration.py:675-716`). This is a strong fault-injection test beyond what the runtime role itself can perform after migration 008.

Exact replay remains intentionally before fence validation. An already committed command returns its immutable prior result or error without performing another mutation; a new key must pass the live-allocation fence. This preserves at-most-once behavior, stale-fence safety, and durable correlation (`factory/src/adaptive_factory/store.py:109-131,600-617,680-689,701-756,779-893`).

## Prior security areas rechecked

| Area | Round-5 result | Evidence |
| --- | --- | --- |
| M0 authority | **Closed** | Intake accepts only a matching, non-revoked persisted observation or bounded exception; caller assertions alone fail (`factory/src/adaptive_factory/service.py:43-49`, `factory/src/adaptive_factory/store.py:133-150`). Runtime has SELECT-only access to the authority tables. |
| Worker actor and repository binding | **Closed** | Claim owner is derived from the authenticated worker. Worker kind, scope, repository authorization and grant owner are checked at the service boundary; store fencing rechecks immutable run/task identity (`factory/src/adaptive_factory/service.py:61-132`, `factory/src/adaptive_factory/store.py:581-599`). |
| Completion accounting and fail-closed budgets | **Closed** | Reservation and usage values are typed/bounded; accounting blocks on invalid/missing pricing or exceeded limits; completion requires usage, no accounting block and no open reservation (`factory/src/adaptive_factory/store.py:629-650,691-893`). |
| Claim-null replay and command correlation | **Closed** | No-grant claims are recorded durably. Commands serialize by advisory lock, bind actor/action/request digest, preserve correlation, replay exact results/errors, and reject changed content (`factory/src/adaptive_factory/store.py:109-131,418-521`). |
| UDS and secret boundary | **Closed** | Composition pre-binds only an owned `AF_UNIX` socket at mode `0660`; safe absolute paths and private parents are required. Token/actor files are bounded no-follow regular `0600`; bearer comparisons are constant-time; access logging is disabled (`factory/src/adaptive_factory/server.py:20-120`, `factory/src/adaptive_factory/settings.py:25-73`, `factory/src/adaptive_factory/api.py:35-53`). |
| Streaming request cap | **Closed** | Declared length is validated and streamed chunks are cumulatively capped at 1 MiB before parsing (`factory/src/adaptive_factory/api.py:19,108-126`). Declared, missing/chunked and malformed-length regressions pass. |
| SQL/injection and definer search path | **Closed** | Application values are parameterized. All capacity definer functions fix `search_path=pg_catalog,factory`, schema-qualify relations, validate typed inputs, revoke PUBLIC execute and expose only the bounded runtime calls (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:11-169`). |
| Canonical capacity and isolation | **Closed** | Database CHECK policy fixes global readers at 20, global writer at 1 and repository readers at 10. Runtime cannot forge counters or allocations; supported scheduler hard-cap tests pass (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-9,80-125,160-169`). |
| Lease fencing, kill switches and reconciliation | **Closed** | Database time, monotonic fences, owner/run/packet/current-state/deadline/live-allocation checks, kill-before-claim, bounded ordered reconciliation and fail-closed capacity consistency remain. Stale holders and hidden allocations are rejected. |
| Audit integrity and logging | **Closed** | Runtime cannot UPDATE/DELETE audit rows; hash-chain verification and append-only event/audit behavior pass. HTTP access logging is disabled and bounded error responses do not expose secrets or SQL details. |
| Unsafe operations | **Closed** | No provider execution, subprocess/shell, Git/GitHub, systemd, deploy, TCP listener/client, connector, production mutation or Trust CI authority path exists under `factory/src/adaptive_factory`. |

## Verification evidence

```text
git rev-parse HEAD
f82134de35e531a8b3bbf235ad480254ba40f1fe

git show -s --format='%H%n%P%n%s' HEAD
f82134de35e531a8b3bbf235ad480254ba40f1fe
9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
fix(factory): close allocation release authority

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..HEAD
PASS (no output)

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
Ran 30 tests — OK

uv run --project factory python factory/tests/run_disposable_exit.py
Ran 43 tests — OK
PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

python3 scripts/grok_verify.py --mode pr
PASS architecture, governance, secret-scan, contract-structure, SQL safety,
Ruff, Bandit, Python unittest, coverage, factory unit, factory PostgreSQL exit,
and source stability
RESULT: PASS | profiles=base,contracts,data,integration | changed=86
```

The first broad verifier invocation was environmentally invalid because the preceding focused `uv run` had created an ignored `factory/.venv`, which architecture inventory correctly treated as unowned source. The reviewer moved that generated environment out of the repository and reran the verifier; the clean exact-head run above passed with a stable fingerprint. No product file was changed for that cleanup.

The disposable PostgreSQL runner removed its unique container. No `.env`, token content, private key, credential store, production dump, Trust CI secret/state or human approval material was read. No shared/production database, external system, push, merge, release or deployment was mutated. The only repository write by this reviewer is this requested report.

## Verdict

**PASS** for local `security_review` on exact head `f82134de35e531a8b3bbf235ad480254ba40f1fe`. Critical: 0. Important: 0. Moderate: 0. Record the receipt only while the tree fingerprint remains current; any repository change invalidates this report and requires affected verification/review again.
