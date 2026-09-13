# L5 delivery slice C implementation

Route: 00652f60f78c. Worktree: /home/pall/grok-projects/adaptive-grok-build-pro-l5-split-c.
Branch: feat/l5-split-c-evidence-v2.
Genuine source predecessor at route creation: c46f14f6a39ca8dc778f8a179ab4f61cdfe13599.
Current pre-commit HEAD after ancestor documentation corrections: 63351be5ed814353cd1e8da4089edef2ca9a013f.
Immutable reconstruction source: f31406e970d67f7cd59694da5de88915adb0fa68.
All 13 C product/test/config hashes stayed unchanged through the parent's paperwork merges.

## Implemented selection

The frozen contracts/provider/service modules and remaining retention version hunks add independent V2 evidence readers and matching retained-envelope version2. V1 retains its original dispositions, digest domain, exact published schema bytes and version1 retained envelope. Invalid boolean/unknown versions, crossed nested/envelope versions and changed evidence facts without a matching digest reject. No HTTP producer, new composition helper, migration or external capability is introduced.

landing_runtime.py contains only the three LandingProviderEvidence union substitutions (import, direct builder argument, input acceptance); its existing compose_landing_live body is otherwise byte-identical to B. Architecture system changes are exactly the V2 contract declaration plus existing DOGFOOD public-contract ID and schema path. No future module ownership or rules were copied. Existing semantic and root architecture catalogs now require the explicit additive V2 identity/version while retaining closed and exact inventories.

Ten whole-file selections match frozen content exactly, including the now-complete retention module and both root architecture test files whose remaining differences were the approved deferred catalog hunks. The runtime union and architecture model were independently reconstructed from the real predecessor with only the approved changes and byte/semantic compared. V1 schema, landing OpenAPI, uv.lock and architecture/rules.yaml are unchanged.

## Independent reader proof retained beyond C

factory/tests/test_landing_runtime.py adds one bounded reader-only regression, test_mixed_evidence_readers_persist_restart_and_reject_tampering_without_http. It reuses BoundProvider/_bound_output, the direct coordinated artifact builder, sealed source fixture and actual temporary SQLite store. A local subclass converts synthetic V1 facts to V2 facts; it never imports future HTTP modules or create_landing_artifact_builder.

Both versions reach artifact_ready, share one SQLite store and survive close/reopen with revalidated files. Raw sealed_artifact_json bytes remain identical across restart, including the legacy V1 envelope. Both providers are invoked exactly once. The test rejects seven envelope/version/disposition/digest mutations and then corrupts a persisted V2 usage fact, verifies the reopened store rejects it with store_record, and verifies the V1 job remains readable. All preexisting runtime test bodies are unchanged.

This test and its local imports are an explicitly authorized strengthening difference from frozen f31406e. Preserve it in later slices and final manifest accounting; do not replace the runtime test file wholesale with the monolith's version.

## Verification evidence

- Focused predecessor baseline: 30 contracts/runtime/semantic-catalog tests passed in1.526s (split-c-baseline.out).
- Fixture-first RED: three failures and one error across missing V2 type/schema catalogs and the independent reader flow (split-c-readers-red.out). The V1 job successfully built before the unavailable V2 path reached needs_human.
- Final focused readers/catalogs: 33 tests passed in2.120s (split-c-readers-green-final.out). An earlier attempt exposed a new-test fixture mistake, Actor.tenant_id instead of the existing service's actor.actor_id key; only that test expression was corrected. The original failed output remains split-c-readers-green.out.
- Root architecture catalogs plus mandatory current-module inventory: seven tests passed in1.265s (split-c-core-catalog-green.out). Diagram --check passes with no generated changes (split-c-diagrams.json).
- Expanded 28-worker Factory run: 73 passed, one test's text subcase hit its unchanged two-second sealed-provider timeout and caused its derivative list assertion (split-c-focused-green-final.out). The exact failed method then passed serial in0.341s on unchanged source (split-c-provider-targeted-recovery.out). This is preserved targeted recovery, not a relabeled whole-suite pass. An initial command named nonexistent test_landing_service.py and collected zero tests; split-c-focused-green.out is retained as that non-evidence run. The corrected run used the real test_landing_api.py.
- Actual fitness after documentation merges: PASS against genuine route base c46f14f6a39ca8dc778f8a179ab4f61cdfe13599, including code budgets, contract compatibility, boundaries and separation. No rule/budget changes. Final JSON: split-c-fitness-final.json; earlier same-source fitness remains split-c-fitness.json.
- All changed Python sources/tests pass Ruff (split-c-ruff.out); diff --check passes. Exact thirteen-path audit and final HEAD/hash manifest: split-c-source-sha256.json. No new coverage percentage measured.

All evidence paths above are under /tmp/agbp-sweep/. Parent owns current full verification, independent reviews and receipts in the separate evidence worktree. Earlier A/B or monolith reports do not substitute C verification.

## Commands

From C with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=.:factory/src:delivery/src:.grok-stack:

```sh
/tmp/agbp-venv/bin/python -m unittest factory.tests.test_landing_contracts factory.tests.test_semantic_bridge factory.tests.test_semantic_contracts factory.tests.test_landing_runtime
taskset -c 0-27 /tmp/agbp-venv/bin/python -m pytest -n 28 --dist loadfile factory/tests/test_landing_contracts.py factory/tests/test_landing_provider.py factory/tests/test_landing_api.py factory/tests/test_landing_runtime.py factory/tests/test_landing_sqlite_store.py factory/tests/test_semantic_bridge.py factory/tests/test_semantic_contracts.py factory/tests/test_landing_live_executors.py
/tmp/agbp-venv/bin/python -m unittest factory.tests.test_landing_provider.LandingProviderTests.test_explicit_sealed_fixture_normalizes_all_five_kinds_to_same_semantics
/tmp/agbp-venv/bin/python scripts/grok_architecture.py fitness --base c46f14f6a39ca8dc778f8a179ab4f61cdfe13599 --worktree --pre-risk yellow --json
```

## Handoff and rollback

Product source is frozen. No production producer emits V2 in C; D must introduce its producer only after these readers exist. Rollback to a V1-only reader cannot consume V2 retained envelopes; stop any later V2 producer and preserve original durable evidence rather than relabeling versions. No existing stored rows are migrated by opening the store.

No credentials, approval stores or private keys were read, no live HTTP/network/operational writes occurred, and this child performed no Git mutation or full-verifier run. Root-owned exact factory/README.md changes are documentation and excluded only from the implementation path manifest; they remain reviewable paperwork.

## Exact source/config/test hashes

- `architecture/system.yaml` (three_v2_registration_entries): `86b45dc1cacf56dae1dd4b72d972296dec3e14c9b50640c1e3338490c7ae696f`; Git blob `b0b78afcaba427050113fc495d07db2bc23a6d8e`.
- `factory/contracts/jsonschema/landing-provider-evidence.v2.schema.json` (whole_frozen): `888ddf6ee0042cb332ae17904d1c0f7269894e863ee37ba3b7a950e463bc9eeb`; Git blob `ee40c1860df65aad00effcb12ed06aab169a415a`.
- `factory/src/adaptive_factory/landing_artifact_retention.py` (whole_frozen): `c2016e054010a2f26d34b25b97615eb4d13964986a8deade58a0c42efbc484f0`; Git blob `b4d85b9accd00054076cd5a1027cede37075606d`.
- `factory/src/adaptive_factory/landing_contracts.py` (whole_frozen): `e69b8f754570a62bc168e0c73069b398e6166699127386c8ba69e4c8753cc6d8`; Git blob `2409a1ef92d90e03d00740a9ca79b33695d64739`.
- `factory/src/adaptive_factory/landing_provider.py` (whole_frozen): `031fd7cd31be8bbf7a1b98e022a6592818a64d5f05da0da80c182c6b17339cb6`; Git blob `61b3b6f1ea1e6574a536a1cae605b8d045edfd72`.
- `factory/src/adaptive_factory/landing_runtime.py` (union_only): `d1805ac32f7e15ef35ddabdaa8d87f2d234b95fd39feb89093e52e8236395461`; Git blob `ba5764f78531de0fdd6c257213a68b2eaf410158`.
- `factory/src/adaptive_factory/landing_service.py` (whole_frozen): `b6d6ca442aed9f01f541cfd2c44e9632c30b05e34df4bf066bd7819b3d688b3b`; Git blob `face482d20776fa44d7faeaed2940ed994edaf33`.
- `factory/tests/test_landing_contracts.py` (whole_frozen): `98927025419de33ba3fa7d2c2acac59b16982c4d72cea45f08f85d9466abd302`; Git blob `7d5009f84a2de41079b591f285875fc26a201c7f`.
- `factory/tests/test_landing_runtime.py` (independent_reader_test_strengthening): `246dca28b92a1f8b313f3620e09c3d30f66f8b6e92724eb0c265f3ddf4867643`; Git blob `96615590b494283057d7b53ea0ed1596dd3e46bf`.
- `factory/tests/test_semantic_bridge.py` (whole_frozen): `0389767fe99830b448bad57b5f59e786d4814b063fe0db367cf9d3305b8f7d98`; Git blob `a76a02298b25ceaf0f924c81082ab0a792e470b9`.
- `factory/tests/test_semantic_contracts.py` (whole_frozen): `5d38739bfaa1c9709fa11ddd6c85b2ca80967e48a57576b1e5ca589a90a1f1ea`; Git blob `563777238363c49ee2f87ead089cbd602d9264ee`.
- `tests/test_architecture_fitness.py` (whole_frozen): `be87cf5b1ac76ff115f5ecbac7df5337b03ec5e1f87b6957341fccf299480146`; Git blob `7649ba9c5d55654f7cc05583ea8833eb1d7191cd`.
- `tests/test_architecture_model.py` (whole_frozen): `aba093773e2974fdc84ca1ed604d38ac545689e793b16d7daaec1d754b3552ea`; Git blob `5bd53c70caf33070a9b1a171088015a94930df3b`.
