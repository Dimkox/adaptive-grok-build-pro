# Issue 155 root-suite diagnosis — 2026-09-21

Route: `c4e47ea3ced7`; application write owner: `frontend_implementer`.

## Result

No application, test, configuration, migration, or reviewed-checkout file was changed by this subtask. The exact root `python-unittest` command currently passes all 785 tests. Coverage passes at 80% against the unchanged 74% threshold. No product fix is warranted by this reproduction.

## Exact command and run

Working directory: `/home/pall/grok-projects/adaptive-grok-build-repair`.
`selected_workers(root)` returned `None`; `GROK_TEST_WORKERS` was unset and `.grok-test-runner.json` was absent. This selects the legacy branch at `.grok-stack/adaptive_grok/verification.py:966`, with a fresh external `COVERAGE_FILE`.

```text
COVERAGE_FILE=/home/pall/.cache/agbp-run/p155-root-unittest-lqk7chp4/.coverage coverage run --rcfile=.coveragerc -m unittest discover -s tests
COVERAGE_FILE=/home/pall/.cache/agbp-run/p155-root-unittest-lqk7chp4/.coverage coverage report --rcfile=.coveragerc
```

- First command: exit 0, 604.509 s wall time; unittest reports `Ran 785 tests in 603.604s` and `OK`.
- Second command: exit 0, 1.719 s; `TOTAL 80%`.
- Started `2026-09-21T04:37:13.312279+00:00`; completed `2026-09-21T04:47:19.542411+00:00`.
- Start HEAD `6b13806d454cada0c63520129baf09056db46408`; end HEAD `4a47c76b3fb37fbac430fd209771a695832610d2`. The controller committed only eight handoff/change-package documentation files during this run, confirmed by `git diff --name-only` between those commits. Product/test/config bytes did not change. This diagnostic run is not a whole-tree fingerprint-bound verification receipt; the controller owns the required final verifier.
- Full output, data, and metadata: `unittest.log`, `coverage.log`, `.coverage`, `results.json` in this directory.

## Confirmed causal control; historical attribution remains inferred

The old `/home/pall/.cache/agbp-run/p155_verify.log` reports architecture failures for seven unowned source helpers under `.qwen/tmp`, and `python-unittest: exit=1`, but has no traceback. Its exact failed root test therefore cannot be recovered conclusively.

The existing `tests.test_architecture_model.ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts` asserts `validate_repository_drift(ROOT, snapshot) == ()` at `tests/test_architecture_model.py:1319`. Architecture validation reports undeclared sources at `.grok-stack/adaptive_grok/architecture.py:1048`.

An isolated external local clone at `/home/pall/.cache/agbp-run/p155-arch-control-ybbd7v9n/checkout` of `4a47c76b3fb37fbac430fd209771a695832610d2` proved the causal mechanism with the same single focused command:

```text
/usr/bin/python3 -m unittest tests.test_architecture_model.ArchitectureModelTests.test_seed_architecture_models_current_boundaries_and_real_contracts
```

1. Clean clone: exit 0; one test passed in 0.260 s.
2. Added exactly `.qwen/tmp/probe.py` inside that external clone: exit 1; one failure in 0.201 s at the assertion above, with `ArchitectureFinding(code='undeclared_source', path='.qwen/tmp/probe.py')`.
3. Removed only that synthetic file: exit 0; one test passed in 0.252 s. Clone `git status --short` is empty.

The complete baseline/red/green logs and results JSON are in `/home/pall/.cache/agbp-run/p155-arch-control-ybbd7v9n`. The real checkout never contained this probe and was clean at the end. This supports scratch-source contamination as the inferred historical root-suite cause. It does not assert that no additional historical failure occurred, because the original traceback is unavailable.

## Preserved boundary and handoff

Migration `factory/src/adaptive_factory/resources/018_semantic_validation_bridge.sql` is byte-identical to route base `90078959ff816068af374ad42f4bb80fdbaec866`; SHA256 `33053563dce7c34edfa9301130272adb34651d44dd1f2bc305ba3eec01382c70`.

No full `grok_verify`, disposable database tier, receipt/grant/route mutation, commit, push, PR, external service write, or deployed CI change was performed by this subtask. The controller continues final whole-tree verification, content-bound PostgreSQL evidence, and independent route reviews.

Fact for durable shared memory (controller owns docs): source-like diagnostic helpers inside an inventory-scanned checkout can fail both architecture verification and a root architecture seed test even when ignored by Git; keep helper files, test output, and intentional negative controls in external temporary directories. The cause is helper placement inside the scanned source boundary, not application behavior.
