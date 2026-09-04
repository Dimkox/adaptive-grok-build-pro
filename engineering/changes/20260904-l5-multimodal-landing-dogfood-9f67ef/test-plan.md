# Test plan — L5 multimodal landing dogfood

## Execution rule

Each focused group runs once after its RED and repair. On failure, rerun only the failed method or affected group. After the product tree freezes, run one `python3 scripts/grok_verify.py --mode pr`, then all route-selected reviews; do not create a recurring exploratory loop.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Five media kinds, shape/type/limit validation, tenant and replay isolation | `test_landing_intake.py` |
| P0 | Fixed command identity, strict protocol, sealed fixture, unavailable default, no fallback/call | `test_landing_provider.py` |
| P0 | Prompt/tool/path/URL/authority injection rejected by closed spec | `test_landing_contracts.py`, `test_landing_provider.py` |
| P0 | Exact-SHA workspace, add-only writes, cleanup, independent evaluator, ordinals 1-3 only | `test_landing_coordinator.py`, `test_landing_renderer.py` |
| P0 | Deterministic manifest/ZIP/sidecar, traversal/symlink/mode/member rejection | `test_landing_artifact.py` |
| P0 | Default publisher denies before transport and cannot return live/indexed state | `test_landing_api.py`, `delivery/tests/test_landing_publisher.py` |
| P1 | 320/768/1280/1920 layout, keyboard, focus, reduced motion, static dependency policy | focused browser contract |
| P1 | Existing showcase, migrations, M0-M9 contracts, and product artifact unchanged | `tests/test_structure.py`, Git object/digest checks |

## Focused commands

```bash
python3 -m unittest factory.tests.test_landing_contracts factory.tests.test_landing_intake -v
python3 -m unittest factory.tests.test_landing_provider -v
python3 -m unittest factory.tests.test_landing_renderer factory.tests.test_landing_coordinator -v
python3 -m unittest factory.tests.test_landing_artifact -v
python3 -m unittest factory.tests.test_landing_api delivery.tests.test_landing_publisher -v
python3 -m unittest tests.test_structure -v
python3 scripts/grok_architecture.py validate --json
python3 scripts/grok_architecture.py drift --json
python3 scripts/grok_architecture.py diagram --check --json
```

Task-specific RED expectations are module/symbol absence or failed behavioral assertions, never a broad-suite failure. Browser commands must use the repository's existing local-only showcase harness with no external origin.

## Final evidence

The exact final source fingerprint must bind the typed spec and one PR-mode verifier receipt. Only after PASS are `code_reviewer`, `test_reviewer`, `security_reviewer`, and `release_reviewer` dispatched; every report and receipt binds the same unchanged fingerprint. This local evidence does not authorize push, merge, release, provider use, or deployment.
