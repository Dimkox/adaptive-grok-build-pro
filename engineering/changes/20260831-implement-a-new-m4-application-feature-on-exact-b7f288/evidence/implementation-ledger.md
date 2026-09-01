# M4 implementation ledger

## Gate and base binding

- Exact implementation base: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`.
- Clean-base tree fingerprint: `17f8ca8d94a118d02192e5fa0bd9cafc6e219354e390f1d640511d6e6a4fcaa2`, derived by the repository `tree_fingerprint` algorithm before package edits.
- Scope/design: explicitly approved by the user in the active conversation.
- Migration scope: fresh disposable local PostgreSQL only; no external, shared, Trust CI or production write.
- Producer handoff ruling: M2/M3 exact-base/head values remain producer-owned frozen values; M4 validates them and does not replace them with its implementation base.

## TDD cycles

Each vertical records its RED command/result before production source is added, then GREEN/refactor commands. Final real PostgreSQL and root verifier evidence is appended after the last product change.

### Contracts

- RED: `python3 -m unittest factory.tests.test_contracts -v` failed with `ModuleNotFoundError: adaptive_factory`; the package/contract behavior was absent.
- GREEN: the same command passed 5 tests after closed immutable handoffs/intake/limits, canonical digests, M0 freshness/exception and bounds were implemented.
- Focused repair: the first GREEN exposed that a valid App check name contains `@`; the existing failing contract test drove a bounded check-name grammar repair, after which all 5 passed.

### State and retry policy

- RED: `python3 -m unittest factory.tests.test_state -v` failed because `adaptive_factory.state` did not exist.
- GREEN: the same command passed 6 tests covering every state pair, terminality, operator requeue evidence, provider denial, rejected future delivery states and the initial-plus-two closed retry policy.

### Migration foundation

- RED: `python3 -m unittest factory.tests.test_migrations -v` failed because `adaptive_factory.migrations` did not exist.
- GREEN: the same command passed 4 tests for contiguous discovery, immutable checksum planning, drift rejection and factory-only schema markers.
- Ruling: bootstrap creates only `factory.schema_migrations`; all three packaged migrations apply under one factory-specific advisory transaction and never inspect another migration registry.

### Durable intake, leases, capacity and recovery

- RED: `python3 -m unittest factory.tests.test_service -v` failed because the service boundary did not exist; disposable PostgreSQL tests then exposed the four-hour timestamp-boundary check, repository-capacity starvation and expired-grant reconciliation defects.
- GREEN unit: service authorization/bounds passed 3 tests; prior contract/state/migration suite passed 15 tests.
- GREEN PostgreSQL: `FACTORY_TEST_DATABASE_URL=<redacted> ... -m unittest factory.tests.test_postgres_integration -v` passed 4 real PostgreSQL 17 tests in 5.887s after the focused repairs.
- Database-time ruling: task acceptance/deadline, lease expiry and reconciliation use PostgreSQL time. The restart tests expire only the named disposable run row to avoid a 30-second sleep; production callers cannot supply the database clock.
- Restart probe: the bounded subprocess holder/reclaim script passed; one expired lease was repaired, a higher fence issued, and the late heartbeat rejected.

### Local API and CLI

- RED: after installing the approved pinned dependencies into a disposable venv, `test_api` failed because `adaptive_factory.api` did not exist. A later focused RED proved raw contract exceptions escaped instead of producing a safe structured response.
- GREEN: API plus service tests passed 9 tests for constant-time scoped bearer auth, repository authorization, idempotency/correlation, 1 MiB bound, safe errors, typed failures, forbidden endpoint absence and no-follow mode-0600 token loading.
- Boundary: checked-in OpenAPI and CLI expose only local control operations; HTTP transport uses an explicit Unix-domain socket and the CLI has no database, provider, repository, GitHub, systemd or deployment path.
- Cleanup: editable-install `factory/src/adaptive_factory.egg-info` was removed as an exact generated artifact and excluded by `factory/.gitignore`.

### Accounting, audit and role separation

- RED: the real PostgreSQL role/audit regression failed because `verify_audit_chain` was absent; the missing-price regression then failed because `observe_usage` was absent.
- GREEN: targeted PostgreSQL tests prove the three factory roles are `NOLOGIN`, non-superuser and non-creator; runtime has no `trust_ci` usage and no audit update/delete, while audit-reader has read-only access. Chain verification recomputes every bounded digest and head; missing price tables and cost/token/output overflow persist `accounting_blocked` before returning a bounded error.
- RED/GREEN: the migration test required a contiguous `004` repair/event-budget migration before it existed, then passed all four migration tests after the forward-only addition. Event writes now enforce the accepted per-task ceiling, and restart repair counts cannot exceed the persisted semantic-repair ceiling.

### Architecture, delivery surface and documentation

- RED: the architecture regression failed because the factory API/control/database nodes, local-preflight domain and isolated edges were absent. GREEN: architecture model/rules, all five deterministic diagrams, drift and 130 model/fitness tests passed with no Factory-to-Trust-CI/external edge.
- RED/GREEN installer: the payload inventory initially omitted `factory/`; it now includes runtime source, SQL resources, OpenAPI, `uv.lock`, the mandatory disposable verification harness and placeholder local templates, while excluding credentials, sockets and runtime/database state.
- RED/GREEN verifier: a focused test first proved the root verifier omitted nested factory tests; it now runs 19 dependency-free factory contract/state/migration/service tests on every verification and includes factory source in Python quality paths.
- README/roadmap now state accepted M3 base `67714a1...`, truthful M4 candidate status, separate authority, complete K17/136-edge inventory, rollback and installer boundaries.

### Full disposable exit suite before final root verification

- `FACTORY_TEST_DATABASE_URL=<redacted> ... -m unittest discover -s factory/tests -t . -v` passed 30/30 tests, including five real PostgreSQL 17 cases, in 6.431 seconds.
- `postgres_restart_probe.py` passed: one expired holder was reclaimed exactly once, a higher fence issued and the late heartbeat rejected.
- The only database mutation was the fresh local disposable database inside exact container `m4-factory-pg-b7f288`; no Trust CI, shared, external or production state was read or written.

### First root verifier repair cycle

- First post-commit `python3 scripts/grok_verify.py --mode pr` returned `RESULT: FAIL`: architecture fitness rejected the new OpenAPI baseline, standard checksum migration names and HTTP-over-UDS classification; governance failed only as its required architecture predecessor; secret scan matched a literal test credential; Bandit B608 rejected a string-composed lease guard; root tests retained pre-M4 fixtures that omitted the new required contract path plus a stale no-factory assertion.
- The exact root diagnostic ran 483 tests and reported one failure plus 14 errors. The one failure was the historical M3 `test_no_factory_tree`; its M4 replacement positively requires the nested factory package while retaining every root packaging and GitHub Actions prohibition. All 14 errors had one cause: receipt/governance fixtures copied the new architecture model but omitted its required factory OpenAPI Git object; the fixture helpers now copy that declared contract without weakening receipt, handoff, governance or exact-state assertions.
- RED/GREEN rulings: OpenAPI now uses valid bearer security requirements and supported compatibility syntax; factory standard migrations have an immutable-history policy without pretending phased files exist; bounded `httpx.HTTPTransport(uds=...)` is classified as `unix_http` while ordinary HTTPX remains HTTPS; database roles keep a parameterized lease predicate. Dedicated regressions strengthen HTTP exception/UDS classification, and the 15 formerly failing tests, full 131-test architecture suite, 25 dependency/API unit tests, secret scan, Bandit and ruff all pass after these changes.

### Five-review remediation cycles

- RED terminal ownership: leased cancel/supersede left both run/allocation flags false and capacity nonzero; GREEN closes run, attempt, allocation and ordered counters transactionally, rejects the old fence, and makes repeat cancel/reconcile no-ops for reader and writer leases.
- RED accounting: replay of a full reservation raised `BudgetError`, wall could exceed 14,400 seconds, and completion accepted no accounting; GREEN resolves exact replay first, rejects changed evidence, bounds wall/cost/tokens, settles reservations into immutable observations, and requires present/unblocked/settled accounting before completion.
- RED command/auth: repeated API claim returned a second result, proposal replay returned stale-fence, caller M0 assertions and cross-worker/repository grants reached the store, and CLI UUID kills failed; GREEN persists actor/action/request/result/correlation records, canonicalizes headers, binds owner to authenticated worker, checks every task repository/kill scope, and looks up M0 only in immutable provisioned authority tables.
- RED deployment boundary: no server module existed and body framing trusted `Content-Length`; GREEN pre-binds only an owned absolute Unix socket at `0660`, loads closed mode-`0600` actor/token files without following links, executes store connections as `factory_runtime`, and cumulatively bounds streamed bytes.
- RED schema/evidence: migration count was four and effective runtime could update immutable facts; GREEN migration `005` adds trusted authority/command records, accounting fields/composite FKs/keyset indexes and column-level grants. Effective-role SQL now denies accepted-intent, task-event and audit tampering.
- RED verifier: PR `_python` had no PostgreSQL exit check; GREEN adds `factory-postgres-exit`, whose self-provisioning run passed 40 tests and an actual PostgreSQL restart with one repair, zero on replay, higher fence and late-holder rejection.

### Round-two review remediation

- RED null claim: an empty claim returned `grant=null`, but the same command key leased newly arrived work; GREEN serializes the key and persists/replays `{"grant":null}` before every accepted no-grant return.
- RED accounting commands: changed usage under one command key returned 200 and a reservation replay after release returned 409; GREEN binds reservation/usage request and exact result to actor, action, caller command key and correlation, and consults durable replay before live-fence state.
- RED effective role: runtime privilege probes returned `(ceiling_update=True, active_count_update=True, intake_update=True)`; GREEN forward migration `006` returns `(False, True, False)`, while normal intake and capacity operations continue under `factory_runtime`.
- GREEN focused: migration/API/service tests passed 17/17 and ruff passed. GREEN exit: 42/42 factory tests passed on fresh disposable PostgreSQL 17, followed by actual restart, one repair, zero-repair replay, higher fence and late-holder rejection.

### Round-three capacity authority remediation

- RED effective role: runtime retained raw counter INSERT and `active_count` UPDATE, so it could seed ceiling 999, admit repository reader 11, reset the global count and admit reader 21. RED installer/migration tests also showed no schema 007 and no transferred `uv.lock`/exit harness.
- GREEN migration `007` constrains the only valid counter identities/ceilings, revokes raw counter INSERT/UPDATE and allocation INSERT, and grants only fixed-search-path eligibility/lock/allocate/release functions. Readiness and reconciliation now fail closed unless counters equal live allocations; metrics derives live capacity from allocations.
- GREEN boundary evidence: direct forged INSERT, ceiling/reset UPDATE and intake-identity UPDATE are denied under effective `factory_runtime`; normal reader/writer allocation, release, cancel, supersede and reconciliation remain functional, while repository reader 11, global reader 21 and writer 2 return no grant.
- GREEN packaging: all 17 installer tests pass with exact locked dependency and 10-file disposable harness inventory. The fresh PostgreSQL exit suite passes 42/42 plus actual restart, one repair, replay no-op, higher fence and late-holder rejection.

### Round-four allocation release authority remediation

- RED migration: `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_migrations -v` failed because the packaged versions were `[1,2,3,4,5,6,7]`, not `[1,2,3,4,5,6,7,8]`, and the release-authority revoke was absent.
- RED PostgreSQL: the effective-role probe returned `capacity_allocations.released_at UPDATE=True`; an owner-simulated hidden allocation still accepted heartbeat instead of raising `FenceError`. The full disposable runner failed four tests for those migration, privilege and fence defects.
- GREEN migration `008` revokes runtime allocation updates. Grant validation now requires a live matching allocation; redundant allocation row locks were removed because immutable runtime allocations are mutated only by the canonical security-definer release function, while run/task serialization remains.
- GREEN focused: migration tests passed 4/4, installer tests 17/17 and ruff passed. GREEN exit: 43/43 factory tests passed on fresh disposable PostgreSQL 17; direct release/restore DML was denied, owner-simulated hidden allocation fenced heartbeat/release/reservation/usage, reconciliation failed closed without repair, and the supported lifecycle plus actual restart/reconciliation remained green.

### Five-review fix wave on `cf0219b`

- Durable inputs: the overwritten `code-review.md`, `security-review.md`, `test-review.md`, `release-review.md` and `data-review.md` remain unchanged as FAIL evidence. Static path tracing and the reviewers' exact probes confirmed every reported defect; no finding is being waived or weakened for green.
- Intake root cause: the accepted-intent lookup returned on the subset `idempotency_key` without comparing the complete `intent_digest`, so mutually consistent frozen authority/head/limits changes could be discarded as duplicates. M0 trust was also queried on a separate connection using only caller-repeated head/check/timestamp fields, leaving repository/policy subject confusion and a revocation TOCTOU.
- Scope/API root cause: reconciliation and metrics modeled an operator scope but no wildcard repository authority, while API handlers performed raw enum/integer/string coercions outside closed request validation. The repair requires explicit global authority and typed bounded parsing that maps client defects to deterministic 4xx responses.
- Integrity/data root cause: audit hashing omitted stored task/run/correlation identity; completion looked only for current-run reservations; reconciliation locked task before canonical capacity locks; and retained-history predicates lacked task-compatible indexes. Forward migration `009+` and behavioral PostgreSQL tests will bind authority/audit identities, preserve one lock order, make all-task accounting fail closed and prove indexed plans.
- Acceptance/release root cause: event, repair, database-time deadline, repository-kill isolation and >100/5-second reconciliation were implemented but not tested at their boundaries. The shipped compose/example also named a runtime login that bootstrap never created and offered no executable migrator interface; closure requires a disposable shipped-input bootstrap/readiness test, not an improvised external database mutation.

### Fix wave vertical 1 — frozen intent, transactional authority, scoped global controls and closed API

- RED: `uv run --project factory python -m unittest factory.tests.test_contracts factory.tests.test_service factory.tests.test_api -v` ran 22 tests with 11 failures and one error. Complete frozen authority/evidence/limit changes retained the same key, observed policy mismatch was accepted, repo-scoped global controls reached the store, the service performed a separate M0 lookup, and eight malformed command cases returned 500/200 instead of bounded 4xx.
- GREEN: contracts/service/API/migration tests passed 26/26 and ruff passed. Duplicate identity now binds the full normalized intent; policy/check identity is structurally consistent; global reconciliation/metrics require wildcard authority; and closed parsers bound enum, UUID, scalar, collection, digest, reason and cursor inputs before store access.
- RED PostgreSQL migration: the first fresh run exposed PostgreSQL's truncated auto-generated constraint name, then `FOR KEY SHARE` correctly failed under the deliberately non-updatable runtime role. GREEN uses the exact constraint and fixed-search-path `SECURITY DEFINER` validation functions, retaining narrow EXECUTE-only runtime authority while locking authority rows against concurrent revocation.
- GREEN PostgreSQL: three focused tests passed against fresh PostgreSQL 17: complete head/authority/limit changes supersede exact replay, repository/policy/action mismatches and an advisory-gated concurrent revocation fail closed, and audit task/run/correlation fault injection invalidates the version-2 chain. Migration `009` retains legacy version-1 verification for already durable evidence while every new row uses the complete version-2 envelope.

### Fix wave vertical 2 — accounting recovery, lock order, acceptance bounds, credentials and rollout

- RED PostgreSQL: the cross-attempt probe returned `retry` with a live full-budget reservation; the capacity-held two-connection probe reproduced `DeadlockDetected` between reconcile and cancel. GREEN moves unresolved failed-run accounting to `needs_human` with `accounting_blocked`, checks every task reservation/counter before completion, and makes reconciliation take capacity locks before task/run locks; both focused regressions pass.
- GREEN acceptance boundaries: real PostgreSQL tests consume the last permitted event and prove rollback on the next transition, exhaust the persisted repair cap, reject DB-time-expired claim and heartbeat, isolate a valid repository kill, and assert the effective reconciliation transaction setting is exactly `5s`. A valid capacity snapshot has at most 21 live leases, so the defensive >100 test temporarily removes and then restores only the disposable counter ceiling check; it proves pages of 100 then 1 and exact replay without claiming 101 candidates are reachable in valid state.
- GREEN data plans: `EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON)` at retained-history volume proves `tasks_claim_queue`, `audit_log_task_order`, `usage_observations_task_run`, `budget_reservations_task_run_active` and a reconciliation keyset/expiry index are selected. Migration `009` is forward-only; applied migrations `001..008` were not edited.
- RED/GREEN credential boundary: relative paths, ancestor symlinks, unavailable no-follow support and foreign leaf ownership were accepted or unchecked; absolute descriptor-walk tests now pass for actor and token files, including trusted ancestry and owner/mode enforcement. A real UDS server test rejects missing auth then accepts the scoped bearer without TCP.
- RED/GREEN rollout: the shipped example named a nonexistent runtime login and exposed no migrator command. `adaptive-factory-admin bootstrap-local` now applies checksummed schema `009` via the distinct owner DSN, provisions or validates a bounded `NOINHERIT` runtime login, grants only `factory_runtime`, and proves readiness through the runtime DSN; the disposable effective-role test and 17/17 installer tests pass.

### Fix-wave exit verification

- Fresh disposable exit attempt one passed 37 dependency/API tests, then PostgreSQL closed the first TCP connection immediately after `pg_isready`; no migration ran and the runner removed its exact container. A second fresh run passed 59/59 in 30.687s, then passed actual restart, one repair, replay no-op, higher fence and late-holder rejection; its exact container was removed.
- Root RED: `python3 -m unittest discover -s tests -v` ran 488 tests in 314.727s with one failure because the new admin source was not owned by the executable architecture model. GREEN: adding that exact source to the existing factory service node made the focused regression pass; architecture validate, drift and all five generated diagram checks pass without changing trust edges.

### Final verifier repair cycle

- RED: the first clean `python3 scripts/grok_verify.py --mode pr` passed source stability, unit, coverage and quality checks but failed architecture fitness because newly authored migration `009` contained a destructive `DROP CONSTRAINT`; governance failed only through that prerequisite. Secret scan also reported three literal test-only credentials, and the disposable PostgreSQL exit returned 1 after the image bootstrap/postmaster handoff closed its first host TCP connection.
- GREEN architecture/security: migration `009` retains the historical uniqueness constraint and no longer performs destructive SQL; repository-specific authority fixtures use distinct deterministic observation instants. This correction changes only the unaccepted, disposable-only migration authored in this fix wave: every database to which its earlier draft was applied was an exact disposable container and was destroyed, while immutable accepted migrations `001..008` remain byte-identical. Architecture fitness now passes and the three focused files report zero potential secrets without weakening authentication behavior.
- GREEN exit harness: after the first successful `pg_isready`, the disposable runner allows the image's one-time bootstrap/postmaster handoff to settle before opening host TCP clients. This is a bounded one-second readiness stabilization, not a database or product retry; the runner retains its existing deadline and exact-container cleanup.
- RED fresh exit: 58/59 tests passed; the authority-scope case failed before its database assertion because a hard-coded bootstrap-exception expiry crossed the actual run date. GREEN fixture: the expiry is now ten minutes after the test's captured UTC instant, preserving the production ten-minute bound and the repository/policy/action assertion without calendar coupling.
- GREEN fresh exit: the corrected suite passed 59/59 in 30.541s on fresh PostgreSQL 17, then passed an actual restart with one repair, replay no-op, higher fence and late-holder rejection. The runner removed its exact disposable container and temporary environment.
