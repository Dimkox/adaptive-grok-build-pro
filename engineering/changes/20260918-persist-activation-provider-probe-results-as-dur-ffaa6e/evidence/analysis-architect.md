# Architect analysis — durable activation provider probes (#121)

Base inspected: `2f66ba6ef82d0f6a0bb3a4389e7f03b393c99217`; route `ffaa6e006773`. Scope is one operator-triggered provider capability probe, durable re-derivation, and clear separation from landing pilot work.

## Recommendation

Use a dedicated append-only activation-probe event table in the existing private `landing.sqlite3`, reached only through the server process that already owns `SQLiteLandingJobStore`. Add operator-only Unix-socket POST trigger and GET readback operations. Keep probe records separate from `landing_jobs`: a probe is not customer intake, has no landing repository/base revision, artifact lifecycle, or pilot/cohort semantics. Do not mint a synthetic `LandingInputV1` or land it as a fake normalized job.

The server-side route resolves the configured profile and credential itself. The request supplies only a stable bounded `probe_id`/idempotency key and correlation ID; it cannot select arbitrary provider/model, supply a credential, or pass prompt content. Fix the synthetic probe input in code. GET returns a closed redacted observation projection by exact ID.

## Durable identity, replay, and failure semantics

Represent state as immutable events keyed by `(probe_id, sequence)`, rather than updating a single row from pending to complete. A minimal lifecycle is `reserved` (sequence 0, committed before any provider effect), `request_started` (committed immediately before the one outbound request, with the attempt count), then exactly one terminal `normalized` or safe classified failure event. Store profile ID/digest and a digest of the closed probe request in the reservation; bind terminal facts back to them. Use the existing provider observation/evidence contracts where applicable, with their own digest, and include `provider_requests` explicitly because the existing observation type does not contain a request count.

POST with a new ID inserts and commits the reservation, then alone may execute the provider call. A concurrent/retried POST with the same ID and same request identity returns current durable state and never dispatches another call: `202`/pending for an unfinished attempt, completed projection for a terminal event. Reuse of an ID with a different profile or request digest returns `409`. A process death after `request_started` but before terminal persistence leaves an unresolved record; GET exposes it as ambiguous/pending with the recorded attempt count, and the same ID is never retried. The operator must choose a new ID for a new provider attempt. This avoids double billing after a lost response.

Define `provider_requests` as outbound request attempts initiated by this probe adapter, not provider acceptance or billable requests. There is an unavoidable ambiguity if the process dies at the network boundary; preserve `request_started` as evidence of an initiated attempt and never infer zero cost from missing usage. The current executor sends one request and configures no retry; preserve that. Persist only bounded categorical failure/status data and digests/counts. Do not store provider key, authorization header, raw response, prompt, generated text, or upstream error body. The response digest/spec digest and factual token usage suffice for this record's purpose.

Readback validates contiguous sequence numbers, legal transitions, single terminal result, event digests, stable request/profile identity, and the terminal provider observation. It must not re-run the provider. If the profile has since changed, keep the historical row readable as historical evidence, but expose digest mismatch against current configured profile rather than silently reinterpreting it. A normalized event is the only successful probe outcome; incomplete/failed/ambiguous events cannot satisfy an activation claim.

## Authorization and boundary

The existing landing Unix socket is owner-controlled and bearer-authenticated, but `Authenticator.authenticate` authorizes by scope only; it does not require `Actor.kind == "operator"`. The probe routes therefore need an explicit operator-kind check plus a dedicated `landing:probe` scope (and a repository wildcard/operator binding appropriate to this host-only action). Do not reuse `landing:submit` or `landing:read`: triggering a probe spends provider budget and must not be available to ordinary landing clients. The route remains local UDS only; no TCP listener or public endpoint. Bound request IDs, response size, execution deadline, and concurrent probes (at most one active probe per configured profile/store) to avoid provider-cost multiplication.

Use the active server profile/credential already selected by the private host configuration, not `probe_qwen`'s standalone environment/file-loading route. Pass a server-owned probe executor to the API/service and the owner store. This ensures the DB write uses the existing process-lifetime writer lock and avoids a second `SQLiteLandingJobStore` instance or direct SQLite connection. The current `probe_qwen` helper has no persistence and independently reads a Qwen credential; calling it from an API route without refactoring would create a parallel credential/config path.

## Migration and compatibility impacts

`landing_sqlite_store.py` is schema version 2 and validates an exact schema inventory of only `landing_jobs` and `landing_commands`. Add schema version 3 and an exact expected definition for the event table, indexes, constraints, and any append-only triggers. Keep `application_id` unchanged. Migration paths must be sequential and transactional: v1→v2 (existing nullable `observation_json` migration)→v3, and v2→v3; do not reinterpret or rewrite existing landing records. Validate a v1/v2 database against its old exact schema before applying each step, then validate v3 after migration.

Update SQLite store schema tests and hostile-schema tests, and preserve all old job CRUD/readback behavior. `landing_backup.py` currently accepts current schema plus v1 when making snapshots; specify whether v2 snapshots remain restorable and ensure v3 snapshots include probe rows unchanged. New backups and restored v3 DBs must return identical probe events/readback with no provider replay. A pre-v3 backup naturally has no probe table/record; state that boundary. Restore remains inactive-only and requires provider disabled. Older v2 binaries reject the v3 `user_version`; rollback after upgrade therefore requires a v3-capable reader or restoring a pre-upgrade v2 snapshot (which necessarily loses post-upgrade probe evidence). Document this as a forward schema upgrade.

`landing_publication_cli.py` checks `(APPLICATION_ID, SCHEMA_VERSION)` and reads only `landing_jobs`; its runtime import will follow the bumped constant, but test the publication path against v3 so it remains compatible. The additive routes belong in the landing dogfood OpenAPI contract; do not alter the frozen 17-operation `factory-control.v1` contract. Update actor/config examples and host runbook with the exact new scope and replay behavior.

## Invariants and verification targets

- A probe ID is reserved durably before any external request; same-ID retries never dispatch again.
- An ID is immutable across profile/request digest; mismatched reuse conflicts.
- Event rows are append-only, contiguous, digest-checked, and limited to a valid transition chain with at most one terminal result.
- Exactly one server-owned configured profile may be probed per request; caller cannot select model, endpoint, credential, prompt, or usage.
- Only an operator actor with the dedicated scope can trigger or read; submit/read clients and wrong-kind actors fail closed.
- Provider call occurs at most once per ID; concurrent duplicate trigger requests have one winner. Provider retry remains disabled.
- Crash before dispatch leaves `reserved`; crash after dispatch leaves `request_started`/ambiguous and is not replayed. Completed readback is byte-stable and makes no provider call.
- Usage is retained only when reported by the provider. Missing usage is unknown, never zero-cost. `provider_requests` counts initiated adapter requests and does not claim billing.
- Database schema v1 and v2 migrate forward preserving existing rows; v3 exact inventory rejects unowned/unexpected schema objects.
- Backup/restore roundtrip preserves v3 probe event bytes and readback, and invokes no provider. Older v2 backup behavior and rollback limitation are explicit.
- Probe records remain absent from `landing_jobs`, pilot counts, M8 cohorts, landing result routes, and artifact publication.

No product code was changed during this analysis. The issue's quoted prior probe is historical context; do not fabricate a v3 row by copying dossier text. A new durable record must arise from the newly authorized trigger path and its live provider result.
