# Test plan — Implement durable Factory v1.5 result admission persistence

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Exact replay/conflict, authority/fence, rollback, tenant read, zero outbox | `test_postgres_integration.py` |
| P0 | Result and replay survive actual PostgreSQL restart | `postgres_restart_probe.py` |
| P1 | API parsing/auth/status and OpenAPI binding | `test_result_admission_api.py`, `test_openapi_contract.py` |

## Automated checks

- Unit: result admission API, broker and migration modules.
- Integration: disposable PostgreSQL 17 suite with runtime role.
- Contract: OpenAPI and JSON schema binding.
- E2E: mandatory disposable exit runner including actual container restart.
- Static analysis: repository verifier compile/lint checks.

## Manual checks

- Confirm release notes do not claim dispatch, channel qualification, U3 completion or U4/macOS.
