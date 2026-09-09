# Architecture — Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

## Current behavior

`compose_landing_live` injects any `CodexLandingExecutor` into normalize→render→evaluate→seal. The dogfood landing files are `network: none` and may not import `httpx`. The shipped server uses `UnavailableLandingProvider`.

## Proposed behavior

HTTP Chat Completions adapters live in `factory/src/adaptive_factory/landing_live_executors.py`. Named composers `compose_landing_live_grok` / `compose_landing_live_qwen` inject those executors into the existing live path. Default server composition is unchanged. Tests inject `httpx.MockTransport`.

## Components and boundaries

- `NODE-FACTORY-LANDING-DOGFOOD` stays `runtime.network: none` and does not own the HTTP module.
- `NODE-FACTORY-LANDING-LIVE-EXECUTORS` owns `landing_live_executors.py`, `declared_egress`, no mounted secrets (keys are constructor-injected).
- `NODE-FACTORY-LANDING-MODEL-PROVIDER` is an `external_system` in `TD-FACTORY-CONTROL` so factory does not cross `TD-EXTERNAL-PLATFORM`.
- `EDGE-FACTORY-LANDING-LIVE-EXECUTORS`: python_import dependency onto the dogfood composer.
- `EDGE-FACTORY-LANDING-LIVE-MODELS`: allowlisted HTTPS control edge.

## Data flow

Caller injects API key + optional transport → Chat Completions POST `/chat/completions` → assistant content bytes → `CodexLandingNormalizer` → existing seal path. `live_url` remains null.

## API and event contracts

No OpenAPI, event, or migration change.

## Bitrix-specific impact

- Modules/events/agents/components affected: none
- Cache and managed cache impact: none
- Installation/update/uninstall impact: none
- Core modification: forbidden unless explicitly approved.

## Decisions

Keep HTTP out of the dogfood fitness prefix. Do not mount Grok/Qwen secrets on the shipped server. Do not retarget the landing pin.

## Risks and mitigations

`new_network_client` / `new_edge` / `new_external_integration` escalate architecture post-risk. Mitigation: default-off, MockTransport tests, no env load, same-trust-domain provider node, no Trust CI/external-platform crossing.
