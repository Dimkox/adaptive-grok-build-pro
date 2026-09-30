# F24/F26 TDD and focused verification

This is implementation evidence, not a verification receipt, live profile qualification, human acceptance, merge authority, or production authority.

## RED

Command:

```text
PYTHONPATH=factory/src python3 -m unittest factory.tests.test_behavior_qualification
```

Observed before production code existed: `Ran 6 tests`; all six failed at the explicit `F24/F26 qualification harness missing` assertion. The failure was caused by the missing `adaptive_factory.behavior_qualification` module, not a test import typo.

A second RED cycle added the finite input-token budget and actual-provider identity check. The unchanged implementation rejected the new closed config field, so the new tests could not pass until the production contract and accounting were extended.

## GREEN

Commands and observations:

```text
PYTHONPATH=factory/src python3 -m unittest factory.tests.test_behavior_qualification
Ran 6 tests in 0.133s — OK

PYTHONPATH=factory/src python3 -m unittest factory.tests.test_behavior_qualification factory.tests.test_qualification factory.tests.test_decision_contracts factory.tests.test_context_contracts factory.tests.test_prediction_contracts factory.tests.test_result_contracts
Ran 24 tests in 0.290s — OK

PYTHONPATH=factory/src python3 -m compileall -q factory/src/adaptive_factory factory/tests/test_behavior_qualification.py
exit 0
```

The package was also built without dependencies or isolation into a private temporary directory. Inspection of the wheel confirmed these exact entries:

- `adaptive_factory/behavior_qualification.py`
- `adaptive_factory/resources/pump-selector-qualification-v1.json`
- `adaptive_factory/resources/pump-selector-baseline-v1.json`

## Wider discovery observation

`PYTHONPATH=factory/src python3 -m unittest discover -s factory/tests` is not the repository's package-aware factory command. It ran 782 tests with 160 skips, seven relative-import collection errors, and one pre-existing frozen landing migration/showcase identity mismatch (`expected 33`, observed current v1.5 migration count `23`). None referenced the new harness paths. This result is retained as a non-passing observation; it is not reported as verification. The authoritative integration gate remains `python3 scripts/grok_verify.py --mode pr` on the final integrated tree.
