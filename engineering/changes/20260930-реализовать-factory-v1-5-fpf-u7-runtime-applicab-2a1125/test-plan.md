# Test plan — Реализовать Factory v1.5 FPF U7 runtime: applicability selector, progressive dependency-complete reader, context budgeter, URI resolver, semantic projection, decision invalidation, adapter, offline snapshots, security boundary, A/B/C evaluation, upgrade fallback and deterministic tests

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | tenant/URI/security/semantic-loss/fallback negative controls | `test_fpf_runtime.py` |
| P1 | deterministic selection, projection, replay and A/B/C controls | `test_fpf_runtime.py` |

## Automated checks

- Unit: `PYTHONPATH=factory/src python3 -m unittest factory.tests.test_fpf_runtime -v`
- Integration: full Factory suite.
- Contract: change-spec validation and closed existing contracts.
- E2E: frozen snapshot through delivery and offline replay.
- Static analysis: route `base` and `contracts` profiles through `grok_verify`.

## Manual checks

- Independent code, test, security and release review on the frozen diff.
