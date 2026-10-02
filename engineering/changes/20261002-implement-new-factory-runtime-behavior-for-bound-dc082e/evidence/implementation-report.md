# PR3a offline result foundation

Write owner: route-selected general_implementer, route dc082e48d0da. Candidate started at exact PR232 head 12a7fd63146c96cff655f1d9cf21184c465037ca. Adapted aa53f300d506736e61b36f627f8f12172ce8fbce without cherry-picking or replacing shared snapshots.

## Change

Six additive files: factory/src/adaptive_factory/result_broker.py, result_contracts.py; factory/contracts/jsonschema/result-envelope.v1.schema.json, result-channel-qualification.v1.schema.json; factory/tests/test_result_broker.py; tests/test_factory_v15_result_schema.py.

Limits accept only exact positive integers: bytes <=1,000,000; records <=100,000; depth <=64; chunks <=100,000. Defaults are 1,000,000/1,000/32/1,000. Policy metadata is safe, bounded UTF-8 text. Collection checks remaining byte capacity before extending the buffer, counts empty chunks, and returns payload-free stable rejections without truncation or exception diagnostics.

JSON parsing rejects duplicate keys including escaped-equivalent and nested keys. Sensitive structured keys replace their complete value and key with the redaction marker; collisions reject. Direct envelope admission independently checks strict JSON, structured secret keys, nonfinite values, typed/Unicode metadata, digests, completeness and unknown-channel payload parity. Qualification remains unavailable-only with null interception points and a complete unique seven-channel set.

Architecture registers the sidecars/modules under the existing proposal-broker boundary; no limit is relaxed. Existing schema inventory tests admit the sidecars, and additive exclusions retain the predecessor count 23 and digest 98818e23ea78821c1c602774072c77bf7d891ef69fe2ba03f0ecbad9220134fc. PR2c source/contracts remain unchanged.

## RED evidence

Before adding production modules, loaded retained aa53f300d result modules into an in-memory adaptive_factory package and ran the new result tests with PYTHONPATH=factory/src. Eleven tests produced 32 failed subcases and 12 errors: Authorization/nested secret leakage, duplicate-key acceptance, invalid limits/metadata accepted, unknown payload parity accepted, unhashable enum TypeError, missing max_chunks interface, and oversized pre-copy probe returning stream failure. This uses real retained source and has no candidate production writes.

Additional RED before local repairs: typed-envelope surrogate metadata produced three UnicodeEncodeError errors and a surrogate JSON key was admitted (one failed subcase); nested credentials object was admitted (one failed subcase). Both are now covered by passing regressions.

Reproduction against the final regression inventory still fails on retained source: 13 tests, 33 failed subcases, 18 errors, exit 1. This isolated in-memory source load does not alter candidate files:

```bash
PYTHONPATH=factory/src python3 - <<'PY'
import io, subprocess, sys, types, unittest
for name in ('result_contracts', 'result_broker'):
    mod = types.ModuleType('adaptive_factory.' + name)
    mod.__package__ = 'adaptive_factory'
    sys.modules[mod.__name__] = mod
    source = subprocess.check_output(['git', 'show', 'aa53f300d:factory/src/adaptive_factory/' + name + '.py'], text=True)
    exec(compile(source, 'aa53f300d/' + name + '.py', 'exec'), mod.__dict__)
suite = unittest.defaultTestLoader.discover('factory/tests', pattern='test_result_broker.py')
result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
print('Retained source RED:', result.testsRun, 'tests;', len(result.failures), 'failed subcases;', len(result.errors), 'errors')
sys.exit(not result.wasSuccessful())
PY
```

## Verification

Focused GREEN commands/results are recorded after the final run below. Initial individual unittest discovery for semantic_bridge failed because its relative test imports require package-qualified loading; the corrected package-qualified combined invocation passes. An attempted decision schema filename was absent; the discovered actual module is tests/test_factory_v15_decisions.py and the final run uses that path.

Initial implementation focused GREEN recorded for 3442713ef06b586b098d17ad10d377b7fa546193:

- PYTHONPATH=factory/src python3 -m unittest factory.tests.test_result_broker factory.tests.test_semantic_contracts factory.tests.test_semantic_bridge factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_package_are_frozen — 33 tests passed (13 result tests), 0.489 s.
- python3 -m pytest tests/test_factory_v15_result_schema.py tests/test_factory_v15_decisions.py tests/test_architecture_model.py -q — 96 tests and 336 subtests passed, 2.35 s.
- python3 scripts/grok_spec.py validate engineering/changes/20261002-implement-new-factory-runtime-behavior-for-bound-dc082e/change-spec.yaml --gate — ok, zero errors; all 11 criteria mapped, exact schema/test inventory declared.
- python3 scripts/grok_architecture.py validate — ok, no findings.
- python3 scripts/grok_architecture.py fitness --base 12a7fd63146c96cff655f1d9cf21184c465037ca --worktree --json — pass, no findings.
- ruff check factory/src/adaptive_factory/result_broker.py factory/src/adaptive_factory/result_contracts.py factory/tests/test_result_broker.py tests/test_factory_v15_result_schema.py — all checks passed.
- git diff --check — passed.

These are focused implementation evidence, not final full-verifier receipts or independent review evidence.

Fitness against exact agreed stacked base 12a7fd63146c96cff655f1d9cf21184c465037ca passes with no findings. The older active-route base 01b089fcbf417d69f8a21407ea41941436ce74d4 additionally includes predecessor PR2 changes and reported failure; coordinator confirmed the exact agreed comparison base is PR232 head. No history rewrite or architecture-budget relaxation.

## Residual scope

inspect() never consumes result chunks and leaves every real channel unavailable. This is deterministic offline policy evaluation only, with known-pattern secret detection rather than proof of arbitrary secret identification. A synchronous iterator can block inside next(); timeout and authenticated runtime interception belong to the later adapter slice. No persistence, migration, endpoint, dispatch, live U3/U6, BB-R08 or full F25 acceptance is provided. Full routed verification, read-only independent mutation reviews, exact-tree receipts and external Trust CI remain coordinator delivery gates. Rollback is reviewed revert/forward fix of additive sidecars/bindings with unavailable runtime behavior preserved.

## Independent code-review correction: declared unknown sentinel

Code review of 3442713ef06b586b098d17ad10d377b7fa546193 found that inspect() rejected the declared unknown sentinel even though the qualification matrix includes it as unavailable. The source test explicitly excluded that seventh channel, allowing the inconsistent behavior to survive. Changed the test to iterate all RESULT_CHANNELS and added a separate non-consumption regression for unknown-channel sanitization and unrecognized-channel inspection.

RED: PYTHONPATH=factory/src python3 -m unittest factory.tests.test_result_broker.ResultBrokerTests.test_runtime_channels_are_unavailable_and_stream_is_not_consumed factory.tests.test_result_broker.ResultBrokerTests.test_unknown_sanitization_and_unrecognized_inspection_reject_without_consuming — 2 tests, 1 failure: rejected/invalid_channel instead of unavailable/runtime_wiring_missing for the declared unknown channel.

Repair: inspect() alone opts into allowing the declared sentinel in the shared metadata validator. The validator first distinguishes actual membership in RESULT_CHANNELS from fallback unknown metadata. Unrecognized metadata still rejects; sanitize_candidate() retains its default rejection of unknown, and direct ResultEnvelopeV1 admission still forbids unknown-channel sanitized payloads.

Focused GREEN after correction:

- PYTHONPATH=factory/src python3 -m unittest factory.tests.test_result_broker factory.tests.test_semantic_contracts factory.tests.test_semantic_bridge factory.tests.test_landing_api.LandingApiTests.test_predecessor_contract_migration_showcase_and_published_package_are_frozen — 34 tests passed (14 result tests), 0.464 s.
- python3 -m pytest tests/test_factory_v15_result_schema.py tests/test_factory_v15_decisions.py tests/test_architecture_model.py -q — 96 tests and 336 subtests passed, 2.31 s.
- python3 scripts/grok_architecture.py validate — ok, no findings.
- python3 scripts/grok_architecture.py fitness --base 12a7fd63146c96cff655f1d9cf21184c465037ca --worktree --json — pass, no findings, unchanged limits.
- ruff check factory/src/adaptive_factory/result_broker.py factory/src/adaptive_factory/result_contracts.py factory/tests/test_result_broker.py tests/test_factory_v15_result_schema.py — all checks passed.
- git diff --check — passed.

Prior full-verifier/review results remain bound to their original identities. The coordinator must verify/review the corrected candidate afresh.
