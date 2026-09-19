# Architecture — durable activation probe observations

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This design applies only to new server-executed probes. The historical 2026-09-16 result (769/191, profile digest `4cc85b8a…`) remains an attestation; its original model/payload is unavailable and it will not be backfilled or re-created by a fresh call.

## Current behavior

`probe_qwen()` runs a synthetic provider request from a CLI, returns normalized digests/usage/timing, and has no durable identifier or store. The production landing server owns `SQLiteLandingJobStore` for the lifetime of its process under an exclusive-writer lock and serves an operator-only Unix socket. The existing snapshot/restore captures the complete `landing.sqlite3`; a sidecar database would be outside that inventory. Landing jobs are semantically end-to-end artifacts and remain separate from health/activation probes.

## Proposed behavior

Add an operator-scoped probe API only to the landing-only server app:

1. `POST /v1/landing-probes` accepts a caller-supplied idempotency key and allowlisted profile ID. It requires both filesystem access to the configured Unix socket and `actor.kind == "operator"` with the dedicated `landing:probe` scope. The server verifies the profile against configured runtime policy.
2. In one store transaction, reserve a unique `probe_id` and persist `pending` plus `request_started_at` before any provider network activity. Commit before dispatch.
3. The server executes the synthetic request itself through the configured provider runtime/credential. The client never submits a result assertion. No application-level provider retry is added.
4. Persist one immutable terminal record: `normalized` or an allowlisted `failed` state, profile/model ID and profile digest, synthetic input digest, normalized spec/response digests on success, usage, elapsed time, provider request-attempt count, safe failure category/status, and timestamps. Store no credential, raw prompt, raw response/body, or unbounded exception text.
5. `GET /v1/landing-probes/{probe_id}` reads the stored row without provider access. Repeating the same POST idempotency key returns the existing pending/terminal record and never starts another request.
6. On process restart, a row left `pending` after `request_started_at` is ambiguous. It remains `unknown`/incomplete for operator interpretation and is never silently reissued. Provider attempt count describes locally initiated attempts, not billing truth.

## Components and boundaries

- Add an append-only `landing_activation_probes` table owned by `SQLiteLandingJobStore`; do not encode probes as `landing_jobs` or `landing_commands`.
- Add sequential schema v2→v3 migration while retaining v1→v2→v3 migration. Existing jobs are unchanged.
- Extend closed schema inventory and backup snapshot identity validation/restore tests to schema v3. SQLite backup already includes committed WAL pages; no sidecar files or second writer are introduced.
- Add a separate closed OpenAPI contract for probe create/read; preserve frozen landing job v1. Keep routes out of the general factory app and expose them only when `landing_only=True`.
- Reuse Unix-socket actor authentication but explicitly check `actor.kind`; current `Authenticator` validates scopes and is not by itself an operator-kind check.
- Run probe execution server-side using the configured provider credential/runtime. Never send credential values to the client or persist them.

## Data flow and crash behavior

The durable reservation precedes dispatch. A crash before request-start leaves a reservation known not to have dispatched; a crash after request-start but before terminal commit is ambiguous. Both are queryable and cannot be retried under the same ID; an explicit operator action may create a new ID/new event. Distinct new probes remain distinct rows even with the same profile/input digest.

## API and event contracts

New contract: `engineering/contracts/openapi/landing-probe.v1.json` (or the repository's canonical equivalent discovered during implementation). Closed request/response schemas, bounded strings, exact scope, idempotency key semantics, safe error taxonomy, and GET-by-ID are required. Add route/contract parity and authorization tests. No asynchronous event or provider response is exposed.

## Rollout and recovery

Migration is additive and forward-only; v1/v2 stores migrate without rewriting landing records. SQLite backup/restore remains the recovery path and must be exercised with a probe row. If API behavior fails, disable the new probe route while retaining rows; do not delete observations or roll back the schema destructively. Existing provider execution defaults and services remain unchanged.

## Decisions

- Future probes are durable; the old 769/191 response remains historical attestation only.
- Probe is a first-class append-only observation, not a landing job.
- The landing server is the sole writer and performs the provider call itself.
- Idempotent retries never cause a second provider call; ambiguous post-dispatch interruption is not replayed.
