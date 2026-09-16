# Architecture — qwen-omni-intl profile and probe classification

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Current behavior

Omni is bound to the mainland host; `selected_profile`, the settings enum and `compose_env_landing` cannot express omni-on-international (and the env path cannot express omni at all); the probe prints one undifferentiated failure reason.

## Proposed behavior

One more profile in the same table with the international host and the pinned model, admitted by every gate that enumerates profiles, plus a bounded classification on probe failure. `HttpLandingProfile.__post_init__` re-reads the table, so an inconsistent profile cannot be constructed.

## Components and boundaries

- `landing_http.py` profile table (single source of endpoint/model/streaming/media facts).
- `landing_provider.py` now owns `EXECUTOR_CODE_CATEGORIES`/`FAILURE_CATEGORIES`, shared by the durable collapse and the probe, so `deadline`/`transport`/`accounting` are reachable in both views of the same failure.
- `landing_host_config.py`, `settings.py`, `landing_live_executors.py` enumerations; `landing_server.py` needs no change because it selects the composer from `profile.provider_id`.
- Untouched: `landing_failover_config.PROVIDER_ORDER`, the mainland omni binding, every existing digest.

## Data flow

host config / `FACTORY_LANDING_PROVIDER` → profile → request body (`stream`, `modalities`, `stream_options`, media content part) → SSE → observation/classification → durable job or probe output.

## API and event contracts

No machine contract is changed. The first attempt added `qwen-omni-intl` to the closed `profile` enum of
`landing-backend-capability.v1.schema.json`, and the fitness gate rejected the edit: the comparator cannot
represent object-valued enum members (json_schema → `unsupported_schema_keyword`; the failover OpenAPI that
`$ref`s the file → `unsupported_openapi_construct`; any `unsupported` hard-fails architecture), and the only
reviewed escape admits unchanged documents. The contract is therefore frozen until issue #104 decides between a
comparator extension and a v2 coexistence contract; drift is guarded in the meantime by
`test_profile_facts_keep_the_backend_capability_contract_shape`, which asserts declared profiles remain real and
every table profile emits the contract's exact fact shape. The probe's stdout is an operator interface extended
by two bounded fields.

## Governance context

No rule or digest restated as authority here.

## Bitrix-specific impact

None.

## Decisions

Add a profile rather than re-point the existing one: existing installations keep their endpoint, and region choice becomes configuration instead of a code edit. Keep the failover chain untouched, because that would silently change live routing for hosts that did not ask.

## Risks and mitigations

- Two omni profiles invite picking the wrong one for the key region: documented in the runbook table and in `factory/README.md`, and #86's 401-vs-200 measurement is recorded here. - Probe classification could leak: only allowlisted enums are printed, asserted by tests.
