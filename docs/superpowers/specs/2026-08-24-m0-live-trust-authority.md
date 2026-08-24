# M0 — Live Trust Authority (activation spec)

## Objective

Turn the existing `trust-ci/` source (service 2.1.0, already on `main`) into the actual merge authority for `Dimkox/adaptive-grok-build-pro`. GitHub Actions remain absent. Local receipts, delegated grants, prompts, and agent reviews stay preflight only.

This spec **does not replace** `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` (the already-built service). That document still describes commit-status wording in places; the **operator contract** is the GitHub App Check Run `adaptive-trust-ci/verified@<policy-sha12>` bound to the Trust CI App ID (`trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, `AGENTS.md`).

## Baseline

| Item | Value |
| --- | --- |
| Repository | `Dimkox/adaptive-grok-build-pro` |
| Base SHA | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` (`origin/main` at design freeze) |
| Product version | 2.0.12 |
| Trust CI service | 2.1.0 |
| M1 typed spec | already on `main`; do not re-implement |
| M2–M9 | out of this branch |

## Live gap (freeze snapshot probed 2026-08-24, no secrets)

The table below is the **design-freeze** probe (listener not yet up; no Check Run). It is not the current claw state. Operator-safe live facts (PR #5, Check Run `97390635614`, job `needs_approval`, loopback HMAC, kill-switch drill) live in `engineering/runbooks/trust-ci-activation-report.md`.

| Probe | Result |
| --- | --- |
| `GET .../branches/main/protection` | HTTP 404 `Branch not protected` |
| `GET .../hooks` | empty |
| Check runs on `48cb973` | total 0 |
| PR #4 | merged; only GitGuardian; no `adaptive-trust-ci/verified@*` |
| `.github/` on `main` | absent |
| GitHub Actions registry | leftover workflow `trusted-ci` **id 340420982**, path `.github/workflows/trusted-ci.yml`, **state=active**, 0 runs on `main` |
| Docker | no Trust CI containers; leftover `adaptive-trust-ci-{api,worker,runner}:2.1.0` images not running |
| `127.0.0.1:8080` | SearXNG, not Trust CI `/health/ready`. Trust CI **must not** publish host 8080; published default is `127.0.0.1:18080` (`TRUST_CI_API_HOST_PORT`) |
| App installation ID | not queryable with the agent `gh` user token (401/403) |
| `trust-ci/runtime/github-app-private-key.pem` | filename present, gitignored; **not opened in this spec** |
| `runtime/policy.json`, operator `env/*.env` | absent (examples only) |

M0 was **source-complete and live-absent** at that freeze snapshot. The freeze table is retained. Live claw is documented in the activation report; M0.2 is still incomplete (no public HTTPS webhook).

## Trust boundary

**Trusted:** dedicated-host images pinned by digest, server policy, holdout digest, PostgreSQL, worker-only CI Ed25519 key, worker-only GitHub App RSA, API-only webhook HMAC secret, API-only human public-key store, branch protection bound to App ID.

**Untrusted:** pull-request tree, `AGENTS.md`, `.grok/**`, local receipts, delegated grants, agent output, GitGuardian, leftover Actions catalog entries. The agent workspace on `claw` is untrusted even though `claw` is the CI host. Trusted runtime is the deployed compose project `adaptive-trust-ci` (images, policy, holdout, PostgreSQL, keys), not the checkout.

## Role split

- API verifies webhooks and human approval signatures. It cannot hold App RSA, installation tokens, or publish a successful Check Run.
- Worker holds App ID + installation ID + RSA, mints a reduced installation token (`checks:write`, `contents:read`, `pull_requests:read`), publishes the Check Run, signs attestations. It must not receive the webhook secret or human trust store.
- Runner: no token, no key, no Docker socket, `network=none`.
- Human approval private keys never live on the CI host or in the agent workspace.
- `adaptive-trust-ci branch-protect` uses a **temporary human administration token**. The long-lived App must not have repository Administration.

## Check contract

- Name: `adaptive-trust-ci/verified@<first-12-hex of policy sha256>`
- `external_id` = durable PostgreSQL job id
- Owner = Trust CI GitHub App (`app.slug` = `adaptive-trust-ci`)
- Success is backed by a stored Ed25519 attestation, independently verifiable with the published CI public key
- Same check **text** from another actor does not satisfy branch protection

## Host

**Host is `claw`** (Xeon E5-2680 v4, ~16 GiB ECC, Ubuntu 24.04). The user named it. Port 8080 is SearXNG; n8n/Caddy and app databases share the Docker engine; privileged DinD remains residual risk the user accepted; `TRUST_CI_PUBLIC_BASE_URL` must still be HTTPS. The hostname gate for M0.1 is **satisfied**. Compose-up still needs `migration_or_external_write_approval`.

Required: Docker Engine + Compose v2 on `claw`, TLS reverse proxy to `/webhooks/github` and `/approvals`, named PostgreSQL volume and backup destination, host-owned policy/holdout/keys. Published API mapping is `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` with compose project `adaptive-trust-ci`.

- Outbound GitHub traffic from this host must use the existing `/home/pall/app-stack` `proxy-gateway` on `127.0.0.1:1080` (HTTP and SOCKS5). The operator sets `HTTP_PROXY`/`HTTPS_PROXY` in the **host-owned** worker environment. Never commit proxy secrets or read `glider.conf` / `secrets/`.

## Rollout order (binding)

1. Deploy API + PostgreSQL + worker on the dedicated host (`/health/ready`).
2. Register repository webhook `POST https://<ci>/webhooks/github` (API-only HMAC, `pull_request` events; drafts enqueue).
3. Disposable docs PR → observe App-owned Check Run on the exact head SHA → offline attestation verify → SHA/policy/holdout change, `trust-ci/**` needs_approval + human Ed25519 requeue of the **same** Check Run, source-mutation fail, kill switch, backup/restore/restart.
4. **Then** protect `main` with the exact epoch name **and** App ID. Disable leftover Actions workflow `340420982`. Supersede bootstrap-exception language because a live check exists — never by forging one.

Protecting `main` before the live check can lock the repository.

## GitHub App

Permissions: Checks read/write, Contents read, Pull requests read. Record App ID and installation ID in untracked `env/worker.env` and in the operator-safe activation report. Never commit PEM, JWT, installation token, webhook secret, or admin token.

## Human approvals

Created with `adaptive-trust-ci approval-create` on a human machine. Bound to repository, PR, base SHA, head SHA, policy digest, actor, key_id, nonce, TTL. Worker restarts the same durable Check Run.

## Exit criteria (verbatim + extras)

```text
main protected = true
required check = current adaptive-trust-ci/verified@<policy-sha12>
required check app_id = adaptive-trust-ci App ID
exact-SHA disposable PR = success
signed attestation = independently verified
protected-path approval flow = proven
backup + restore + restart drill = pass
kill switch = pass
no GitHub Actions = true
```

Also: leftover Actions workflow `340420982` disabled or deleted; bootstrap-exception language in `decisions.md` / README superseded.

## Forbidden

- `.github/workflows/**`, Dependabot CI, other CI SaaS
- Forging `adaptive-trust-ci/verified@*`
- Reading or committing PEM / human approval private keys
- Treating local receipts or delegated grants as merge authority
- Re-implementing M1; starting M2–M9; creating `factory/`
- Root `pyproject.toml` / `requirements.txt` / `setup.py`
- Auto-merge
- Protecting `main` before the live App-owned check
- Misnaming hostname `claw` (it is the named CI host, not a portable workstation)
- Publishing Trust CI on host 8080
- Stealing existing containers, volumes, or networks
- `compose-up` / webhook / `branch-protect` in this host-name slice
