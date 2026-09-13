# B/C prerequisite correction and confirmed extraction

Read-only comparison of genuine main `4b3ad5e8ec1e9fc426caaacd3cbf3f4d6e72c102` with frozen source `f31406e970d67f7cd59694da5de88915adb0fa68`, together with `/tmp/agbp-sweep/split-final-integration.md`. No repository edits, tests, secret reads or external actions. This report only amends the approved delivery manifest; it does not expand the audit.

## Mandatory shared-test correction

`tests/test_architecture_model.py` contains three frozen hunks and must be split:

- **A now:** the first hunk, base line 653 / final line 656, in the closed-object-schema check permits only `allowed_dependency_modules` to be optional in `$defs.path_boundary`. Its previous assertion requires every property to be required, so schema support without this test update is inconsistent. This corrects the prior A report's five-path estimate: A has six product/test paths.
- **C:** the base line 1315 / final line 1318 hunk changes the actual contract count from 40 to 41 and asserts the exact V1/V2 provider-evidence record versions/paths.
- **C:** the base line 1368 / final line 1379 hunk adds `CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V2` to the expected landing contract IDs.

Also retain the already identified **C** hunk in `tests/test_architecture_fitness.py` changing the seven-contract count into the exact eight-ID set. Its earlier boundary regression block belongs to A. After C, both root architecture test files can equal their frozen final contents without importing any D-to-G product modules.

## B confirmed path/hunk set

Take final whole `landing_renderer.py`, `landing_evaluation.py`, `landing_artifact.py`. Include `ExactGitLandingWorkspace.validate_source()` here, as the approved map directs. In retention take only: `DEPLOY_MEMBERS` to `deploy_members_for_source` import, source-identity member lookup in validation, and manifest count from `self.member_names`. Preserve V1 retention schema/evidence dispatch until C.

All frozen hunks in these five tests are B-owned: `test_landing_renderer.py`, `test_landing_artifact.py`, `test_landing_api.py`, `test_landing_live.py`, `test_landing_sqlite_store.py`. The shared `sealed_target` fixture in renderer tests is a real prerequisite: it adds the analytics/static source members and patches retention's new `deploy_members_for_source` symbol for synthetic Git identities. The fixture and retention import must arrive together. Runtime/coordinator/legacy executor tests already reuse this fixture, so their source behavior updates without copying future HTTP tests.

No B architecture owner, schema inventory, module inventory or package dependency changes are needed. Keep the thirteen-module A inventory. The existing final artifact-test member-count assertion should be copied with the artifact update; do not retain its old literal count.

## C confirmed complete set

Whole source: `landing_contracts.py`, `landing_provider.py`, `landing_service.py`, and new `factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json`. Complete retention's remaining frozen hunks, including its versioned envelope (not only union annotations). In `landing_runtime.py` take only the evidence import, builder parameter annotation and `isinstance` union hunks; leave `create_landing_artifact_builder` and compose extraction for D.

Architecture changes are exactly: V2 contract object; DOGFOOD `public_contracts` V2 ID; DOGFOOD schema repository path. Do not copy future module owners, runtime paths, staged publication schema path, or unrelated trust-ci sorting from final `architecture/system.yaml`.

C frozen test changes comprise `factory/tests/test_landing_contracts.py`, `test_semantic_bridge.py`, `test_semantic_contracts.py`, plus the C root architecture hunks above. Both semantic test files enumerate every factory schema and assert the V2 version explicitly; both must accompany the new schema. The V1 schema is byte-identical between base and frozen source and must remain so.

C still needs the independently runnable synthetic V1/V2 retention/SQLite roundtrip adaptation described in the integration map. Existing `factory/tests/test_landing_runtime.py` already provides `_bound_output`, `BoundProvider`, the direct coordinated builder and real SQLite fixtures, without `landing_http` or the future builder helper. Retain this added test after D/G; account for its whole-file budget cost.

Static import inspection of the listed B/C whole source/test files found no imports of future host/HTTP/media/SSE/backup/publication modules. No additional frozen modified-test prerequisites were found within this bounded set. Preserve `factory/tests/__init__.py` until F and the old executor test until D, except B's inherited shared fixture. B/C add no Python modules, so A's classification inventory and rules remain unchanged.

Durable next-slice fact: `tests/test_architecture_model.py` is shared A/C work: optional-schema assertion in A; both V2 contract-inventory assertions in C. B fixture/retention-source hunks and C envelope/reader/schema-inventory hunks are indivisible within their respective slices.
