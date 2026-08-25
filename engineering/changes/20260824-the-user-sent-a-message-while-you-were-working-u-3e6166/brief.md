# M0 host-socket overlay: first App-owned Check Run on claw

Change ID: `20260824-the-user-sent-a-message-while-you-were-working-u-3e6166`
Route: `3e61666b8de2`
Created: 2026-08-24T09:31:47+00:00
Risk: low (operator overlay; tracked compose unchanged)
Complexity: standard
Domains: generic
Write owner: `general_implementer`

## Problem

Nested rootless DinD (`docker-engine`) restarts on `claw` with `rootlesskit: fork/exec /proc/self/exe: operation not permitted`. Worker never reaches running. Container `HTTP_PROXY=http://127.0.0.1:1080` does not reach host glider. GitHub cannot POST to `127.0.0.1:18080`. User order «короче делай сам»: pick the simplest path and produce a live App-owned Check Run.

## Outcome

Worker running against the host Docker socket. One HMAC-signed loopback `POST /webhooks/github` for draft PR #5. GitHub shows Check Run `adaptive-trust-ci/verified@6737355947c2` owned by App `4694114` on the exact head SHA (`external_id` = durable `job_id`). Publication/ownership is success; `conclusion=success` is not required.

## Scope

### In scope

- Untracked host overlay outside the git tree (not `trust-ci/compose.override.yaml`)
- Stop crash-looping `docker-engine`; `up -d --no-deps runner-loader worker`
- Overlay `HTTP(S)_PROXY=http://host.docker.internal:1080` + `extra_hosts`
- Loopback HMAC POST for PR #5; observe App-owned Check Run
- Operator-safe activation-report fields if P0 holds

### Out of scope

- Edit tracked `trust-ci/compose.yaml`, tests, smoke.sh, systemd
- Public HTTPS webhook, Cloudflare, `branch-protect`, merge/ready PR #5
- PEM read, forged checks, GitHub Actions, M1–M9

## Constraints

- Backward compatibility: tracked product still documents isolated DinD
- Secrets: never print PEM, webhook secret, JWT, installation token
- Operational: leave postgres+api up; never `compose down -v`; host `:8080` stays SearXNG
- Four planes stay separate
