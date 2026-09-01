# M4 final security re-review — PASS

## Reviewed identity

- Route: `b7f288f1e81e`
- Change: `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
- Exact base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Prior residual-review HEAD: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698`
- Exact final product HEAD: `83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact Git tree: `c8bc3eee0beb54a18c61f941a4d8ad5d6dc0a8e2`
- Focused residual-fix range: `4230dc8e73bcf4dfcf6c60d294d379d44a30c698..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..83e6b0d0c29e813932aa29b0d72ac4d85d27df7b`
- Exact-head verifier: PASS, fingerprint `9a9dd64921cc5edf8889330b79732016c0235cc37e4a27c712a05128b3659746`
- Reviewer: route-selected read-only `security_reviewer`

## Verdict

**PASS**

- Critical findings: **0**
- Important findings: **0**
- Moderate findings: **0**

No security finding at Moderate severity or above remains on the exact reviewed
HEAD. The previous M0 revocation race is closed, and the residual accounting and
mandatory-cleanup repairs preserve rather than weaken the established trust
boundaries.

## Residual finding closure

### M0 revocation serialization — closed

Forward migration `010` replaces both authority validators with fixed-search-path
`SECURITY DEFINER` functions whose matching row is selected `FOR SHARE`
(`factory/src/adaptive_factory/resources/010_authority_accounting_and_cleanup.sql:1-30`).
That lock conflicts with the `FOR NO KEY UPDATE` lock taken when `revoked_at` is
changed, and it remains held through the surrounding intake transaction. The
accepted-intent write therefore has a defined serial order with revocation:

- revocation committed before validation makes both observation and exception
  validation return false;
- revocation started after successful validation blocks until the successful
  intake transaction commits, and subsequent intake using that revoked authority
  is rejected.

The real PostgreSQL regression covers both authority forms and both orderings.
Its after-validation case pauses inside the intake transaction after the validator
returns, proves the revoker remains blocked, releases intake to commit, compares
commit ordering, and then proves later use fails
(`factory/tests/test_postgres_integration.py:235-316`). This directly exercises
the interleaving missed by the prior advisory-lock test.

Migration `010` does not broaden the definer boundary. Both functions retain
static, schema-qualified SQL, `search_path=pg_catalog,factory`, PUBLIC execution
revocation and EXECUTE-only `factory_runtime` grants
(`010_authority_accounting_and_cleanup.sql:1-36`). Applied migrations `001..009`
remain unchanged.

## Accounting upgrade, claim and cleanup review

- The schema-008 upgrade path preserves active reservation evidence and aggregate
  counters while moving unsafe queued/retry projections to
  `needs_human/accounting_blocked`; it neither releases nor erases accounting
  evidence (`010_authority_accounting_and_cleanup.sql:38-70`). The separately
  constructed non-empty 008 database test proves only migrations 009/010 apply,
  readiness becomes consistent, and the quarantined task cannot be claimed.
- Runtime readiness independently fails closed if a queued/retry task is blocked,
  has non-zero reserved counters or retains an active reservation
  (`factory/src/adaptive_factory/store.py:66-94`). Claim repeats the safety
  predicates in its locked candidate selection, so an owner-only projection fault
  cannot bypass quarantine (`store.py:513-525`).
- Ordinary task events remain capped by the accepted event limit. Only internal
  release, reconciliation/orphan cleanup, cancellation and supersession facts are
  marked `mandatory_cleanup`; callers cannot select that flag through the closed
  API. Those paths are state/fence/idempotency bounded and append the existing
  hash-chained audit in the same transaction.
- An exhausted ordinary-event budget can no longer roll back run/allocation/counter
  release. It also cannot create an unclaimable retry loop: before choosing retry,
  release checks remaining ordinary capacity and routes exhaustion to
  `needs_human` (`store.py:192-231,686-760`). Real PostgreSQL tests prove one cleanup
  event, one audit fact, zero live allocation/counters and replay without a second
  release for release/reconcile/cancel paths.
- Audit version 2 still authenticates task, run, correlation, actor, action,
  resource, reason, timestamp and canonical metadata; runtime audit update/delete
  remains denied. Mandatory cleanup does not skip `_audit` or weaken chain
  verification.

## Rechecked prior security closures

- M0 observations/exceptions remain bound to exact repository, full policy digest,
  closed intake action, trusted row identity, expiry/non-revocation and governance
  exact head. Legacy unbound rows remain fail-closed.
- M2/M3 producer provenance and matching architecture digest/exact base/head pairs
  remain closed and immutable; M4 records those values and does not manufacture or
  claim Trust-CI authority.
- Global reconciliation and metrics require operator kind, explicit scope and
  wildcard repository authority. Worker claims and mutations remain bound to the
  authenticated actor, repository, task/run, live allocation, owner, fence, packet,
  lease/deadline and budget state.
- Capacity authority remains in fixed-search-path, PUBLIC-revoked definer
  functions with canonical 20/10/1 ceilings; runtime cannot forge counters,
  allocations or allocation release. Readiness and reconcile still fail closed on
  drift.
- Actor and token files still require absolute normalized paths, capability
  availability, descriptor-walked no-follow ancestry, trusted ownership, a private
  owned final parent and an owned regular mode-`0600` leaf. Bearer comparison is
  constant-time; request bodies are cumulatively capped at 1 MiB; errors and
  metrics remain bounded/redacted; the listener remains owned UDS-only.
- No provider, shell, repository, Git/GitHub, systemd, deployment, TCP service or
  other external execution/write path was added. No GitHub Actions, deployed
  Trust-CI policy/holdout/key/state, GitHub App configuration, human approval store
  or branch-protection boundary changed.

## Verification evidence

- Inspected the active route/change package, prior FAIL report, implementation
  ledger/report, complete base-to-head diff, focused `4230dc8..83e6b0d` diff,
  migration `010`, store paths and the real PostgreSQL regressions.
- `git diff --check 67714a1...83e6b0d` passed.
- Independent focused contracts/state/migrations/service run passed 24/24.
- The exact-head verifier receipt reports all gates PASS, including source
  stability and 63/63 fresh disposable PostgreSQL/API/effective-role tests plus an
  actual PostgreSQL restart, one reconciliation repair, replay no-op, higher fence
  and late-holder rejection.
- No `.env`, token, private key, credential store, production dump, shared
  database, Trust-CI state or external system was read or mutated. No product code,
  commit, receipt, database, push, merge, release or deployment was changed by this
  review; the only retained repository write is this requested report.

## Residual trust boundary

This PASS is local preflight evidence for exact product HEAD `83e6b0d...`; it is
not merge authority. The final pull-request SHA still requires the GitHub
App-owned policy-epoch Check Run and every independently signed approval scope
required by deployed policy. Any product commit or policy/base change requires
fresh exact-head verification and review evidence.
