# Host is <ci-host>, not a laptop

Change ID: `20260824-task-c8e5e5`
Route: `c8e5e567a15d`

## Outcome

M0 spec/plan/activation name hostname **<ci-host>**. Trust CI must not publish host 8080 (SearXNG). Compose project `adaptive-trust-ci`, default publish `<loopback-trust-ci>`. GitHub egress uses existing app-stack `proxy-gateway` on `<loopback-proxy>`. No compose-up this slice.

## In scope

- Retract laptop language; host = `<ci-host>`
- Compose `name` + `TRUST_CI_API_HOST_PORT` default 18080
- Health curl examples 18080
- `decisions.md` three-sentence entry
- Document app-stack proxy for outbound GitHub (no credentials)

## Out of scope

- `docker compose up`, webhook, branch-protect, PEM, M0.2/M0.3, M1/M2
