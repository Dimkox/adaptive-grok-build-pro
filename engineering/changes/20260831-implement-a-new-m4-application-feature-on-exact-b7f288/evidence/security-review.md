# M4 last exact-head security review — FAIL

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Exact base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact reviewed HEAD: `04261326e177e6d2014a576d3f4a0fb5feab56be`
- Exact Git tree: `3959e7c46d6bb30f49727f6162b73d8ab4a72376`
- Focused range: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Full range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..04261326e177e6d2014a576d3f4a0fb5feab56be`
- Exact-head verifier: PASS, all 14 gates, fingerprint `e7401c598db44069e77259d7e0f4da893e67b89f4778e195af540c3a753e86b0`
- Reviewer: route-selected read-only `security_reviewer`

## Verdict

**FAIL**

- Critical findings: **0**
- Important findings: **1**
- Moderate findings: **0**

Migration `011` closes the two previously reported accounting-state omissions in
the single-generation fixture, but its `ready_for_human -> needs_human` recovery
can violate the existing active-identity uniqueness invariant. The exact tree must
not receive a passing security-review receipt.

## Severity-ordered finding

### Important I-1 — legacy positive-state quarantine can collide with a newer active generation and roll back migration 011

The durable task index permits at most one state considered active for a
`(repository_id, source_type, source_id)` identity. It excludes
`ready_for_human`, `dead`, `cancelled` and `superseded`, but it does **not** exclude
`needs_human`
(`factory/src/adaptive_factory/resources/001_initial.sql:61-64`). This is
consistent with runtime intake: a positive `ready_for_human` generation is not
superseded and does not block creating a later active generation of the same
source identity (`factory/src/adaptive_factory/store.py:308-338`).

Migration `011` unconditionally changes every unsafe legacy
`ready_for_human` row to `needs_human`
(`factory/src/adaptive_factory/resources/011_legacy_accounting_quarantine.sql:1-16`).
For a reachable history containing:

1. generation 1 in `ready_for_human` with unresolved prior-attempt accounting;
2. generation 2 for the same identity in `queued`, `retry`, `leased` or another
   index-active state;

the update attempts to put both generations inside `tasks_one_active_identity`.
PostgreSQL raises a unique violation and the atomic migration transaction rolls
back. The control plane remains below required schema 11 and therefore not ready;
the security quarantine that was intended to remove the false-positive terminal
state is never installed.

The expanded upgrade regression does not cover this case. Its unsafe positive row
uses source ID `legacy-ready-reservation`, while every other seeded task uses a
different source ID (`factory/tests/test_postgres_integration.py:1051-1089`). It
therefore proves the update only when no later active generation can conflict
(`test_postgres_integration.py:1129-1144`). The exact-head verifier's 63-test
PostgreSQL pass inherits this gap.

Required remediation:

1. Add a forward migration that gives unsafe legacy positive generations an
   evidence-preserving, non-positive quarantine representation compatible with an
   already-active newer generation. Do not delete or rewrite intent, run,
   reservation, usage or audit evidence, and do not weaken the one-active-identity
   invariant merely to make the migration pass.
2. Add a real schema-008 upgrade regression with an unsafe
   `ready_for_human` generation and a newer active generation sharing the exact
   repository/source identity. Prove migrations `009..current` apply atomically,
   the unsafe generation is no longer reported as a successful endpoint, the
   intended current generation remains unambiguous, readiness is truthful, and
   migration replay is idempotent.

## Focused security assessment

- Migration `011` contains only static, schema-qualified owner DML. It adds no
  function, role, grant, default privilege or dynamic SQL and does not broaden
  runtime access. Its predicates preserve reservation/counter/run/usage rows; the
  finding is the incompatible target state, not evidence deletion.
- The new readiness predicate correctly detects blocked or unsettled
  `queued`, `retry` and `ready_for_human` rows. Claim independently retains the
  unblocked/zero-counter/no-live-reservation candidate guard. These checks fail
  closed after a successful migration and under owner-only fault injection.
- The checked single-generation upgrade cases now correctly move blocked-zero
  retry and unsettled positive rows to `needs_human/accounting_blocked`, preserve
  aggregate and reservation evidence, reject claim, and make migration replay a
  no-op.

## Prior security closures rechecked

- Observation and bootstrap-exception M0 authority remain bound to repository,
  full policy digest, closed action, trusted identity, exact governance head and
  expiry/non-revocation. Both validators retain fixed
  `search_path=pg_catalog,factory`, PUBLIC-revoked EXECUTE-only definer authority
  and `FOR SHARE`; real PostgreSQL tests still cover revoke-before-validation and
  revocation blocked through commit after validation.
- M2/M3 provenance and exact base/head compatibility remain immutable and caller
  claims do not substitute Trust-CI authority.
- Global reconcile/metrics still require wildcard operator authority. Worker
  operations remain actor/repository/task/run/owner/fence/packet/live-allocation/
  lease/deadline/budget bound.
- Capacity remains behind the fixed-search-path, PUBLIC-revoked 20/10/1 definer
  functions. Runtime cannot forge counters, allocations or allocation release;
  drift makes readiness and reconcile fail closed.
- Mandatory cleanup remains internal, state/fence/idempotency bounded and audited
  in the same transaction. It cannot consume or bypass ordinary retry budget;
  exhausted retry routes to `needs_human`, and cleanup releases capacity exactly
  once.
- Audit v2 still authenticates task/run/correlation and all other semantic fields;
  runtime audit/event update and delete remain denied. Absolute owned no-follow
  actor/token loading, constant-time bearer comparison, 1 MiB cumulative body cap,
  bounded/redacted responses and owned UDS-only serving remain unchanged.
- No provider, shell, repository, Git/GitHub, TCP, systemd, deployment or other
  external execution/write path was added. No GitHub Actions or deployed Trust-CI
  policy, holdout, key, database, GitHub App, approval-store or branch-protection
  boundary changed.

## Verification evidence

- Inspected the active route/change package, prior reviews, implementation
  ledger/report, complete focused diff, migration `011`, readiness/store logic and
  the expanded schema-008 PostgreSQL fixture.
- `git diff --check 67714a1...0426132` passed.
- Independent focused contracts/state/migrations/service run passed 24/24.
- The exact-head receipt reports all 14 gates PASS, including source stability,
  63/63 disposable PostgreSQL/API/effective-role tests and actual restart/
  reconciliation. Those results do not exercise the same-identity multi-generation
  upgrade conflict above.
- No `.env`, token, private key, credential store, production dump, shared
  database, Trust-CI state or external system was read or mutated. No product code,
  commit, receipt, database, push, merge, release or deployment was changed by this
  review; the only retained repository write is this requested report.

## Residual trust boundary

After I-1 is repaired by the route's single write owner, rerun exact-head
verification and affected independent reviews on one stable fingerprint. Local
review evidence never authorizes merge: the final PR SHA still requires the GitHub
App-owned policy-epoch Check Run and all independently signed approval scopes
required by deployed policy.
