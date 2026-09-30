# Test plan — Добавить в Factory новый observation-only адаптер ротации бесплатных Qwen/OpenRouter моделей: versioned provider registry, bounded failover/cooldown, token quota observation, deterministic selection, retry and fallback evidence, tenant/fence/budget binding, no credential persistence, no authority bypass, tests; источник prototype qwen-model-rotator commit b76a09849c132ab62f73bee76f949bd600bc4649

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | response-start, fatal auth/payment/daily limit and binding fail closed | `factory/tests/test_model_rotator.py` |
| P0 | attempt and token budgets cannot be exceeded | `factory/tests/test_model_rotator.py` |
| P1 | deterministic cooldown selection and complete evidence | `factory/tests/test_model_rotator.py` |

## Automated checks

- Unit: `python -m unittest factory/tests/test_model_rotator.py`
- Integration:
- Contract:
- E2E:
- Static analysis:

## Manual checks
