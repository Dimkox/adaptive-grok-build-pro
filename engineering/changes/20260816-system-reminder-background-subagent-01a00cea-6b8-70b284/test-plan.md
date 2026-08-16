# Test plan — 2.0.10

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Pins expect 2.0.10; in-zip VERSION is 2.0.10 | `python3 scripts/grok_verify.py --mode pr` |
| P0 | No GitHub Actions / no pyproject | same |
| P1 | README H1 and Current state name 2.0.10 | structure test + README |

## Automated checks

- Unit: `tests/test_structure.py`, `tests/test_manifest_package.py`
- Static: ruff/bandit/coverage as selected by `grok_verify --mode pr`

## Manual checks

- `git describe --tags --exact-match` after tag
- `gh release view v2.0.10`
- `git rev-parse v2.0.9` still `f72c0fc…`
