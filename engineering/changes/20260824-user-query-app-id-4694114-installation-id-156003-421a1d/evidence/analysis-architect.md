# Architect ruling — M0.1-complete worker IDs on `claw`

Route `421a1ddd7770`. Change `20260824-user-query-app-id-4694114-installation-id-156003-421a1d`. Write owner: `general_implementer`. This agent does not compose-up, push, merge, register webhooks, branch-protect, or read `.env` / PEM / JWT.

User-supplied integers (operator-safe, not secrets): GitHub App ID `4694114`, installation ID `156003193`. The change-id slug truncates the installation id to `156003`; the env value and activation-report field **must** be the full `156003193`.

## Ruling

**This slice completes M0.1: patch gitignored worker-only IDs, then start `docker-engine` + `runner-loader` + `worker` on compose project `adaptive-trust-ci`, keeping the already-healthy `api` and `postgres`.** Do not register a GitHub webhook. Do not start M0.2/M0.3. Do not merge or ready PR #5. Do not add GitHub Actions. Do not read the App PEM.

Worker start **is** M0.1-complete even though GitHub cannot POST to `127.0.0.1:18080`. M0.2 webhook waits for a public HTTPS URL (app-stack Caddy site or operator hostname). A dead localhost/LAN webhook is forbidden.

Activation-report may record App ID and Installation ID. Never commit `trust-ci/env/worker.env`.

## Why this unblocks the worker

Previous claw ruling (`6346a3`) deferred the worker because `WorkerSettings` requires positive integers `TRUST_CI_GITHUB_APP_ID` and `TRUST_CI_GITHUB_INSTALLATION_ID`. Those are now user-provided. The gitignored PEM filename exists (`mode 0600`, unread). `GitHubAppAuth` does **not** read the PEM at process start; it reads it only when minting an installation token for a claimed job. With no webhook, no jobs enqueue, so M0.1 does not require a live GitHub round-trip.

`Worker.build()` does load the **CI Ed25519 signing key** (not the GitHub App RSA) and `Policy.load`. Policy `sandbox.image` must already match `TRUST_CI_RUNNER_IMAGE` from the M0.1 bootstrap. Do not rewrite policy this slice.

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User binding this turn | Patch worker.env IDs; `up -d docker-engine runner-loader worker`; keep api/postgres; no dead webhook | **Wins.** |
| Previous architect (`6346a3`) | Worker off until IDs exist without PEM/JWT | Satisfied. IDs exist; PEM still unread. |
| M0 plan leftover | `up … worker` deferred; worker env IDs `UNKNOWN` and not started | This turn ticks that M0.1 line. Rewrite the deferred sentence. Leave M0.2 webhook unchecked. |
| docs_researcher | `up -d postgres migrate api worker`; then webhook | Full README topology is not a new `postgres`/`api` start. Explicit service list only. Webhook **blocked** until public HTTPS. |
| task_analyst | IDs in worker.env + activation-report; start worker+DinD+loader; webhook only on real public HTTPS | **Aligned.** |
| repo_explorer | api+postgres healthy on `127.0.0.1:18080`; no host `:443`; n8n-proxy Caddy has no public HTTPS hostname | **Fact.** Do not invent a webhook URL. |
| Rollout README | Register HTTPS `/webhooks/github` after deploy | M0.2, not this slice. |

## Non-goals (forbidden this slice)

- `docker compose up` **without** an explicit service list (would be redundant; never omit the three names).
- Restarting or recreating `api` / `postgres`. Do not `down`. Do not `down --volumes`.
- Publishing host `8080` (SearXNG), `1080` (proxy-gateway), `443`, or any Postgres host port.
- Registering `/webhooks/github` (GitHub UI, `gh api`, App webhook API, or localhost URL).
- `branch-protect`, disabling workflow `340420982`, forging `adaptive-trust-ci/verified@*`.
- Merging/readying PR #5; starting M2–M9; creating `factory/`; adding `.github/workflows/**`.
- Reading or printing PEM, JWT, webhook secret, DB passwords, human approval private keys, `glider.conf`.
- `git add` of `trust-ci/env/*.env` or `trust-ci/runtime/**`.
- Putting App ID / installation ID / PEM path into `api.env`.
- VERSION/tag/release. Do not edit `README.md`.
- Rebinding `proxy-gateway` or adding a Caddy Trust CI site (operator/M0.2).

## Current host facts (read-only)

Hostname `claw`. `adaptive-trust-ci-api-1` healthy `127.0.0.1:18080->8080/tcp`. `adaptive-trust-ci-postgres-1` healthy, `5432` unpublished. `migrate` already exited 0. Worker/DinD/runner-loader are not running.

| Path / port | State | Rule |
| --- | --- | --- |
| `trust-ci/env/worker.env` | exists, `0600`, size 726; App/installation IDs are **non-integer** placeholders | In-place replace the two keys only. |
| `HTTP_PROXY` / `HTTPS_PROXY` in worker.env | already `http://127.0.0.1:1080`; `NO_PROXY=postgres,127.0.0.1,localhost` | Preserve. Do not rewrite the file from the example. |
| `trust-ci/runtime/github-app-private-key.pem` | filename exists, `0600`, unread | Do not open. Compose will mount it into `worker`. |
| `127.0.0.1:18080` | Trust CI API | Keep. |
| `127.0.0.1:8080` | SearXNG | Do not bind. |
| `127.0.0.1:1080` | `proxy-gateway` (loopback publish only) | Do not bind. Worker env already points here. |
| Host `:443` | **not listening** | No public HTTPS webhook target. |
| `n8n-proxy` Caddy | host `3001` and `5678` HTTP only; container 80/443 not on host 443 | Not a Trust CI public URL. |

## Hook constraint: `/tmp` script, argv without `trust-ci`

`trust-ci/**` is control-plane. `trust-ci/env/*.env` and `trust-ci/runtime/**` are secret-read. Structured `Read`/`Write` of `worker.env` is blocked. Bash whose command string contains the substring `trust-ci` **and** a mutation signal (`cp`/`sed -i`/`python3 -c`/redirection/…) is blocked even with a path grant. `python3 -c` is always a mutation signal.

`docker compose` is **not** a production_action and **not** a mutation signal. The user-named compose command is allowed in argv. If a hook still denies it, wrap compose in a second `/tmp` script whose argv has no `trust-ci` substring.

**Do not paste secrets into tool payloads or chat.**

### ID patch script (required)

Implementer writes `/tmp/m01-set-app-ids.py` (or similar). Invoke **only** `python3 /tmp/m01-set-app-ids.py` — no path, no `trust-ci`, no `-c`.

Inside the script (not argv):

1. Absolute path to the existing gitignored worker env file.
2. Read text; replace lines that start with `TRUST_CI_GITHUB_APP_ID=` and `TRUST_CI_GITHUB_INSTALLATION_ID=` with `4694114` and `156003193`. Leave every other line byte-identical (DSN, proxy, key paths).
3. Atomic write + `chmod 0600`.
4. Print only operator-safe status: `APP_ID=4694114 INSTALLATION_ID=156003193 PROXY_PRESERVED=yes OTHER_KEYS=untouched`. Never print DSN, passwords, or PEM.
5. Unlink the `/tmp` script after use.

Do **not** copy `worker.env.example` over the live file (it would clobber the worker DB password). Do not add App IDs to `api.env`. Optional one-line hardening while patching: append `docker-engine` to `NO_PROXY` if absent; not required for start.

## Compose-up (implementer only; after grant)

Working directory must be the compose file directory so `env_file: ./env/…` resolves. Explicit service list **exactly**:

```bash
docker compose --project-name adaptive-trust-ci up -d docker-engine runner-loader worker
```

`-d` is required so the command returns. `depends_on`: `docker-engine` healthy → `runner-loader` pull completes → `worker` starts. Already-running `api`/`postgres` stay up. Do not pass `postgres`, `migrate`, or `api` on this command.

`runner-loader` is a oneshot (`restart: "no"`) that `docker pull`s `TRUST_CI_RUNNER_IMAGE` **into DinD**, not the host engine. Host images are invisible to `trust-ci-docker-data`. If the pull fails, record the exact error and stop; do not `--force-recreate` api/postgres as a workaround; do not skip loader.

Proof (operator-safe; no env dump, no `docker logs` that might later contain tokens):

```text
docker compose --project-name adaptive-trust-ci ps
curl -fsS http://127.0.0.1:18080/health/ready
```

Expect: `docker-engine` running healthy; `runner-loader` exited 0; `worker` running; `api`/`postgres` still healthy; ready JSON `status=ready`. Host `8080` still SearXNG; host `1080` still proxy.

## Residual: worker container vs host loopback proxy

`proxy-gateway` publishes **only** `127.0.0.1:1080`. Inside the `worker` container, `127.0.0.1:1080` is not that host bind. `urllib` honors `HTTP_PROXY`/`HTTPS_PROXY`, so the first GitHub token mint (M0.2 job) will fail closed until a container-reachable proxy path exists (connect `proxy-gateway` to the Trust CI network, publish proxy on a bridge IP, or `host-gateway` **plus** a bind that is not loopback-only).

**Do not fix that this slice.** Do not edit `compose.yaml`. Do not `network_mode: host`. Do not rebind `proxy-gateway`. Worker poll loop against PostgreSQL does not need GitHub. M0.1-complete is process up, not a Check Run.

DinD `docker-engine` has no `HTTP_PROXY` today. If `runner-loader` cannot reach `ghcr.io`, that is a recorded start failure, not a silent skip.

## Webhook (M0.2, blocked)

GitHub cannot POST to `127.0.0.1:18080`. Host has no `:443`. n8n-proxy Caddy has no Trust CI site and no public HTTPS hostname. `TRUST_CI_PUBLIC_BASE_URL` stays loopback HTTP until an operator HTTPS URL exists (`CommonSettings` requires HTTPS outside localhost).

Do **not** register `http://127.0.0.1:18080/webhooks/github`, a LAN IP, or `http://192.168.0.229:18080`. Record webhook **blocked**. M0.2 waits for app-stack Caddy (or another operator hostname) terminating TLS to `/webhooks/github`.

## Product-tree edits

Keep the “Fill after live M0.2/M0.3” lead. Never paste secrets.

| Path | Hook | Action |
| --- | --- | --- |
| `engineering/runbooks/trust-ci-activation-report.md` | not in `protected_paths` | Structured Write. Set App ID `4694114`, Installation ID `156003193`. Keep `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. Note worker/DinD started; webhook absent (no public HTTPS). `main` protected stays `false`. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | not protected | Tick the M0.1 compose worker/loader line actually completed. Rewrite “IDs UNKNOWN / worker not started”. Leave M0.2 webhook / Check Run / `branch-protect` unchecked. |
| `decisions.md` | protected + control plane | Exact `protected-path-write` grant, then structured Write. Three sentences: user IDs without PEM read; worker+DinD started; webhook deferred until public HTTPS. |
| `README.md` | protected | **Do not edit.** |
| `trust-ci/env/worker.env` | gitignored secret | `/tmp` script only. Never stage. |

## Grants

User explicitly delegated this compose-up. Old grants belong to other `change_id`s / fingerprints / TTLs — **do not reuse**. Mint **after** the gitignored ID patch (ignored files must not move the tracked fingerprint) and **before** compose-up. A later product-tree edit invalidates the grant; do not compose-up on a stale grant if the tree changed.

```bash
python3 scripts/grok_approve.py production --action external-write \
  --resource 'docker compose --project-name adaptive-trust-ci' \
  --reason 'M0.1-complete: docker-engine runner-loader worker; keep api/postgres' --ttl 30
python3 scripts/grok_approve.py external-write --action external-write \
  --resource 'docker compose --project-name adaptive-trust-ci' \
  --reason 'M0.1-complete: docker-engine runner-loader worker; keep api/postgres' --ttl 30
```

If `decisions.md` is edited, mint a separate `protected-path-write` for that file **after** compose-up (tree may still match until the first product write). No `docker-push`, no `pull-request-merge`, no wildcard, no `gh api` webhook create.

## Role split to preserve

- API: webhook HMAC + trust-store **public** keys. No App ID/PEM/signing key. Do not restart API to pick up worker IDs.
- Worker env: App ID, installation ID, PEM path, CI signing key path, `HTTP_PROXY`. Worker container on; PEM live-mounted but unread by agents.
- Runner: no token, no key, `network=none` (unchanged).
- Human approval private key: none on host.

## Observability and acceptance

- Compose project name `adaptive-trust-ci`.
- Services: `postgres` + `api` still healthy; `docker-engine` healthy; `runner-loader` completed 0; `worker` running.
- `GET http://127.0.0.1:18080/health/ready` → 200.
- worker.env untracked; IDs set; `git status` does not stage it.
- Activation-report App ID / Installation ID filled; webhook recorded blocked.
- GitHub: no write APIs. Optional read-only confirm hooks still empty / `main` protection still 404.
- No `.github/workflows/` added. `test_m0_invariants` remains green.

## Tests / verification

No production Python change is required. Gitignored host files alone are a no-op for `grok_verify`. Activation-report / M0 plan / `decisions.md` **are** product files → run `python3 scripts/grok_verify.py --mode pr` and route reviews (`code_reviewer`, `test_reviewer`). Keep `python3 -m unittest trust-ci.tests.test_m0_invariants` green. Do not add tests that require compose-up inside unittest. Do not assert “main is unprotected” in a way that fights M0.3.

## Rollback

```bash
docker compose --project-name adaptive-trust-ci stop worker docker-engine
```

Leave `api`/`postgres` running. `runner-loader` is already a oneshot. Prefer `stop` over `down --volumes`. Do not delete `adaptive-trust-ci_trust-ci-postgres` or `adaptive-trust-ci_trust-ci-docker-data`. Reverting worker.env IDs to placeholders is optional and must use the same `/tmp` script pattern.

## Implementer sequence

1. Read this ruling + repo_explorer + task_analyst + docs_researcher. Do not read secrets.
2. `/tmp` script: set App ID `4694114` and installation ID `156003193` in gitignored worker.env; preserve proxy and DSN; print operator-safe status; delete the script.
3. Mint compose grants on the then-current fingerprint.
4. `docker compose --project-name adaptive-trust-ci up -d docker-engine runner-loader worker` from the compose directory (or `/tmp` wrapper if argv is denied).
5. Prove `ps` + `/health/ready` without dumping env.
6. Product edits: activation-report IDs + webhook-blocked note; M0.1 checkboxes; `decisions.md` with a fresh protected-path grant.
7. Verify/reviews because the product tree changed.
8. Stop. No webhook, no branch-protect, no PR #5 merge, no PEM read, no GitHub Actions.
