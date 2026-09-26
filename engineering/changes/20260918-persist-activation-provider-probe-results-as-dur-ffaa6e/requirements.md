# Requirements — durable activation probe observations

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Historical 769/191 remains attested only; no historical provider replay or backfill is in scope.

## Acceptance criteria

- [x] A POST to the landing-only Unix socket accepts only configured profiles, requires operator actor kind plus `landing:probe`, persists the unique ID and pending/request-start state before the provider call, and then executes exactly one server-side synthetic request.
- [x] Repeating the same idempotency key returns the same current/final record and does not dispatch another provider request.
- [x] Durable rows keep profile/model identity and digest, synthetic input digest, normalized state, spec/response digests on success, usage, locally initiated provider attempt count, timing, timestamps, and only allowlisted failure category/status. No secrets, raw prompt/provider bodies, or unbounded exception text.
- [x] Lookup is read-only and works after restart. A pending record whose dispatch outcome is uncertain is not retried automatically.
- [x] v1 and v2 SQLite stores migrate sequentially to v3 without changing existing landing jobs. Snapshot validation, restore, and round-trip preserve the new record.
- [x] OpenAPI and runtime registration keep the new routes exclusive to `landing_only=True`; existing landing job v1 semantics remain unchanged.
- [x] Documentation names the historical attestation boundary, separates probes from pilot jobs, and describes operator use and backup coverage.

## Failure and edge cases

- Invalid profile/scope/kind: reject before reservation and before provider call.
- Store reservation failure: do not call provider.
- Provider timeout/rejection/protocol error: persist a bounded failed result if the call outcome is known; do not persist upstream bodies.
- Server crash after dispatch marker but before terminal result: expose ambiguous/incomplete status; never auto-dispatch again for that probe ID.
- Duplicate concurrent idempotency key: exactly one reservation and at most one provider dispatch.
- Backup/restore: preserve IDs/digests/terminal or ambiguous status, without provider access.

## Non-functional requirements

- Security: UDS filesystem permissions plus operator actor-kind check and dedicated narrow scope; no credentials or provider bodies in storage, errors, or logs.
- Reliability: one SQLite writer, transactionally persisted reservation, append-only finalization, no hidden retry.
- Performance: bounded one-call operation using current provider timeout constraints; GET performs no network calls.
- Observability: query by probe ID; status, attempt count, elapsed time, and bounded failure details are durable.
