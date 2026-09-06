# Release plan — Add default-off live Grok and live Qwen landing executors plus explicit Python/system requirements for the current host configuration; no live API calls in tests; no landing-repo mutation.

## Deployment

Source-only. No VERSION bump, tag, or host change in this slice.

## Feature flags / staged rollout

Constructor injection only. Shipped server stays unavailable. Env names are placeholders.

## Metrics and alerts

Existing landing job `state`. `live_url` remains null.

## Go/no-go criteria

Local `grok_verify --mode pr` PASS plus independent code and test reviews. Not merge authority.
