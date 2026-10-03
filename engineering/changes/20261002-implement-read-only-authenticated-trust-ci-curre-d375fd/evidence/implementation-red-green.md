# G implementation evidence

Route `d375fd5f77d1`; sole write owner `integration_implementer`; source base `e5856acfd4bc7a186f40a740b54ec86459462db5`. The controller completed startup scope selection before implementation. Its docs-only draft-spec failure is historical startup evidence, not current product verification. Current runtime/API/store/OpenAPI changes require full PR verification.

## RED controls

`PYTHONPATH=trust-ci/tests taskset -c 0-27 python3 -m unittest test_api.ApiTests.test_authority_auth_is_enforced_before_source_or_job_lookup test_store.StoreTests.test_bounded_approval_inventory_is_available test_authority.AuthorityTests.test_snapshot_conforms_to_versioned_closed_openapi_schema -v` returned exit 1 with three expected failures: missing route returned 404 instead of 401, bounded store method was absent, and authority contract route was absent. Earlier complete authority RED discovery also produced missing-module setup errors; those errors are not claimed as behavioral RED evidence.

Additional implemented negative controls exposed stable-public-file access-time rejection, unknown signed attestation fields, signed-inventory normalization (duplicates, negative duration, malformed command digest), and signed-byte mutation not detected by dataclass equality. Their targeted commands returned expected failures before their corresponding repair. The service now compares stable inode/content metadata excluding access time, validates the signed canonical inventory without normalization loss, verifies the signature through existing `verify_attestation`, and compares the exact envelope digest on closing acquisition.

## Focused GREEN observations

`PYTHONPATH=trust-ci/tests taskset -c 14,15 python3 -m unittest test_authority test_store test_api -q` passed 61 tests before the final malformed-inventory test addition. This is a dated intermediate result; final full Trust CI discovery supersedes it below.

`TRUST_CI_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:32993/authority_test PYTHONPATH=trust-ci/tests taskset -c 14,15 python3 -m unittest test_postgres_integration -v` passed 13 tests in 5.379 seconds. Disposable image `postgres:17.6-bookworm`, local image ID `f3bd19c606e4`, container `v211-g-authority-postgres-20261002`, ID `0b2d6b8eda3b8287fb9a923bf4fe3435ef2730b6e884191600d186ab14c80e93`, loopback-only ephemeral port 32993, no mounted host/runtime data, at most two CPUs (14,15), 512 MiB. An initial migration attempt failed because fixture roles were absent; creating the four synthetic disposable roles allowed the complete migration and tests. No production database was contacted.

New PostgreSQL assertions cover exact repository/PR/base/head/policy/time predicates, memory/PostgreSQL ordering and limit+1 overflow, a genuinely blocked table query cancelled by the four-second statement timeout, and authenticated current-authority readback of durable signed rows. Existing durable-row/lease/replay tests also ran.

`TRUST_CI_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:32993/authority_test taskset -c 14,15 python3 -m unittest discover -s trust-ci/tests -q` passed 277 tests in 17.015 seconds without skips before replacement of the undeclared `jsonschema` test dependency with the checked-in dependency-free subset validator. Final handoff records the fresh rerun after all edits and main synchronization.

`taskset -c 14,15 python3 -m unittest tests.test_structure -q` passed 21 tests. `git diff --check` returned exit 0.

Fresh final implementation rerun after all production edits and dependency cleanup: `TRUST_CI_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:32993/authority_test taskset -c 14,15 python3 -m unittest discover -s trust-ci/tests -q` passed all 277 tests in 12.605 seconds, no skips. `python3 -m py_compile trust-ci/src/adaptive_trust_ci/authority.py trust-ci/src/adaptive_trust_ci/api.py trust-ci/src/adaptive_trust_ci/store.py` returned exit 0.

## Limits and handoff

The controller owns full repository PR verification, all four selected independent reviews, final fingerprint receipts and exact-head external Trust CI. Focused checks are implementation evidence only. No live CI endpoint/deployment, signed human approval/private key, branch-protection change, existing production state or operational rollout was exercised. Synthetic private keys stayed in test memory; only public fixtures were written to disposable scratch. Policy/holdout and trust rechecks cannot create a transaction across independent mounted sources; the endpoint rejects observed changes during acquisition and expires within its bounded observation window. The current policy schema has no timestamp cutoff, so none is invented.

The immutable historical source supplied only the narrow endpoint/service/query pattern. No historical workflow receipt, aggregate policy/CLI/settings/worker/example/README change or private/deployed source was imported. Frozen brief/spec/architecture/requirements/test-plan files were not edited by the writer.
