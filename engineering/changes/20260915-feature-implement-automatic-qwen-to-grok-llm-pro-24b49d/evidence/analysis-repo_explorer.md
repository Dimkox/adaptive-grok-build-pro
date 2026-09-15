# Qwen → Grok failover: submission and replay inventory

- Route: `24b49d0529c8`; inspected source HEAD: `7b147366a1f9b7e4b59f17e10283cc8ad67ba0c8`.
- Role: read-only repository analysis; report recorded 2026-09-15 12:21 UTC. No product changes, tests, credential/config reads, log-body reads, or provider calls.
- Scope: existing local landing submission API and durable job semantics. Findings below describe implemented behavior; proposed failover rules are design inferences, not accepted or verified implementation.

## Caller contract and identity

1. Unix-socket HTTP is supported; a real client pattern already appears at `factory/tests/test_server.py:596` (`httpx.HTTPTransport(uds=...)`). No existing cross-service failover client/journal was found. The installed landing host does not expose general `/v1/tasks`: `factory/src/adaptive_factory/api.py:627` returns the landing-only application before those routes.
2. `POST /v1/landing-inputs` sends raw media bytes with `Authorization: Bearer …`, `Idempotency-Key`, `X-Correlation-ID`, `X-Repository-ID`, `X-Exact-Base-SHA`, `X-Exact-Base-Tree`, and `Content-Type` (`api.py:488`). The idempotency key is the job ID. Header IDs match `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}` (`api.py:44`). Bearer authentication maps separately configured credentials to actors; scopes are `landing:submit`, `landing:read`, and `landing:cancel` (`api.py:80`, `api.py:488`, `api.py:540`, `api.py:566`). A primary-service token/actor cannot be assumed valid or equivalent at the secondary.
3. Reads use `GET /v1/landing-jobs/{job_id}` and `/result`, with read scope, repository, and correlation headers (`api.py:540`, `api.py:599`). Cancellation uses a separate idempotency key (`api.py:566`). Tenant identity comes from the authenticated actor. The service authorizes the fixed landing target repository and requires its pinned exact base SHA/tree (`landing_service.py:278`, `landing_service.py:474`).
4. Submission buffers the bounded body, then awaits the synchronous service in a thread (`api.py:251`). The service retains its lock through normalization/build and returns after persisting the resulting state (`landing_service.py:293`, `landing_service.py:326`). Thus HTTP **202 is returned after processing**, not as an immediate durable enqueue acknowledgment. Caller disconnect/timeout does not establish that processing stopped.

## States, information loss, and restart

`factory/src/adaptive_factory/landing_service.py:514` permits:

| State | Allowed subsequent states, besides itself |
|---|---|
| accepted | normalizing, provider_unavailable, rejected, needs_human, cancelled |
| normalizing | generating, provider_unavailable, rejected, needs_human, cancelled |
| generating | evaluating, artifact_ready, needs_human, cancelled |
| evaluating | artifact_ready, needs_human, cancelled |
| artifact_ready / provider_unavailable / rejected / needs_human | cancelled |
| cancelled | none |

Normal execution persists `normalizing`, invokes one normalizer, persists `generating`, builds, then persists `artifact_ready` (`landing_service.py:378`). The normal path does not separately persist `evaluating`. There is no terminal-failure-to-normalizing retry transition. Result reads return 409 while nonterminal (`landing_service.py:370`). Cancellation waits for the same submit lock, so it does not interrupt an in-flight provider call (`landing_service.py:343`).

Public job views expose only version, job ID, state, and input digest; result views add artifact digest and a null live URL. Neither exposes failure reason, attempt phase, profile, usage, or provider evidence (`landing_service.py:79`). The internal `http_outcome_unusable` outcome already collapses executor, contract, transport, and decoding failures (`factory/src/adaptive_factory/landing_http.py:254`). Generic service provider exceptions become `provider_unavailable/provider_error` (`landing_service.py:447`). Therefore existing public terminal states are insufficient to infer whether a provider request was sent, charged, refused, or failed before sending.

SQLite startup recovery changes interrupted rows to `needs_human`: accepted → `input_unavailable_after_restart`; normalizing → `provider_outcome_ambiguous`; generating/evaluating → `local_run_interrupted`. Recovery is bounded and never replays providers (`factory/src/adaptive_factory/landing_sqlite_store.py:373`; tests at `factory/tests/test_landing_sqlite_store.py:247` and `:292`).

## Same input at the secondary

- Same-service idempotency is durable and tenant/repository/job scoped. An identical replay returns the retained row without calling the provider or builder; changed source material conflicts (`landing_sqlite_store.py:178`; `landing_service.py:323`). Existing tests verify this across restart and after provider failure (`test_landing_sqlite_store.py:173`; `factory/tests/test_landing_api.py:318`).
- Independent services/databases provide **no cross-service deduplication**. Reusing the primary job ID on Grok is a new independent execution, not continuation of the Qwen attempt.
- `LandingInputV1.input_digest` binds job, tenant, repository, exact base, site, media, byte length/content hash, quarantine reference, and received/expiry timestamps (`factory/src/adaptive_factory/landing_contracts.py:212`). It does not bind the provider. Same-service replay reuses existing timestamps, while fresh secondary intake generally produces a different input digest. Provider evidence must match each service's own input/profile digest (`landing_service.py:391`); copying primary evidence or expecting identical cross-service input digests is invalid.
- A controller needs its own durable logical-input identity plus a map of service/actor/job/input/profile bindings. Preserve the exact raw payload and media metadata for the permitted retry lifetime: the service purges the input blob after terminal processing and public APIs do not export original input (`landing_service.py:335`; `factory/src/adaptive_factory/landing_intake.py:231`). Each target must independently accept the media type and exact source identity; do not assume all profile inputs overlap.

## Delivery classification required for failover

These are design inferences from the implementation, not existing fallback behavior:

| Observation | Delivery conclusion and bounded response |
|---|---|
| Fresh attempt fails socket connect with ENOENT/ECONNREFUSED before transmitting any request, with no older unresolved attempt | That attempt was not delivered. Eligible for one recorded secondary attempt if its authorization/input/profile checks pass. |
| Primary unit reported stopped | Useful availability signal only. It cannot establish that an earlier request was never sent or charged; combine with durable attempt history and actual connect stage. |
| 401/403, input/media validation rejection, or exact-source conflict | Request/authority/input problem. Do not reinterpret it as provider outage or bypass it by switching credentials/providers. |
| Write/read timeout, reset after possible transmission, lost response, or controller crash after send | Ambiguous delivery. Retain original attempt identity and reconcile/poll it; do not label it unsent or free. A read 404 alone cannot eliminate a concurrently progressing submission before its row is created. |
| Primary returns artifact_ready | Select the retained primary result; no secondary generation needed. |
| Primary returns provider_unavailable or needs_human | Public v1 does not supply enough evidence to classify safe fallback. Add durable structured phase/reason/usage observations or operate below that information-loss boundary. |
| Secondary response is lost | Reconcile the same recorded secondary job. Never allocate a new secondary job merely because its response was lost. |

Any policy permitting a second model call after an ambiguous provider outcome must explicitly reserve/account for unknown primary usage and the additional attempt. It cannot claim exactly-once provider execution. Retained input, fallback intent, attempt identity, and the chosen winner must survive controller restart; otherwise retries can duplicate generation or lose attribution.

A fallback implemented only inside the Qwen service cannot handle that service being stopped. Covering process unavailability requires an independent caller/controller or an independently running ingress component with access to both sockets and separately scoped credentials.

## Minimal test leverage and remaining acceptance

- Extend existing auth/replay/conflict tests (`test_landing_api.py:243`) and no-repeat-on-failure coverage (`test_landing_api.py:318`). Preserve tenant isolation and full input binding.
- Reuse durable restart/recovery tests (`test_landing_sqlite_store.py:173`, `:247`, `:292`); add controller crash after fallback intent, lost secondary response, and ambiguous primary reconciliation cases.
- Add real UDS tests for an absent/refused primary socket, primary success suppressing fallback, response loss after server acceptance, and bounded one-secondary dispatch. In-process TestClient tests do not prove stopped-process behavior.
- Runtime metadata only: both `adaptive-l5.service` and `adaptive-l5-grok.service` reported loaded, active/running, enabled; main PIDs were 698333 and 3597736. This verifies unit state only, not authentication/provider health or failover acceptance. Socket `stat` access was denied to this account; no further access attempted. No live failover or model test was performed.
