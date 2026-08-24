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

## Live gap (probed 2026-08-24, no secrets)

| Probe | Result |
| --- | --- |
| `GET .../branches/main/protection` | HTTP 404 `Branch not protected` |
| `GET .../hooks` | empty |
| Check runs on `48cb973` | total 0 |
| PR #4 | merged; only GitGuardian; no `adaptive-trust-ci/verified@*` |
| `.github/` on `main` | absent |
| GitHub Actions registry | leftover workflow `trusted-ci` **id 340420982**, path `.github/workflows/trusted-ci.yml`, **state=active**, 0 runs on `main` |
| Docker | no Trust CI containers; leftover `adaptive-trust-ci-{api,worker,runner}:2.1.0` images not running |
| `127.0.0.1:8080` | SearXNG, not Trust CI `/health/ready` |
| App installation ID | not queryable with the agent `gh` user token (401/403) |
| `trust-ci/runtime/github-app-private-key.pem` | filename present, gitignored; **not opened in this spec** |
| `runtime/policy.json`, operator `env/*.env` | absent (examples only) |

M0 is **source-complete and live-absent**.

## Trust boundary

**Trusted:** dedicated-host images pinned by digest, server policy, holdout digest, PostgreSQL, worker-only CI Ed25519 key, worker-only GitHub App RSA, API-only webhook HMAC secret, API-only human public-key store, branch protection bound to App ID.

**Untrusted:** pull-request tree, `AGENTS.md`, `.grok/**`, local receipts, delegated grants, agent output, this laptop, GitGuardian, leftover Actions catalog entries.

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

This laptop is **forbidden** as the Trust CI host: port 8080 is SearXNG; n8n/Caddy and app databases share the Docker engine; privileged DinD must not sit next to those workloads; `TRUST_CI_PUBLIC_BASE_URL` must be HTTPS.

Required: a dedicated Linux CI host with Docker Engine + Compose v2, TLS reverse proxy to `/webhooks/github` and `/approvals`, named PostgreSQL volume and backup destination, host-owned policy/holdout/keys. User approved host-activation **intent**; M0.1 still requires the **hostname** and `migration_or_external_write_approval`.

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
- Using this laptop as the CI host
