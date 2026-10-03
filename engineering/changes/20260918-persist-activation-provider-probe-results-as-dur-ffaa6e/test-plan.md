# Test plan — durable activation probe observations

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Reserve and commit unique pending probe before provider dispatch; reservation failure means zero provider calls | Store/service unit test |
| P0 | Same idempotency key under sequential and concurrent POSTs causes at most one provider call | API concurrency regression test |
| P0 | Operator kind + dedicated scope required; non-operator, wrong scope, and general factory app cannot access route | API authorization tests |
| P0 | Known success/failure stores only bounded safe fields; credential/body/raw prompt never appears | Sanitization tests |
| P0 | Restart with terminal row; GET returns exact row and zero provider calls | SQLite/API restart test |
| P0 | Crash after request-start remains ambiguous and a same-key POST through the reopened service returns unknown without calling the runner | API restart/idempotency regression test |
| P0 | v1/v2→v3 migrations preserve prior rows; backup/restore round-trip preserves probe row | Migration and backup integration tests |
| P0 | Historical 769/191 evidence is not assigned a new probe ID or rewritten as a row | Dossier boundary check |
| P1 | OpenAPI schema parity and operator route registration remain closed and landing-only | Contract parity/structure tests |

## Automated checks

- Unit: probe record lifecycle, immutable finalization, idempotency, bounded fields, error taxonomy.
- Integration: real SQLite v1/v2 migration, landing Unix socket POST/GET, process restart, provider transport mock with request-count assertion.
- Contract: schema and route parity; closed request, response, and error objects.
- Backup: snapshot and restore retain exact row identity and digest.
- Static: `git diff --check`, Ruff, bandit, full `python3 scripts/grok_verify.py --mode pr`.

## Manual checks

- Inspect a restored probe row and verify no provider invocation occurs during GET or restore.
- Confirm operator runtime docs distinguish activation probe from the end-to-end pilot and classify the historical 769/191 result as attested only.
