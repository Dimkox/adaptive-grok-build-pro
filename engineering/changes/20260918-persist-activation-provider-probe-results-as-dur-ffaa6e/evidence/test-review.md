# #121 Test review — PASS

Re-reviewed the current #121 diff in `/tmp/adaptive-fix-activation-probe` against the approved design. Focused command:

```text
PYTHONPATH=factory/src python3 -m unittest factory.tests.test_landing_activation_probe -v
Ran 8 tests in 0.639s — OK
```

## Findings

No remaining test-review findings.

The earlier medium finding is resolved in `factory/tests/test_landing_activation_probe.py::test_pending_after_restart_becomes_unknown_and_same_key_never_dispatches` (lines 181–222). The test now calls `LandingActivationProbeService.create` with a runner that simulates process death after dispatch, verifies revision 1 remains pending, reopens the store and verifies recovery to `unknown`, then retries the original idempotency key through POST. The retry returns the same probe ID and `unknown` state, and the reopened runner remains uncalled.

## Coverage confirmed

- POST observes a durable pending reservation, `provider_attempts == 1`, and request-start marker inside the runner before the mock provider returns. It asserts one call, same-key replay without another call, changed-profile conflict, two append-only revisions, and UPDATE/DELETE trigger rejection.
- Eight simultaneous same-key POST requests cause one provider call and share a probe ID.
- Operator actor and dedicated scope are enforced; client actors, wrong scope, forged client results, invalid profiles, and non-landing-only app access are rejected.
- Provider exception text and secret markers are absent from returned and persisted records.
- v1/v2 databases migrate to schema v3; backup preserves a pending probe row and restore conservatively recovers it to `unknown`.
- New probe read survives reopening; the historical 769/191 activation ID is not backfilled and returns 404. The runbook records it as historical attestation only.
- Endpoint operations match the closed OpenAPI contract, including landing-only, operator-kind, scope and bearer-security metadata.

The probe endpoint tests use FastAPI `TestClient` rather than a real Unix-socket transport. Production composition in `factory/src/adaptive_factory/landing_host.py` sets `landing_only=True`, and the dedicated host serves via its configured Unix socket; no contradictory exposure was found. A socket-level probe-specific test would add confidence but is not blocking for this review.
