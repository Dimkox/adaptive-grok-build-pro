# Implementation — M0 host-socket overlay (P0 Check Run)

Write owner: `general_implementer`. Tracked `trust-ci/compose.yaml` was not edited.

## Changed files (git tree)

- `engineering/runbooks/trust-ci-activation-report.md` — PR #5, head SHA, Check Run id, `external_id`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.1 worker running via overlay; M0.2 not complete
- `decisions.md` — three-sentence overlay + HMAC Check Run note
- `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166/evidence/*` — wrappers, overlay source copy, this report

Untracked host overlay: `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` (mode 0600). Not git-added.

## Commands (no secrets)

- `stat` docker GID `988`; workspace `/home/pall/adaptive-trust-ci-host/workspaces` `chown 10001:10001`
- Stop/rm container `docker-engine` only (no `-v`)
- `docker compose --project-name adaptive-trust-ci -f compose.yaml -f <host overlay> up --no-deps runner-loader` then `worker`
- Host `socat TCP-LISTEN:1080,bind=172.17.0.1` → `127.0.0.1:1080` (glider unchanged)
- Signing key host files `chown 10001:10001` mode `0440` (unread)
- HMAC `POST http://127.0.0.1:18080/webhooks/github` via `python3 /tmp/m0-hmac-pr5.py` with `NO_PROXY=*`
- One-row requeue of exhausted job after proxy 111 (attempts 3 while GitHub unreachable)

## Results

| Item | Value |
| --- | --- |
| health | `GET /health/ready` 200 |
| loader | exit 0 (digest already on host; ghcr pull unauthorized, inspect pin) |
| worker | running |
| webhook HTTP | 200 |
| job_id | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` |
| created | true (later requeued after dead) |
| job status | `needs_approval` |
| Check Run name | `adaptive-trust-ci/verified@6737355947c2` |
| Check Run id | `97390635614` |
| app.id | `4694114` |
| external_id | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec` |
| head SHA | `1fc942065a124ce75659bd082519d8ebc37774e8` |
| conclusion | `action_required` (expected; PR touches `decisions.md`) |
| public webhook | still absent |
| main protected | false |

## Residual risk

- Host docker.sock on worker uid 10001 is host-root equivalent vs isolated DinD
- `socat` on `172.17.0.1:1080` is operator residue
- Loader does not pull from ghcr when unauthorized; relies on host image store
- Overlay `entrypoint` override required because worker image CLI is `adaptive-trust-ci`
- `GitWorkspace._git_env` still strips proxy (checkout residual, not Check Run)

## Rollback

Stop `worker` and `runner-loader`; leave postgres+api; delete overlay; stop socat. Do not `compose down -v`. Do not PATCH the Check Run to success.
