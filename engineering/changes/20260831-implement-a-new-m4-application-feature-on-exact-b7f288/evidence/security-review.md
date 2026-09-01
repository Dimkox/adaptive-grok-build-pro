# M4 exact-final security review — PASS

## Review binding

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Accepted M3 base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior reviewed HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact reviewed HEAD: `daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact Git tree: `9c93b2ca4fea4f71ab70bbf71bd62ca8df936ad8`
- Focused collision-fix range: `04261326e177e6d2014a576d3f4a0fb5feab56be..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..daa3930cb84ba6547171583e41bcf0dee2ab1314`
- Exact-head verifier: PASS, fingerprint `ad41a13355b097f4be0a3d6c3754b9cc4de8178824e801ac264fad81c852e794`
- Reviewer: route-selected read-only `security_reviewer`

## Verdict

**PASS**

- Critical findings: **0**
- Important findings: **0**
- Moderate findings: **0**

The prior active-generation collision is closed. No remaining security,
authorization, repository-isolation, audit-integrity or fail-open finding at
Moderate severity or above was found in the exact full diff.

## Prior Important collision — closed

Migration `011` now selects an evidence-preserving target compatible with the
one-active-generation invariant:

- an unsafe legacy `ready_for_human` row with any newer generation becomes
  `superseded/accounting_blocked`;
- an unsafe positive row without a newer generation, and blocked queued/retry
  rows, become `needs_human/accounting_blocked`.

The existence predicate is bound to the exact repository, source type and source
ID and requires a strictly greater generation
(`factory/src/adaptive_factory/resources/011_legacy_accounting_quarantine.sql:1-27`).
`superseded` remains outside `tasks_one_active_identity`, so an already-active
newer generation is not duplicated or displaced. Intent, run, attempt,
reservation, usage, task-event and audit evidence is not deleted or rewritten.

The real schema-008 regression now seeds generation 1 as an unsafe
`ready_for_human` task and generation 2 as `queued` under the same exact source
identity. It proves migrations `009,010,011` apply, generation 1 becomes
`superseded/accounting_blocked`, generation 2 remains the sole claimable task,
the issued grant is for generation 2, aggregates and the live reservation remain
present, readiness is truthful, and migration replay is empty
(`factory/tests/test_postgres_integration.py:984-1242`).

Readiness recognizes the quarantined terminal representation rather than treating
it as a positive endpoint. It fails if unresolved superseded accounting loses its
`accounting_blocked` marker, while allowing the deliberate blocked quarantine
(`factory/src/adaptive_factory/store.py:80-96`). This is defense in depth beyond
the migration and does not weaken claim selection.

## Migration and privilege assessment

- Migration `011` is static schema-qualified owner DML only. It creates no role,
  function or dynamic SQL, grants no privilege, changes no default privilege and
  exposes no runtime callable capability.
- Packaged migrations remain contiguous and checksum-bound. Earlier migrations
  and the authority/capacity definer functions are unchanged by the focused fix.
- `factory_runtime` still cannot update/delete immutable intents, task events or
  audit rows; forge capacity counters/ceilings; insert allocations; directly
  release allocations; or access the separate `trust_ci` schema.
- M0 observation and exception validators retain fixed
  `search_path=pg_catalog,factory`, static schema-qualified SQL, PUBLIC-revoked
  EXECUTE-only runtime grants and `FOR SHARE` locks that serialize non-key
  revocation through intake commit.

## Full security boundary recheck

- **Authority and provenance:** persisted M0 authority is bound to repository,
  full policy digest, exact policy-epoch check name, closed intake action,
  exact governance head, expiry and non-revocation. Both authority forms and both
  revocation interleavings are exercised. M2/M3 architecture/governance digests
  and exact base/head pairs remain mutually bound and producer-owned.
- **Authorization and isolation:** task submit/read/list/cancel and worker
  operations retain repository checks. Worker grants bind authenticated actor,
  task/run, owner, repository, fence, packet, live allocation, lease/deadline and
  budget state. Global metrics/reconciliation and global kill require wildcard
  operator authority; repository kill remains repository-scoped.
- **Capacity, accounting and cleanup:** fixed-search-path/PUBLIC-revoked database
  functions retain canonical 20-global-reader, 10-repository-reader and one-writer
  enforcement. Readiness/reconcile fail closed on capacity drift. Claim excludes
  blocked/nonzero/live-reservation candidates. Completion requires current-run
  usage and all-task settled accounting. Mandatory cleanup is internal,
  idempotent, state/fence bounded, hash-audited and releases capacity exactly once
  even after ordinary-event exhaustion; exhausted retry routes to human review.
- **Audit integrity:** new audit-v2 rows authenticate previous digest, task, run,
  correlation, actor, action, resource, reason, timestamp and canonical metadata;
  legacy v1 rows remain verifiable without rewrite. Runtime audit update/delete
  remains denied, and cleanup does not bypass audit creation.
- **Local transport and secrets:** actor/token inputs require absolute normalized
  paths, descriptor-walked no-follow ancestry, trusted ownership, an owned private
  final parent and an owned regular mode-`0600` leaf. Bearer comparison is
  constant-time. The server exposes only an owned Unix socket, cumulatively caps
  bodies at 1 MiB, disables access logs and returns bounded/redacted errors and
  metrics.
- **External capability:** no provider, shell, repository, Git/GitHub, TCP,
  systemd, deployment or other external execution/write path exists in the M4
  runtime. No GitHub Actions or deployed Trust-CI policy, holdout, signing key,
  database state, GitHub App configuration, human approval store or branch
  protection is modified by the full change.

## Verification evidence

- Confirmed clean product HEAD `daa3930...` and exact tree before this report
  write; inspected the complete accepted-base diff and focused collision repair.
- `git diff --check 67714a1...daa3930` passed.
- Independent contracts/state/migrations/service tests passed 24/24.
- The exact-head receipt reports all 14 gates PASS, including source stability,
  the fresh disposable PostgreSQL/API/effective-role suite, same-identity upgrade
  recovery, authority interleavings and actual restart/reconciliation.
- No `.env`, token, private key, credential store, production dump, shared
  database, Trust-CI state or external system was read or mutated. No product
  source, commit, receipt, database, push, merge, release or deployment was
  changed by this review; the only retained repository write is this requested
  report.

## Residual trust boundary

This PASS is local preflight evidence for exact product HEAD `daa3930...`; it is
not merge authority. The final pull-request SHA still requires the GitHub
App-owned policy-epoch Check Run and every independently signed approval scope
required by deployed policy. Any product, base or policy change invalidates this
review binding.
