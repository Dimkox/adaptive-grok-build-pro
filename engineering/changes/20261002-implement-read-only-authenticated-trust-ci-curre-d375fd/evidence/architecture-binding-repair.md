# Focused architecture binding repair — 2026-10-02

## Source identity and authority

Repair started at HEAD `49330e1a759df74a124c832677ee3639f4f67ed4`, which already contains implementation `7902c6b0e` and actual main `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. The controller owns full verification, independent reviews, receipts and delivery. These focused results are not a passing full receipt or merge authority.

Startup capacity was measured before repository inspection and recorded first at `/tmp/v211-g-architecture-repair-capacity-20261002T231929Z.json`, then copied to `startup-architecture-repair-20261002T231929Z.json`. Verified capacity: 28 allowed online CPUs, 14 physical cores, no finite cgroup quota; this repair uses only CPUs 24,25 and at most two focused workers. No subagents were spawned.

Read the full 724-line failed runtime report and preserve it byte-for-byte as `verification-failed-49330e1-20261002.json`; SHA-256 `7a0b1a1f84dc79c05f57fd15a18cbed6261ace2d668b7d404fd94e923eea62aa`. It is historical failed evidence: architecture/governance and one Core binding test failed, other 998 Core tests and factory/PostgreSQL passed; coverage was not qualified because Core failed.

## Actual repair

- Register `authority.py` under existing `NODE-TRUST-CI-API`.
- Move only `store.py` source ownership from `NODE-TRUST-CI-POSTGRES` to that existing API owner, following the independent architect and coordinator ruling. The Python adapter's pre-existing client connectivity is already represented by `EDGE-API-POSTGRES` and `FIT-DECLARED-NETWORK-ONLY`.
- Preserve every node, edge, runtime, trust, secret and rule attribute. No architecture rule waiver or new service/network behavior is introduced.
- Add the authority path to the existing exact OpenAPI binding expectation without deleting any prior path. Add a regression asserting unique API ownership for authority/store and the retained edge and strict network policy.
- Replace the timeout test's driver import used only for exception type inspection with exact PostgreSQL cancellation SQLSTATE `57014`. Keep the actual exclusive lock, query and elapsed-time bounds unchanged.
- Record the missing mandatory ownership/contract preflight root cause in root `mistakes.md`. Frozen scope files and approval binding were updated only by the coordinator and are included unchanged.

## RED and GREEN

1. `taskset -c 24,25 python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts -v`: RED on undeclared authority source. After registration, RED on missing authority path in the exact OpenAPI expectation.
2. `taskset -c 24,25 python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_trust_ci_api_owns_authority_and_store_with_existing_database_policy -v`: RED before source move (`NODE-TRUST-CI-POSTGRES` != `NODE-TRUST-CI-API`).
3. `taskset -c 24,25 python3 -m unittest tests.test_architecture_model tests.test_structure -q`: GREEN, 104 tests in 2.581 seconds after the authorized source move.
4. `taskset -c 24 python3 scripts/grok_architecture.py validate --json`: exit 0, `ok: true`, no findings.
5. `taskset -c 25 python3 scripts/grok_architecture.py drift --json`: exit 0, `ok: true`, no findings.
6. `taskset -c 25 python3 scripts/grok_architecture.py diagram --check --json`: exit 0, no mismatches. All five generated diagram digests are unchanged; no regeneration was needed or performed.
7. `TRUST_CI_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:33020/authority_binding_test PYTHONPATH=trust-ci/tests taskset -c 24,25 python3 -m unittest test_postgres_integration.PostgresIntegrationTests.test_current_approval_query_statement_timeout_is_enforced -v`: GREEN, one test in 4.227 seconds. `psycopg.errors.QueryCanceled.sqlstate` was independently observed as `57014`.

The one changed PostgreSQL assertion used disposable `postgres:17.6-bookworm`, image `sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`, fixture ID `17a60641ccf0515617a0af9defcc415957e1610feded28e317fe3d157e08d2a9`, loopback-only port 33020, CPUs 24,25/max two CPUs, 512 MiB, synthetic database and roles. No host/deployed data mount. Exact fixture and its anonymous volume were removed after the test. No deployed database, trust source or key was accessed.

## Remaining preflight findings — not passed

Fitness ran against both historical route base `e5856acfd4bc7a186f40a740b54ec86459462db5` and actual agreed PR base `63799f8760d3a55028d83ab5ff0116ececf8f7d1`. At the actual PR base, `taskset -c 24,25 python3 scripts/grok_architecture.py fitness --base 63799f8760d3a55028d83ab5ff0116ececf8f7d1 --worktree --pre-risk red --json` exits 1. Network-client fitness now passes, but two previously masked findings remain:

- `FIT-TRUST-CI-SEPARATION`: the existing implementation prefixes include `architecture` and `engineering/contracts`; the required model/OpenAPI binding and approved Trust CI source therefore count as mixed implementation/trust-ci paths even at the actual PR base.
- `FIT-OPENAPI-BIDIRECTIONAL`: `CONTRACT-TRUST-CI-OPENAPI: changed_constraint`. The comparator in `architecture.py` flags any component-name inventory change; the approved new `CurrentAuthoritySnapshotV1` component changes the previously empty schema inventory, while the prior operations/security remain untouched.

The bounded machine summary is `architecture-repair-fitness-preflight.json`. These findings were reported to the coordinator; no rule, exemption or contract change was made to suppress them. The unchanged 277-test API suite and full PR verifier were not repeated by this repair writer. Fresh full verification and independent selected reviews remain controller obligations.
