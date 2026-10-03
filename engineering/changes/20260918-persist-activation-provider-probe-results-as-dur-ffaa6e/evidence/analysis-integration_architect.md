# Integration architect findings — durable activation probes (#121)

Read-only inspection of the active package route `ffaa6e006773` and current landing host/client boundaries.

## Server and authorization boundary

`adaptive-landing-server` is the correct owner: `landing_host.py::build_landing_app` composes one `SQLiteLandingJobStore`, installs the landing-only FastAPI routes, and closes the store through application lifespan. `landing_host.py::main` serves that app on the existing owner-controlled Unix socket created by `server.prepare_unix_socket`; the host has no TCP listener. The app invokes `install_backend_api` only when `landing_only=True`, so a probe operation can remain absent from the general factory server.

Authentication is bearer-token plus scope via `Authenticator.authenticate`, but that helper checks scope only; it does not require `Actor.kind == "operator"`. Probe trigger and read routes must explicitly require operator kind and a dedicated narrow scope, and bind to the configured repository/profile. Existing landing scopes (`landing:submit`/`landing:read`) are too broad because a probe triggers provider spend. Unix-socket filesystem permissions add a local OS boundary but do not replace application authentication.

Existing UDS request patterns are already established in `factory/src/adaptive_factory/cli.py` (`httpx.HTTPTransport(uds=...)`, bearer token, correlation/idempotency headers) and `landing_failover_cli.py`/`landing_failover.py` (dedicated landing socket, backend capability/read before submit, bounded error handling). Reuse those patterns. Do not expose provider credentials or raw provider responses to the client.

## Idempotency and interruption

The current `probe_qwen()` performs one synthetic provider request, uses the selected HTTP profile timeout (60 seconds by default, bounded up to 300), disables redirects and environment proxies, configures no retry, and maps timeout/transport/provider failures to safe `LandingProviderError` categories. It returns sanitized digests, usage and elapsed time but has no persistence. The API should execute the probe in the server using the active host's selected profile and credential; calling this helper unchanged from an API route would retain a second credential-loading path.

Persist a unique probe reservation before dispatch, then atomically mark the single request attempt as started before invoking the executor. Do not hold a SQLite transaction across provider I/O. A duplicate or concurrent request with the same probe ID and identical closed request/profile identity reads/returns current state and never dispatches again; reuse with a different identity conflicts. A completed probe returns the stored terminal result. A timeout that returns normally from the executor becomes a safe terminal `deadline` observation with one initiated request; pre-dispatch validation failures record zero. If the server dies after the committed started marker, readback must report an ambiguous/incomplete attempt and retries must not call the provider again; operator must choose a fresh ID. This is necessary because a lost response cannot reveal whether a request reached the provider. `provider_requests` should mean attempts initiated by this adapter, not provider acceptance or billable calls.

## OpenAPI and parity tests

`landing-dogfood.v1.json` is the frozen v1 job contract. The separate `landing-failover.v1.json` describes backend capability and attempt receipts, but neither contract currently includes probe trigger/readback. Keep job v1 unchanged and add a closed, operator-scoped probe contract (a dedicated `landing-probe.v1.json` is clearest; alternatively extend the dedicated backend v2 contract if its operator-only scope and versioning remain explicit). Include POST trigger and GET exact-ID readback, idempotency/correlation headers, pending/ambiguous/terminal states, bounded fact fields, and auth/error responses; never include credentials, request/response bodies, prompt text, or draft text.

`factory/tests/test_openapi_contract.py` compares static contract operations to runtime operation IDs for always-visible landing routes. Add equivalent assertions for the probe contract and exercise it against a `landing_only=True` app. Test operator+scope succeeds; wrong actor kind, missing scope, and ordinary submit/read clients are denied; probe routes do not appear on the general factory app. Ensure response schemas are closed and bounded. Add behavioral tests for same-ID retry/concurrency (one provider call), conflicting identity (409), readback with no provider replay, timeout classification, and crash/interruption after request-started (ambiguous record, no retry).

No product files were changed during this analysis.
