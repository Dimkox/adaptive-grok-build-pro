# Test review round 4 — M4 durable factory control plane

## Verdict

**PASS**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed head SHA: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Exact-head verification fingerprint: `463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4`

No Critical or Important test, behavioral-contract, PostgreSQL restart/reconciliation, failure-path, installer-reproducibility, effective-role, or verifier-inclusion gap remains in the reviewed tree. The requested capacity and runtime-policy behavior passed against fresh disposable PostgreSQL 17 both in the source checkout and in an independently materialized install.

## Findings

No Critical or Important findings.

### Minor — capacity threshold filling remains sequential

The suite proves one-task transactional contention with two worker threads (`factory/tests/test_postgres_integration.py:369`) and proves the exact reader and writer thresholds against PostgreSQL (`factory/tests/test_postgres_integration.py:428`), but the 20/21, repository 10/11, and writer 1/2 threshold-filling claims are sequential. A future hardening test should place simultaneous claim transactions at each last-slot boundary. This is not a release blocker: database-owned allocation locks and constraints enforce the policy (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1`), the separate contention test exercises concurrent claims, and both fresh-database runs passed all exact boundary assertions.

### Minor — no full HTTP-over-UDS round trip is automated

The server test proves an owned `AF_UNIX` socket at mode `0660`; API/auth behavior is exercised in-process, and the CLI is configured for UDS transport. The suite does not start Uvicorn and send an authenticated request through the actual socket. This is outside the round-four blockers but remains useful rollout hardening.

### Minor — the exit runner does not explicitly remove its anonymous volume

`factory/tests/run_disposable_exit.py:55` removes its uniquely named container with `docker rm -f` but omits `-v`. The runner remains isolated and removed its containers in both successful runs; explicit volume removal would prevent disposable PostgreSQL volumes accumulating locally.

## Requested round-four coverage

| Required evidence | Concrete observation | Result |
| --- | --- | --- |
| Repository reader 11 boundary | The test submits 11 tasks for `repo/a`, claims 20 readers over `repo/a` and `repo/b`, and asserts exactly 10 grants belong to `repo/a`; the 11th remains unleased (`factory/tests/test_postgres_integration.py:428-444`). | PASS |
| Global reader 21 boundary | Exactly 20 reader grants are collected, followed by an explicit `reader-21` claim asserted `None` (`factory/tests/test_postgres_integration.py:443-450`). | PASS |
| Writer 2 boundary | Two writer tasks are submitted; writer 1 receives a grant and writer 2 is explicitly asserted `None` (`factory/tests/test_postgres_integration.py:462-471`). | PASS |
| Runtime DML denial | Privilege queries assert runtime cannot insert/update counters or update intake identity; attempted counter ceiling update, active-count update, forged counter insert, identity update, audit/event/intent changes all raise `InsufficientPrivilege` under `SET LOCAL ROLE factory_runtime` (`factory/tests/test_postgres_integration.py:614-656`). | PASS |
| Normal lifecycle after DML denial | The same effective-role test claims a reader lease through the security-definer API, records usage, releases it, and verifies readiness remains `ready` (`factory/tests/test_postgres_integration.py:657-668`). | PASS |
| Reconciliation and capacity repair | Orphan plus valid expired lease repair returns `(candidates=2, repaired=2)`; immediate replay repairs zero; no live allocation and global reader count zero remain (`factory/tests/test_postgres_integration.py:407-426`). | PASS |
| Installer reproducibility | Installer inventory includes `factory/uv.lock`, the exit runner, restart probe, and every factory test (`scripts/install_into.py:24-41`; `tests/test_installer.py:155-190`). A new materialized install independently ran all 42 tests and actual restart/reconciliation successfully. | PASS |
| API/command idempotency | Successful API claim/proposal/kill replays, changed-payload conflicts, empty-claim replay, budget/usage replay before stale-fence validation, persisted correlations, and command-key serialization remain covered (`factory/tests/test_postgres_integration.py:211-367`). | PASS |
| Leased cancel/supersede | Reader cancellation and writer supersession release run, allocation, and counters once; reconciliation remains clean (`factory/tests/test_postgres_integration.py:79`). | PASS |
| Actual PostgreSQL restart/fencing | The restart probe performs an actual container restart, reconnects, repairs once, replays with zero repairs, issues a higher fence, and rejects the stale holder. This passed in source, installed copy, and exact-head verifier evidence. | PASS |
| Root verifier inclusion | PR/release verification adds `factory-postgres-exit` whenever the runner exists (`.grok-stack/adaptive_grok/verification.py:589-597`). The exact-head receipt records it, `factory-unit`, and `source-stability` as PASS. | PASS |

## Test honesty and failure paths

- Capacity is no longer trusted to runtime table DML. Migration 007 fixes canonical ceilings in a table constraint, revokes runtime counter/allocation DML, and exposes only bounded `SECURITY DEFINER` functions with a fixed search path (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-169`).
- The boundary test can fail for each named off-by-one case: it asserts total grants, repository-specific grants, explicit reader 21 rejection, and explicit writer 2 rejection. It does not infer success merely from counter contents.
- The effective-role test combines privilege metadata with executed forbidden statements, then proves allowed product behavior still works. This avoids a false positive where revocation passes but the ordinary lifecycle is unusable.
- The disposable exit runner fails closed on missing Docker/`uv`, dependency/install failure, PostgreSQL readiness failure, any test failure, or restart-probe failure. Its output proves the database process was restarted rather than only recreating a service object.
- Idempotency checks compare replay response bodies, assert changed commands return conflict, inspect persisted command results/correlations, and cover empty results plus replay after the original fence becomes stale.
- The installer check was not inventory-only: `scripts/install_into.py --materialize-new` created a fresh target and that target's own exit runner built the package from the installed path and passed the full PostgreSQL suite.

## Commands and results

```text
git rev-parse HEAD
  9fd2a56c57f834ad39c03a2f748bdbaefc79c91c

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
  PASS (no output)

python3 factory/tests/run_disposable_exit.py
  PASS: 42 tests in 16.309s
  PASS: PostgreSQL restarted; one repair; replay no-op; higher fence; late holder rejected
  PASS: disposable PostgreSQL + API + effective roles + actual restart/reconciliation

python3 scripts/install_into.py --materialize-new /tmp/m4-r4-install.QvJwcA/installed
  PASS: materialized verified payload including lockfile, migrations, exit runner, restart probe, and tests

(cd /tmp/m4-r4-install.QvJwcA/installed && python3 factory/tests/run_disposable_exit.py)
  PASS: package built from the installed path
  PASS: 42 tests in 15.717s
  PASS: actual PostgreSQL restart; one repair; replay no-op; higher fence; late holder rejected

exact-head verification receipt inspection
  PASS: status=pass
  PASS: head=9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
  PASS: tree_fingerprint=463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4
  PASS: git-diff-check, factory-unit, factory-postgres-exit, and source-stability
  factory-postgres-exit: 42 tests in 16.220s plus actual restart/reconciliation PASS
```

The independently materialized disposable install was moved to trash after testing and is recoverable there. Both exit-runner containers were removed by their runners. No shared, Trust CI, external, or production database was read or mutated.
