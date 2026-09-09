# Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

Change ID: `20260906-add-default-off-live-grok-and-live-qwen-landing-4a8bbb`
Created: 2026-09-06T19:36:12+00:00
Risk: low
Complexity: standard
Domains: generic

## Problem

The injected live landing path can auto-seal the 20-member L5 artifact, but it still has no Grok or Qwen executor and no closed Python/system requirements record for this host.

## Outcome

Default-off Grok and Qwen landing executors implement `CodexLandingExecutor`, fail closed without an injected API key, and are proven only with `httpx.MockTransport`. Current host Python/httpx pins are frozen. `live_url` stays null. The shipped server stays unavailable.

## Scope

### In scope

- `landing_live_executors.py` Chat Completions adapters for Grok and Qwen
- Closed `LandingHostRequirementsV1` for this operator host
- MockTransport tests and fail-closed HTTP/credential paths
- Factory README table and `.env.example` placeholder names
- Architecture ownership of the HTTP module outside the dogfood `network: none` node

### Out of scope

- Real xAI/DashScope calls
- `.env` reads, server auto-enable, landing-repo mutation
- Non-null `live_url`, publisher transport, VERSION bump, M8, `80d6215` retarget

## Constraints

- Backward compatibility: default server path unchanged
- Data/privacy: constructor-injected keys only; tests use fake literals
- Performance: one mocked POST per successful `run`; no retries
- Operational: constructor-injected only; no merge/push/hosting in this slice
