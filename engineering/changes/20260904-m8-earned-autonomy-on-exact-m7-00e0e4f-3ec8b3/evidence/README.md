# Evidence

Store human-readable review reports here. Machine receipts live under `.grok-stack/runtime/receipts/` and are bound to the current repository fingerprint.

Canonical final M8 `2cee9b9` (true comparison base `9fe779a`) is semantic source material only. This change remains a descendant of exact M7 `00e0e4f9a6f50844bf9e0ffc7139d3283dda889f`; the canonical duplicate M7 wire is explicitly excluded and replaced by an integrated bridge over the actual M7 source.

This phase permits repository-local source and synthetic pure tests only. Real cohort/currentness/acceptance evidence, activation, PostgreSQL, providers, network, full verification, reviews, receipts, packaging, delivery, and all external or production actions are deferred.

## Focused source evidence

- Expected RED: `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_autonomy factory.tests.test_autonomy_schema` failed with two import errors because `adaptive_factory.autonomy` did not yet exist.
- Integrated run: the same two modules executed 31 methods; 30 passed and one test-harness method failed because canonical M7 rejected an invalid dataclass replacement before the bridge was invoked.
- Exact repair evidence: `factory.tests.test_autonomy.M7BridgeContractTests.test_direct_wrapper_construction_cannot_bypass_wire_recomputation` passed after the fixture explicitly simulated constructor bypass; no successful group was rerun.
- Python compilation, both JSON parses, and `git diff --check` passed before the source commit.
- `python3 scripts/grok_architecture.py validate` returned `ok: true` with zero findings; architecture files therefore remained unchanged.
