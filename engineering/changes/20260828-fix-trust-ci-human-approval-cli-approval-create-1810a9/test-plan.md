# Test plan — Fix Trust CI human approval CLI: approval-create and approval-submit must run from a source checkout on a human-controlled host without importing API, worker, PostgreSQL, or other server-only dependencies; add regression tests and reproducible operator setup documentation without weakening signature verification or exposing private keys

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Human CLI parses without FastAPI/psycopg/uvicorn | isolated subprocess regression |
| P0 | Actual approval-create works while server imports are blocked | signed-envelope subprocess test using disposable test key |
| P0 | Existing API exact-SHA/replay/signature behavior is unchanged | focused signing/API tests |
| P1 | Every relocated non-human CLI branch imports only its command slice and reaches a safe terminal effect | parameterized fake-backed branch execution test |
| P1 | Full route profiles remain green | `grok_verify --mode pr` |

## Automated checks

- Unit: command-specific human import isolation plus exact import-slice and safe-effect
  coverage for every relocated non-human CLI branch.
- Integration: disposable-key approval creation; existing API approval/requeue tests.
- Contract: no OpenAPI or envelope schema diff; existing contract suite.
- E2E: no production approval; local source-checkout smoke command only.
- Static analysis: route-selected Ruff, Bandit, secret and source-stability checks.

## Manual checks

- On the host, run human-command help through `PYTHONPATH=trust-ci/src python3 -m
  adaptive_trust_ci.cli` without inspecting any private key.
