# Independent security review — issue #155 continuation

Reviewer: route-selected `security_reviewer`, independent of the implementation owner.
Route: `c4e47ea3ced7`. Review date: 2026-09-21.

**Result: FAIL for the inspected delivery snapshot.** The recovery instructions below
would break an upgraded deployment. The remaining NULL traceback defect also needs the
announced implementation correction and a delta review. No new authorization bypass,
cross-repository binding, privilege expansion, injection, or HTTP disclosure was found in
the inspected SQL/Python change. This report is local review evidence, never merge or
deployment authority.

## Inspected identity

- Worktree: `/home/pall/grok-projects/adaptive-grok-build-repair`.
- Base: `90078959ff816068af374ad42f4bb80fdbaec866`.
- Inspected HEAD: `4a47c76b3fb37fbac430fd209771a695832610d2`.
- Product-content manifest: `e33e5e4846200ca06c3f01b3be48f4e90e9e99e2ad3ac080d7dddd3e8922a9a4`.
- Independently hashed all eight changed `factory/` files and matched every hash to
  `continuation-20260921/product-manifest.json`. There was no uncommitted `factory/`
  diff when checked. The implementation hashes observed again after the probes were:
  - `021_semantic_repair_child_rejection_reasons.sql`: `868bc21f47351f92b79acb8bd8e9390c62b43803c0b5761400e32c7143d56d5e`.
  - `semantic_repair.py`: `f20757f9b4b02fed2ba331aa664ff442fbe46947241a4e09c6dc26c56efb2a07`.
  - `store.py`: `e8d365359ebfadbe1cb13224dc572eaf01fa2a751e40ee9962ff21a3bf07dcaa`.

The controller is changing delivery documents and has announced a subsequent product
fix. Neither that future fix nor its new test results are approved by this snapshot
review. The manifest intentionally excludes the active change package, README,
START_HERE, PROJECT_STATE, decisions, mistakes, and machine-local runtime; it is not a
full-tree or exact-head attestation.

## Findings

### P2 — recovery instructions would make the installed schema incompatible with the package

Location at inspected HEAD: `rollback.md`, Application rollback and Data recovery /
forward-fix paragraphs (lines 15–24), under this change package; relevant implementation:
`factory/src/adaptive_factory/migrations.py:69–79`.

The instructions say a source revert re-applies 018 through the same migration mechanism
and leaves an applied 021 harmless. Applied migrations never rerun; moreover,
`plan_migrations` rejects an applied 001–021 database when available resources end at 020.
An offline call using the actual discovered migrations and 21 `AppliedMigration` records,
with `available=migrations[:-1]`, raised exactly
`MigrationError("applied migration is missing from package")`. Following the old recovery
instructions could therefore prevent startup/readiness during recovery.

Required correction: retain immutable resources 001–021 and ship a separately reviewed
additive corrective migration, such as 022, with compatible application behavior. Do not
remove the applied migration row, edit shipped SQL, or claim a source-only revert restores
the old function. Reported to the controller; the controller confirmed the correction is
being made. Final document confirmation remains outstanding for this snapshot.

### P2 — legacy NULL still creates the misleading contract-error traceback

Location: `factory/src/adaptive_factory/store.py:752–761` at inspected HEAD.

The NULL arm is entered only after `RepairChildTaskBindingV1.from_dict(None)` raises a
`ContractError`, and the new `StoreError` is raised `from exc`. An independent mock-store
probe observed the correct outer `store_returned_null` message but
`error.__cause__.code == "invalid_object"`, and `traceback.format_exception(error)` still
contained `invalid_object`. This preserves the misleading diagnostic in logs/tracebacks;
it does not expose that diagnostic through the existing HTTP handler.

The controller separately received this finding from code review and assigned the fix to
the sole implementation owner. Classify NULL before contract parsing and retain malformed
payload contract errors for genuinely malformed non-NULL responses. A fresh product
identity, regression evidence, and delta review are required after that edit.

## Security boundary assessment

- **Assets and actors:** accepted intents, M0 observations, repair proposals and binding
  lineage are protected database state. HTTP operators are repository-scoped; the
  coordinator database capability is a trusted application role, not a tenant credential.
  Validators, adjudicators, runtime workers and PUBLIC must not gain bind execution.
- **Privilege and object lookup:** 021 preserves the `(char,text) -> jsonb` signature,
  `SECURITY DEFINER SET search_path=pg_catalog,factory`, schema-qualified application
  relations/types, and static parameterized SQL. It repeats PUBLIC revocation and grants
  execution only to `factory_semantic_coordinator`. Resources 001 and 018 revoke PUBLIC
  schema/table privileges; 018 grants schema USAGE without CREATE and rejects unsafe
  capability-role attributes/memberships. `store.py:118–210,309–331` checks the dedicated
  login/role boundary before `SET ROLE`. No dynamic SQL, new object ownership, or new
  grant was introduced.
- **Migration immutability:** independently compared all resources 001–020 byte-for-byte
  with `git show <base>:<path>`; all 20 matched. Only additive 021 changes the function.
- **Authorization and lineage:** `service.py:335–340` checks scope, operator kind and the
  parent repository before repair work. The broker binding must match the proposal
  (`service.py:361–371`). SQL 021 retains the broker actor, source identity, repository,
  parent/child policy, subject/head, non-revoked observation, issuer, freshness, deadline,
  and budget conditions before INSERT. The two freshness comparisons still require
  nonnegative ages no greater than 300 seconds. No time window or timeout changed.
- **Guard partition:** reviewed 018's body against 021 and ran the existing independent
  guard-text/structure assertions. Splitting the contiguous OR block into returning IF
  blocks preserves whether any clause is TRUE; NULL predicates do not newly authorize a
  row. Replays still return the exact existing binding before later lineage checks, as in
  018; this is a preserved idempotent path, not a new write bypass.
- **Input/output separation:** `semantic_repair.py:73–80` requires exactly the rejection
  key, accepts only fixed string codes, and folds unknown/non-string values to
  `binding_rejected`. Extra-key documents remain subject to the closed four-key binding
  parser. `store.py:765–766` checks the returned binding and digest against the requested
  one. SQL JSON/cast/constraint failures keep the fixed `store_write_rejected` channel;
  no SQL exception text or row contents are concatenated into reason strings.
- **Information disclosure:** names such as `proposal_not_pending` and
  `child_task_unavailable` reveal a finite predicate result to a holder of the trusted
  coordinator database capability. That role is not repository-scoped at the SQL-login
  boundary and must remain internal. No new direct HTTP bind route was found; the current
  service repair method authorizes the parent repository. The existing HTTP StoreError
  handler (`api.py:384–388`) ignores exception text and returns the same generic
  `409/store_conflict` for all reasons. The in-process HTTP probe below confirmed this.
- **Malformation limits:** the pre-existing `json.loads` call remains outside the
  contract-error wrapper. Arbitrarily malformed JSON text from a broken/mock database
  adapter is not guaranteed a typed StoreError; 021's actual jsonb response does not
  manufacture such text. No new public detail exposure follows because the generic
  exception handler is also redacted. This review does not expand the repair into adapter
  corruption handling or the separate `semantic_plan_repair` NULL channel.

## Checks run by this reviewer

Read AGENTS, START_HERE, PROJECT_STATE, active route, the assigned reviewer definition,
adaptive-delivery/security-sensitive-change and route skills, the typed change spec and
design/recovery documents. Inspected the actual base-to-HEAD SQL/Python/test diff, 018's
function and grants, 001's schema revocation, store role validation, migrations, service
callers, API handlers and existing role/lineage tests. `grok_status.py` correctly reported
review receipts absent/stale while the controller was preparing documents; no receipt
was generated by this reviewer.

Executed, exit 0, **17 tests passed in 0.268 seconds**:

```bash
python3 -m unittest -v \
  factory.tests.test_migrations.MigrationTests.test_repair_child_rejection_resource_is_additive_and_typed \
  factory.tests.test_migrations.MigrationTests.test_repair_child_rejection_reasons_match_the_python_allowlist \
  factory.tests.test_migrations.MigrationTests.test_repair_child_rejection_channel_stays_disjoint_from_bindings \
  factory.tests.test_migrations.MigrationTests.test_bind_repair_child_separates_an_unexplained_store_refusal \
  factory.tests.test_migrations.MigrationTests.test_repair_child_guard_structure_maps_each_reason_to_one_clause_group \
  factory.tests.test_migrations.MigrationTests.test_semantic_migration_is_additive_append_only_and_capability_shaped \
  factory.tests.test_migrations.MigrationTests.test_semantic_evidence_functions_are_reserved_to_distinct_capabilities \
  factory.tests.test_semantic_repair_lifecycle \
  factory.tests.test_api.ApiTests.test_declared_errors_are_normalized_correlated_and_preserve_auth_challenge \
  factory.tests.test_api.ApiTests.test_unexpected_failures_are_redacted_normalized_and_correlated
```

Also ran three short inline Python probes, without database connections or repository
mutations:

1. Mocked `PostgresSemanticCoordinatorStore._connect` and returned each of the 13 Python
   allowlist strings plus an unknown newline-containing string, `None`, `True`, `[]`,
   and `{}` as the exact envelope value. All **18** cases raised only the expected fixed
   StoreError message with no chained cause. Passed that StoreError through a mocked
   intake method in the existing `ApiTests` TestClient: every response was HTTP 409 with
   exactly `{"error":"conflict","code":"store_conflict","detail":"stored command conflicts with request"}`.
2. Called `plan_migrations` with the actual 20-resource prefix and 21 applied records;
   confirmed the recovery failure quoted above.
3. Mocked the actual store response as SQL NULL; confirmed `store_returned_null`, a
   `ContractError invalid_object` cause and `invalid_object` in the formatted traceback.

## Existing verification evidence inspected, not rerun

Validated SHA-256 and byte lengths against `continuation-20260921/index.json` for the
manifest, verifier JSON, streak JSON and each of the four raw PostgreSQL logs.
`verify-initial.json` records a passing full verifier for HEAD `4a47c76...`, full-tree
fingerprint `47e8786408161ac022726c66045b006df1cb07e32d60a4375d7c9889aeab2f3d`, including
785 root tests, 779 PostgreSQL-tier tests, role/restart success and passing source
stability. Four recorded tier attempts exited 0 at the reviewed product-content hash:
353.544, 353.178, 355.034 and 360.154 seconds. The logs consistently report two skips:
the separately configured fresh PG17 cluster test and the unavailable-PDF-parser branch
when the pinned parser is installed. These are not claimed as executed coverage.

The four runs span documentation commits and therefore prove stable product contents,
not four identical Git heads. They become historical evidence when the announced NULL
fix changes the product. Fresh final-content verification remains the controller's task.

## Limitations and handoff

No database, deployed role, production service, remote Git, credential file, private key,
approval authority or external holdout was accessed. No product/test/configuration file
was edited; the assigned report is the only repository write. No full suite was rerun.
Actual database execution is supported by the controller's inspected logs, not a new
live run by this reviewer. Deployed policy, approval scopes, branch protection and
exact-head App-owned Trust CI still independently govern merge eligibility.

Final security receipt must wait for the corrected recovery document, the NULL-path
delta and its new verification evidence. Do not reuse this snapshot result as a pass for
changed product contents.
