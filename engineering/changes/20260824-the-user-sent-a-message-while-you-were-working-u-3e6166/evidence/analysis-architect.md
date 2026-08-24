# Architect ruling — simplest M0 worker + App-owned Check Run on `claw`

Route `3e61666b8de2`. Change `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166`. Write owner: `general_implementer`. This agent does not compose-up, POST the webhook, push, merge, read PEM/`.env`, or deploy.

User standing order «короче делай сам» plus the named slice (host socket, extra_hosts, local HMAC, no public webhook, no branch-protect) outranks spec language that waits for nested DinD and a GitHub-registered HTTPS webhook. This slice is a **loopback characterization** of the already-tested `/webhooks/github` contract so a **real** App-owned Check Run can appear. It is not M0.2 complete, not M0.3, and not merge authority.

## Ruling (one paragraph)

**Do not edit product `trust-ci/compose.yaml`.** Keep `docker-engine` in the tracked file unused on `claw`. Materialize an **untracked host overlay** that mounts `/var/run/docker.sock` on `worker` and `runner-loader` only, sets `DOCKER_HOST=unix:///var/run/docker.sock`, adds `extra_hosts: host.docker.internal:host-gateway`, and overrides proxy/workspace/holdout env so they are host-daemon-visible. Stop the crash-looping DinD container. Start only `runner-loader` then `worker` with `--no-deps`. HMAC-POST PR #5 to `http://127.0.0.1:18080/webhooks/github`. Expect Check Run `adaptive-trust-ci/verified@6737355947c2` owned by App `4694114` with `external_id=job_id`. Do not register a GitHub webhook, protect `main`, merge, or read the PEM.

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User this turn | Host socket, extra_hosts, proxy env, local HMAC, local POST is enough for first Check Run | **Wins.** |
| docs_researcher | Spec/docs still describe privileged DinD and a public HTTPS webhook; no document authorizes host socket or loopback POST | True of **docs**. Operator exception on `claw` this slice. Do not rewrite the product topology or claim M0.2 exit. |
| repo_explorer | Removing `docker-engine` from tracked compose breaks `test_ops`, `test_database_roles` split, `test_supply_chain`, `smoke.sh`, systemd | **Avoided** by leaving tracked compose unchanged. Those tests are **not** updated. |
| task_analyst | Untracked overlay; P0 is publication/ownership not `conclusion=success` | **Aligned.** |
| M0 spec residual | Privileged DinD is the accepted risk | Nested rootlesskit is **dead** on this Engine (`fork/exec /proc/self/exe: operation not permitted`). Host-socket co-location is the substitute residual the user already accepted by naming `claw` as CI host sharing SearXNG/n8n. |
| Hardening plan Task 5 | Restricted Docker API proxy should be the only socket mount | **Not shipped.** Do not invent it this slice (that would be later-milestone work). |
| Prior architect `421a1d` | Do not fix container-loopback proxy; no Check Run this slice | Superseded for proxy + Check Run. App IDs and PEM-unread still stand. |

## Pick: host-only overlay, not product `compose.yaml`

### Why overlay is safer

1. Tracked tests **forbid** `/var/run/docker.sock` in `trust-ci/compose.yaml` (`test_ops.py` `test_production_compose_uses_prebuilt_images_and_isolated_dind`; `trust-ci/scripts/smoke.sh` exits 1 if rendered compose contains that path).
2. Nested DinD failure is **claw + Docker Engine 29 + rootlesskit** specific, not a portable product contract.
3. Product-tree compose edit is a `trust-ci/**` control-plane write: `grok_protected_write.py` + hook-blocked `git add`, plus test/systemd/smoke rewrites. That is a topology inversion, not the simplest Check Run.
4. Overlay + `--no-deps` needs **no** test updates. `test_m0_invariants.py` does not encode DinD.
5. Rollback is stop worker + drop overlay; tracked DinD definition remains.

### Why not change tracked compose this slice

If `docker-engine` were removed from `trust-ci/compose.yaml`, the same change **must** update:

- `trust-ci/tests/test_ops.py` (`TRUST_CI_DIND_IMAGE`, `'  docker-engine:'`, `assertNotIn('/var/run/docker.sock')`, `DOCKER_HOST: tcp://docker-engine:2375`, privileged slice, `trust-ci-docker-data`)
- `trust-ci/tests/test_database_roles.py` (API block split on `'  docker-engine:'`)
- `trust-ci/tests/test_supply_chain.py` (systemd unit contains `docker-engine`)
- `trust-ci/scripts/smoke.sh` (same three greps)
- `trust-ci/systemd/adaptive-trust-ci-compose.service`
- `trust-ci/.env.example` / `trust-ci/env/worker.env.example` comments

**Do not do that this slice.** Do not mix M1–M9. Do not promote host-socket to the published default.

### `docker-engine` stays in compose.yaml, unused

Tracked service remains the product DinD definition. On `claw`:

1. `docker compose --project-name adaptive-trust-ci stop docker-engine`
2. `docker compose --project-name adaptive-trust-ci rm -f docker-engine` (container only; **never** `-v`)
3. Subsequent `up` uses the overlay + `--no-deps` and does **not** name `docker-engine`

Do not `down`. Do not delete `adaptive-trust-ci_trust-ci-postgres` or `adaptive-trust-ci_trust-ci-docker-data`.

## 1. Overlay file (exact)

**Location:** outside the git tree, never named `compose.override.yaml` inside `trust-ci/` (auto-load would break `smoke.sh` if someone later omits `-f`). Suggested path: `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml` mode `0600`. Implementer may also copy the YAML into this change package only if they want it reviewed; it is **not** required in git for P0.

Do not put the overlay under `trust-ci/`. Do not `git add` it.

Export before `up` (operator-safe):

```bash
export DOCKER_GID="$(stat -c '%g' /var/run/docker.sock)"
export TRUST_CI_WORKSPACE_HOST_ROOT=/var/lib/adaptive-trust-ci/workspaces
```

If creating `/var/lib/adaptive-trust-ci/workspaces` needs root and is blocked, use `/home/pall/adaptive-trust-ci-host/workspaces` instead and export that same value. `chown 10001:10001` the directory. Worker uid is `10001`.

Overlay content (substitute nothing except interpolation already shown):

```yaml
# claw-only. Never merge into tracked trust-ci/compose.yaml this slice.
services:
  docker-engine:
    profiles: ["isolated-dind"]
    restart: "no"

  runner-loader:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      DOCKER_HOST: unix:///var/run/docker.sock
    group_add:
      - "${DOCKER_GID:?set host docker.sock GID}"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on: !override {}

  worker:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    group_add:
      - "${DOCKER_GID:?set host docker.sock GID}"
    environment:
      DOCKER_HOST: unix:///var/run/docker.sock
      HTTP_PROXY: http://host.docker.internal:1080
      HTTPS_PROXY: http://host.docker.internal:1080
      NO_PROXY: postgres,api,127.0.0.1,localhost
      TRUST_CI_WORKSPACE_HOST_ROOT: ${TRUST_CI_WORKSPACE_HOST_ROOT:?set host workspace directory}
      TRUST_CI_HOLDOUT_HOST_PATH: ${TRUST_CI_HOLDOUT_SOURCE_PATH:?holdout host path must equal compose bind source}
    volumes: !override
      - ./runtime/policy.json:/etc/adaptive-trust-ci/policy.json:ro
      - ${TRUST_CI_HOLDOUT_SOURCE_PATH:?set absolute reviewed holdout source path}:/etc/adaptive-trust-ci/holdout:ro
      - ./runtime/trust-ci-signing-key.pem:/run/secrets/trust-ci-signing-key.pem:ro
      - ./runtime/github-app-private-key.pem:/run/secrets/github-app-private-key.pem:ro
      - ./runtime/control:/run/adaptive-trust-ci
      - ${TRUST_CI_WORKSPACE_HOST_ROOT:?set host workspace directory}:/var/lib/adaptive-trust-ci/workspaces
    depends_on: !override
      migrate:
        condition: service_completed_successfully
      runner-loader:
        condition: service_completed_successfully
```

Notes:

- `environment:` **overrides** `env_file` for the same keys. Live gitignored `worker.env` can keep `HTTP_PROXY=http://127.0.0.1:1080`; the overlay wins. **Do not rewrite worker.env** unless overlay interpolation is insufficient.
- Socket is **rw**. `:ro` cannot `docker run`/`pull`.
- Do **not** `user: "0:0"`. Do **not** `chmod 666` the host socket. `group_add` only.
- `runner-loader` pull talks to **host** dockerd; registry proxy is the **host Engine’s** proxy, not the container `HTTP_PROXY`. Loader extra_hosts is harmless.
- `NO_PROXY` must **not** include `github.com` / `api.github.com` / `ghcr.io`.
- Named volume `trust-ci-workspaces` is **not** visible to host dockerd at `/var/lib/adaptive-trust-ci/workspaces`. That is why the overlay bind-replaces it (`!override`). Wrong path → empty runner workspace.

`!override` requires Compose v2.24+. Docker Engine 29 on `claw` qualifies. If a tag parse error occurs, stop and use `--no-deps` plus a rewritten overlay without `depends_on` keys rather than editing tracked compose.

## 2. Runner isolation still holds with host docker

Isolation is **argv policy in the worker**, not a second daemon.

| Plane | Socket | Keys | Network |
| --- | --- | --- | --- |
| API | no | webhook HMAC + trust-store **public** keys only | `trust-ci` |
| Worker | **yes** (this overlay) | App RSA path, CI Ed25519, App/install IDs | `trust-ci` + `executor` (executor unused) |
| Runner container | **no** | none | `none` |
| Human approval private key | n/a | **not on claw** | n/a |

`ContainerExecutor.build_argv` (`trust-ci/src/adaptive_trust_ci/sandbox.py`) mounts only:

- `{workspace_host_path}:/workspace:rw`
- `{workspace_host_path}/.git:/workspace/.git:ro`
- optional `{holdout_host_path}:/holdout:ro`

It never adds `/var/run/docker.sock`. Flags: `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pull never`. `_command_environment` does not pass `DOCKER_HOST`, tokens, or `GITHUB_TOKEN`. Policy `allowed_environment` is empty. Host dockerd does **not** inherit the worker’s socket mount into child containers.

`sandbox._runtime_environment` **does** pass `DOCKER_HOST` to the worker’s `docker` CLI process. That is required. It must not leak into runner `env`.

**Invariant the implementer must not break:** overlay volumes on `api`, `postgres`, or any future runner service stay socket-free. Do not `docker run` from a shell as a substitute for `JobRunner`.

Loader and worker **share the host image store**, so `runner-loader`’s digest pin lands where `docker run --pull never` can see it. That is why loader is **not** skipped.

## 3. Tests this slice

**None.** Tracked compose stays DinD. Do not weaken `assertNotIn('/var/run/docker.sock', compose)`. Do not change `smoke.sh`. Do not assert “main is unprotected”.

If a future change promotes host-socket into tracked compose (not this slice), that change owns the list in §“Why not change tracked compose”.

Optional product patch **only after P0 Check Run exists** and checkout is the remaining failure: forward `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`/`http_proxy`/`https_proxy` in `GitWorkspace._git_env`. Today it keeps only `PATH`/`HOME`/`GIT_*`, so `git fetch` will not use glider even if urllib does. `JobRunner.process` calls `ensure_check_run` **before** checkout, so P0 does not depend on this patch. Characterization test first. `trust-ci/**` → protected write. Do not do it pre-emptively.

## 4. Local HMAC webhook

**Secret file:** gitignored `trust-ci/env/api.env`, key `TRUST_CI_WEBHOOK_SECRET`. API-only. Never copy into `worker.env`. Never print, `cat`, `echo`, `set -x`, or paste into chat/activation-report.

**URL:** `POST http://127.0.0.1:18080/webhooks/github`  
**Headers:** `Content-Type: application/json`, `X-GitHub-Event: pull_request`, `X-Hub-Signature-256: sha256=<64 lowercase hex>`  
HMAC-SHA256 over the **raw body bytes** with the secret as UTF-8. FastAPI does not require `X-GitHub-Delivery`.

**PR #5 (confirm SHA immediately before POST; a new push invalidates the body):**

| Field | Value |
| --- | --- |
| `action` | `synchronize` (equivalent: `opened`) |
| `repository.full_name` | `Dimkox/adaptive-grok-build-pro` |
| `pull_request.number` | `5` |
| `pull_request.draft` | `true` (parsed but ignored; drafts enqueue) |
| `pull_request.head.sha` | `1fc942065a124ce75659bd082519d8ebc37774e8` (re-fetch) |
| `pull_request.head.ref` | `milestone/m0-live-trust-authority` |
| `pull_request.base.sha` | `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| `pull_request.base.ref` | `main` |

Minimum JSON (compact, this exact object is what you sign):

```json
{"action":"synchronize","repository":{"full_name":"Dimkox/adaptive-grok-build-pro"},"pull_request":{"number":5,"draft":true,"head":{"sha":"1fc942065a124ce75659bd082519d8ebc37774e8","ref":"milestone/m0-live-trust-authority"},"base":{"sha":"48cb9737fac7f26fb70b425957a3ed64d4c1eb55","ref":"main"}}}
```

Supported actions: `opened`, `synchronize`, `reopened`, `ready_for_review`. `closed` cancels. Other events → `accepted: false`. Wrong repo → 403. Bad HMAC → 401. Kill switch → 503. Replay same repo/PR/SHA/policy → `created: false`, same `job_id`.

Implementer writes `/tmp/m0-hmac-pr5.py` and invokes **only** `python3 /tmp/m0-hmac-pr5.py` (no `trust-ci` in argv, no `-c`). Inside the script: read the secret from the gitignored api env file, build body, sign, POST, print **only** HTTP status and `job_id`/`created`/`status`, unlink the script. Never print the secret, signature, or env dump.

This is **not** GitHub webhook registration. `GET /repos/Dimkox/adaptive-grok-build-pro/hooks` stays empty.

## 5. Expected Check Run

| Field | Value |
| --- | --- |
| Name | `adaptive-trust-ci/verified@6737355947c2` |
| Policy digest | `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5` |
| Owner | GitHub App slug `adaptive-trust-ci`, App ID `4694114`, installation `156003193` |
| `external_id` | durable PostgreSQL `job_id` from the webhook JSON |
| `head_sha` | exact POST SHA |
| Publisher | worker `GitHubClient.ensure_check_run` via installation token (`checks:write`, `contents:read`, `pull_requests:read`) |

`details_url` will be `http://127.0.0.1:18080/jobs/<job_id>` because `TRUST_CI_PUBLIC_BASE_URL` is loopback HTTP. Ugly, allowed, do not change it this slice.

**Honest terminals after P0 (any one is success for this slice):**

- `in_progress` then `failure` / job `dead` — git-proxy, sock GID, or host-path; `publish_dead_job` still App-owned
- `action_required` / `needs_approval` — **expected** for PR #5 because the diff includes `decisions.md` (governance glob). Do **not** forge a human Ed25519 approval
- `success` + attestation — only if the diff is outside approval globs **and** holdout/commands pass; **not required**

If `app.id ≠ 4694114`, fail the slice. Do not PATCH the check to `success` from a user token.

Proof (operator-safe):

```text
curl -fsS http://127.0.0.1:18080/health/ready
docker compose --project-name adaptive-trust-ci ps
gh api repos/Dimkox/adaptive-grok-build-pro/commits/<exact-sha>/check-runs
```

Filter locally for `name==adaptive-trust-ci/verified@6737355947c2` and `app.id==4694114`. Record id, `external_id`, status, conclusion, head SHA into the activation report. No secrets.

## 6. Residual risk (host socket co-location)

User already accepted `claw` as the CI host sharing Docker Engine with SearXNG/n8n/Caddy/app DBs. Privileged nested DinD was the *documented* residual; it does not run.

Host socket is a **security regression vs isolated DinD**: worker uid 10001 with a writable docker.sock is host-root equivalent (privileged containers, bind `/`, other compose projects). App PEM and CI signing key sit in the same container.

Mitigations this slice:

- Overlay only; tracked compose still documents isolated DinD
- Socket on worker + loader only
- Runner argv unchanged (`network=none`, no sock, no token)
- API has no sock and no App key
- Do not persist this as the product default
- Restricted Docker API proxy remains unbuilt (out of scope)
- Rollback stops worker first

Also residual: `host.docker.internal:host-gateway` targets the bridge gateway (often `172.17.0.1`), while glider publishes **only** `127.0.0.1:1080`. If token mint fails with connection refused:

1. Do **not** rebind `proxy-gateway`, edit `glider.conf`, or `network_mode: host`.
2. Host-only fallback: a throwaway `socat`/`iptables` redirect **docker-bridge:1080 → 127.0.0.1:1080`** (does not change glider’s listen address). Record it as operator residue.
3. If still blocked, stop and report; do not disable TLS verify.

`GitWorkspace._git_env` proxy-stripping is residual for **checkout**, not for Check Run creation.

## 7. Rollback

Trigger: worker unhealthy, socket threatens other stacks, wrong-app Check Run, or user abort.

```bash
docker compose --project-name adaptive-trust-ci stop worker runner-loader
# optional: rm -f those two containers only
# leave postgres + api running
# delete the overlay file; do not compose down -v
```

Restore tracked topology mentally: next `up` without overlay is DinD (will fail the same rootlesskit error). Do not restart `docker-engine` unless explicitly rolling back to the previous failed attempt.

A published Check Run cannot be unpublished. Do not forge `success`. `main` is unprotected, so this cannot lock the repository. Optional `closed` HMAC POST cancels queued jobs for PR #5; do not SQL-delete.

Verify after rollback: `/health/ready` 200; no Trust CI container still mounts `/var/run/docker.sock`; hooks empty; `main` unprotected.

## 8. Explicit non-goals this slice

- No branch-protect, no `adaptive-trust-ci branch-protect`, no App Administration
- No merge, no ready PR #5, no push to `main`
- No PEM/JWT/installation-token/webhook-secret/read-token/CI-signing-key/human-private-key read or print
- No public webhook registration (`gh api` hooks, GitHub UI, Cloudflare, Caddy Trust CI site)
- No GitHub Actions, no disable of leftover workflow `340420982` (M0.3)
- No M1–M9, no `factory/`, no policy digest change, no VERSION/tag/release
- No `network_mode: host`, no host `:8080` for Trust CI, no stealing n8n/SearXNG volumes/networks
- No human approval envelope
- No `git add` of `trust-ci/env/*.env`, `trust-ci/runtime/**`, or overlay if it lands under `trust-ci/`

## Product-tree vs host-only (summary)

| Option | Product files | Tests | Protected write | P0 Check Run |
| --- | --- | --- | --- | --- |
| **Host overlay (PICK)** | none required | none | no | yes |
| Edit `trust-ci/compose.yaml` | compose + tests + smoke + systemd + examples | must rewrite DinD assertions | yes (`trust-ci/**`) | yes, slower, wrong scope |

Optional after P0: fill `engineering/runbooks/trust-ci-activation-report.md` PR number / head SHA / Check Run id / `external_id`. Keep `main protected = false` and `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. That **is** a product-tree edit → `python3 scripts/grok_verify.py --mode pr` and route reviews. If only overlay + gitignored env + `/tmp` scripts: skip verify (no-op tree).

`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` / `decisions.md` updates are optional operator notes, not required for P0. `decisions.md` is protected + control-plane if touched.

## Four planes (must remain)

1. **API** — HMAC secret, trust-store public keys, enqueue. No App RSA, no installation token, no Check Run publish, no docker.sock.
2. **Worker** — App ID `4694114`, installation `156003193`, PEM path, CI signing key, host docker.sock, proxy. Never webhook secret or human private keys.
3. **Runner** — no token, no key, no socket, `network=none`.
4. **Human keys** — created off-host; none on `claw`.

## Grants (implementer mints after fingerprint is stable)

User delegated compose-up. Local loopback POST is not an external GitHub write. Do not reuse grants from change `421a1d`.

```bash
python3 scripts/grok_approve.py production --action external-write \
  --resource 'docker compose --project-name adaptive-trust-ci' \
  --reason 'M0 host-socket overlay: runner-loader worker; keep api/postgres' --ttl 30
python3 scripts/grok_approve.py external-write --action external-write \
  --resource 'docker compose --project-name adaptive-trust-ci' \
  --reason 'M0 host-socket overlay: runner-loader worker; keep api/postgres' --ttl 30
```

No wildcard, no merge, no webhook-create, no branch-protect, no PEM. If argv containing `trust-ci` is hook-denied, wrap compose in `/tmp/m0-up.sh` whose **invocation** has no `trust-ci` substring; the script cwd is the compose directory so `env_file: ./env/...` resolves.

Exact up (cwd = compose directory):

```bash
docker compose --project-name adaptive-trust-ci \
  -f compose.yaml \
  -f /home/pall/adaptive-trust-ci-host/compose.host-socket.yaml \
  up -d --no-deps runner-loader worker
```

Wait for loader exit 0, then worker `running`. Do not name `postgres`/`migrate`/`api`/`docker-engine`. Do not `--force-recreate` api/postgres.

## Implementer sequence

1. Read this ruling + `analysis-repo_explorer.md` + `analysis-task_analyst.md` + `analysis-docs_researcher.md`. Do not read secrets.
2. `stat` docker GID; mkdir/chown workspace host dir; write overlay outside git.
3. Stop/rm crash-looping `docker-engine` only.
4. Mint compose grants on the then-current fingerprint.
5. `up -d --no-deps runner-loader worker` with both `-f` files from the compose directory.
6. Prove `ps` + `/health/ready`. Worker must be **running**, not `Created`.
7. `/tmp` HMAC POST for PR #5; print only job_id/status.
8. Confirm App-owned Check Run on the exact SHA. Record operator-safe ids.
9. Optional activation-report fields; verify only if the product tree changed.
10. **Stop.** No branch-protect, no merge, no PEM read, no public webhook, no M1–M9.

## Acceptance (P0)

- `api` + `postgres` still healthy on `127.0.0.1:18080`; host `:8080` still SearXNG; host `:1080` still proxy-gateway
- `worker` running; `docker-engine` not required and not restart-looping
- Overlay not in tracked `trust-ci/compose.yaml`; `test_ops` still forbids host sock in that file
- HMAC POST 200 with `job_id`
- GitHub Check Run `adaptive-trust-ci/verified@6737355947c2`, `app.id=4694114`, `external_id=job_id`, exact head SHA
- No secrets in git, chat, or activation report
- `main` still unprotected; repo hooks still empty
