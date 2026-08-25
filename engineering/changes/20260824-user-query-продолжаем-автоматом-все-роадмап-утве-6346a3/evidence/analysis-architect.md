# Architect ruling — M0.1 listener on `claw`

Route `6346a398114f`. Change `20260824-user-query-продолжаем-автоматом-все-роадмап-утве-6346a3`. Write owner: `general_implementer`. This agent does not compose-up, push, merge, register webhooks, branch-protect, or read `.env` / PEM / JWT.

## Ruling

**This slice is M0.1 only: host-owned untracked runtime + `postgres` + `migrate` + `api` on compose project `adaptive-trust-ci`, published at `127.0.0.1:18080`.** Do not start `worker`, `docker-engine`, or `runner-loader`. Do not start M0.2/M0.3/M2. Do not merge or ready PR #5. Do not add GitHub Actions.

User-approved scope outranks the M0 plan's `up … worker` line and outranks `analysis-task_analyst.md` (which wanted the worker and a STOP if no human public key). Installation ID cannot be obtained without PEM/JWT; the PEM filename exists under gitignored `trust-ci/runtime/` and **must not be opened**. Therefore App ID and installation ID stay `UNKNOWN` and the worker stays off.

Proceed with API+PostgreSQL. `/health/ready` is the listener proof on loopback HTTP. TLS, webhook, Check Run, and `branch-protect` remain later slices.

## Why worker is deferred

`WorkerSettings` requires positive integers `TRUST_CI_GITHUB_APP_ID` and `TRUST_CI_GITHUB_INSTALLATION_ID` plus the App RSA path. `GitHubAppAuth` mints installation tokens with a JWT from that PEM. The M0 spec already recorded that the agent `gh` token cannot read installation ID (401/403). Reading `github-app-private-key.pem` to mint a JWT is forbidden this slice. Missing either ID → **api+postgres only**.

Starting the worker would also pull privileged rootless DinD (`docker-engine`) and `runner-loader`. That is M0.1-complete topology, not this minimum listener.

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User binding | `postgres+migrate+api` at minimum; worker only if App IDs without PEM/JWT | **Wins.** |
| M0 plan / README / docs_researcher | `docker compose up -d postgres migrate api worker` | Full topology is the *later* M0.1 completion, not this turn. Leave the worker checkbox unchecked. |
| task_analyst | `/health/ready` 200; STOP if no human public key; start worker | Overruled on worker and STOP. Ready is still the target *if* the API can start; see trust-store below. |
| M0 plan leftover sentence | “host-name correction … is not M0.1 execution (no compose-up)” | Stale M0.0 text. This turn **is** compose-up on `claw`. Implementer rewrites that sentence when ticking M0.1 boxes. |

## Non-goals (forbidden this slice)

- `docker compose up` without an explicit service list (would start worker+DinD).
- Publishing host `8080` (SearXNG), `1080` (proxy-gateway), `443`, or any Postgres host port.
- Mutable tags (`:latest`). Local `adaptive-trust-ci-{api,worker}:latest` **differ** from the 2.1.0 ghcr RepoDigests; they are forbidden in `.env`.
- Registering `/webhooks/github`, `branch-protect`, disabling workflow `340420982`, forging `adaptive-trust-ci/verified@*`.
- Merging/readying PR #5; starting M2–M9; creating `factory/`; adding `.github/workflows/**`.
- Reading or printing PEM, JWT, webhook secret, DB passwords, human approval private keys, `glider.conf`.
- `git add -A` of `trust-ci/env/*.env` or `trust-ci/runtime/**`.
- VERSION/tag/release. README only if the implementer otherwise has to (this design does not require it).

## Current host facts (read-only; stack not started)

Hostname `claw`. No `trust-ci/.env`. Operator env files absent (examples only). Runtime filenames: `.gitkeep`, `github-app-private-key.pem` (0600; unread).

| Port | State | Rule |
| --- | --- | --- |
| `127.0.0.1:18080` | not listening | **Publish here.** |
| `127.0.0.1:8080` | SearXNG | Do not bind. |
| `127.0.0.1:1080` | proxy-gateway | Do not bind. Point later worker `HTTP_PROXY`/`HTTPS_PROXY` at `http://127.0.0.1:1080`. |
| `:443` | not listening | Do not bind. No TLS proxy this slice. |
| `:5432` | not published by compose | Keep it that way. |

`docker compose --project-name adaptive-trust-ci ps` currently fails interpolation because host image/holdout vars are unset. That is expected. Architect did **not** `up`.

## Image pins (immutable `name@sha256`; inspect RepoDigest, never `:latest`)

Put these exact strings in untracked `trust-ci/.env`. Do not use image `.Id` (no registry prefix) and do not use the un-namespaced RepoDigest as the only form for ghcr images.

| Variable | Pin |
| --- | --- |
| `TRUST_CI_API_IMAGE` | `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` |
| `TRUST_CI_WORKER_IMAGE` | `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` |
| `TRUST_CI_RUNNER_IMAGE` | `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` |
| `TRUST_CI_POSTGRES_IMAGE` | `postgres:17.6-bookworm@sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3` |
| `TRUST_CI_DIND_IMAGE` | `docker:29-dind-rootless@sha256:8a213afdd096a44dff403aaf8eb58b7a96a63113f18a4b094b98b7d0ed7d948b` |

API/worker/runner pins match `build/adaptive-trust-ci-pin.env` and live ghcr RepoDigests. Postgres/DinD are Hub images already present on `claw`; do **not** substitute `postgres:16` / `postgres:16-alpine` also on disk.

Worker/DinD/runner values are required for **compose file interpolation** even when those services are not started. Setting them does not start DinD.

Also set `TRUST_CI_API_HOST_PORT=18080` and `TRUST_CI_HOLDOUT_SOURCE_PATH` (absolute host path outside the checkout).

## Untracked host material

Gitignore already covers `trust-ci/.env`, `trust-ci/env/*.env`, `trust-ci/runtime/*`, `*.pem`. Create only those; never commit them.

Compose `env_file` paths are relative to `trust-ci/compose.yaml`, so operator env files must live at `trust-ci/env/{postgres,common,migration,api,worker}.env`. `backup.env` is not in `compose.yaml`; skip it this slice.

### Control-plane hook constraint

`trust-ci/**` is a control-plane path. Bash `cp`/`mkdir`/`chmod` whose command string contains `trust-ci` is blocked even with a path grant. `Read`/`Write` of `trust-ci/env/*.env` and `trust-ci/runtime/**` is secret/protected.

**Do not paste secrets into tool payloads or chat.** Implementer runs an **out-of-repo** bootstrap script (e.g. `/tmp/m01-claw-bootstrap.py`) whose argv does not mention `trust-ci`. The script writes gitignored files, sets `0600` on env and private keys, and prints only operator-safe status (paths exist yes/no, ports, `name@sha256`, holdout digest, App IDs `UNKNOWN`). Delete the script after use. Do not `cat` the PEM or `.env`.

### Files the script must materialize

1. `trust-ci/.env` — interpolation pins above + `TRUST_CI_API_HOST_PORT=18080` + holdout source path.
2. `trust-ci/env/postgres.env` — long random passwords for admin/api/worker/migrator/backup; never print.
3. `trust-ci/env/common.env` — `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080` (settings allow loopback HTTP; HTTPS is not this slice), policy path, kill-switch path.
4. `trust-ci/env/migration.env` — migrator DSN using the migrator password; `TRUST_CI_ROLE=migration`.
5. `trust-ci/env/api.env` — api DSN, **generated** `TRUST_CI_WEBHOOK_SECRET`, `TRUST_CI_READ_TOKEN`, trust-store path, `TRUST_CI_ROLE=api`. **No** App ID/PEM/signing key.
6. `trust-ci/env/worker.env` — copied from example with `HTTP_PROXY=http://127.0.0.1:1080` and `HTTPS_PROXY=http://127.0.0.1:1080` and `NO_PROXY=postgres,127.0.0.1,localhost`. Leave App IDs as non-integer placeholders (`UNKNOWN`). File is prepared for a later worker start; **do not start worker**.
7. `trust-ci/runtime/policy.json` — copy of `config/policy.example.json` with:
   - `sandbox.image` = the runner `ghcr.io/dimkox/…@sha256:900c…` pin (example `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST` **will not parse**).
   - `holdout.path` remains `/etc/adaptive-trust-ci/holdout` (in-container).
   - `holdout.digest` = measured digest of the host holdout copy (example digest is valid only for an identical `holdout.example` tree).
8. `trust-ci/runtime/trust-store.json` — see trust-store ruling.
9. `trust-ci/runtime/trust-ci-signing-key.pem` + `.pub.pem` via `python3 -m adaptive_trust_ci keygen` (Ed25519 CI attestation key, **not** the GitHub App RSA and **not** a human approval key). `keygen` already refuses overwrite and `chmod 600`s the private file. Worker-only mount; API compose does not mount it.
10. `trust-ci/runtime/control/` empty dir for the kill-switch volume.
11. Host holdout directory **outside the checkout**, populated from `trust-ci/holdout.example/validate.py` (regular file, no symlinks). Measure digest with `python3 -m adaptive_trust_ci holdout-digest --path <abs>`. Suggested host path: `/opt/m0-holdout` (avoids accidental control-plane prefix in ad-hoc bash). Do not steal existing compose volumes/networks.

Do not overwrite `github-app-private-key.pem`. Do not read it.

Postgres init requires all four role passwords in `postgres.env` or the container fails closed.

## Trust-store ruling (API cannot start on the example file)

`ApiSettings` requires `TRUST_CI_WEBHOOK_SECRET`. `create_app` calls `Policy.load` and `TrustStore.load` at process start. `TrustStore.load` rejects placeholder PEMs. `/health/ready` additionally requires PostgreSQL ping and **≥1 active** trust-store public key.

`config/trust-store.example.json` cannot start the API. Human approval private keys must not be generated as the M0.2/M0.3 human key on this host.

**Bounded exception:** the bootstrap script may generate one Ed25519 pair solely to insert the **public** key + matching `key_id` into untracked `runtime/trust-store.json` (actor e.g. `claw-m01-bootstrap`, scopes `governance`/`database`/`production`, schema 2 dates covering now). **Immediately unlink the bootstrap private key** so no approval private key remains on `claw`. This key is not a human security-approval key; M0.2+ still requires a human-workstation key that replaces/revokes this bootstrap public key.

Record that exception in root `decisions.md` (three sentences). Do not log PEMs.

`Policy.load` does not verify holdout bytes at API start; `/health/ready` does not either. Still pin a real digest now so a later worker does not surprise.

## Compose-up (implementer only; after grant)

Working directory **must** be `trust-ci/` so `env_file: ./env/…` resolves.

```bash
docker compose -f compose.yaml --project-name adaptive-trust-ci up -d postgres migrate api
```

Equivalent from repo root: `docker compose -f trust-ci/compose.yaml --project-name adaptive-trust-ci up -d postgres migrate api` only if Compose still resolves `env_file` relative to the compose file (it does). Prefer `cd trust-ci`.

`-d` is required so the command returns. `depends_on`: postgres healthy → migrate completed → api. Do not add `worker`/`docker-engine`/`runner-loader`.

Proof (operator-safe):

```text
curl -fsS http://127.0.0.1:18080/health/ready
docker compose -f compose.yaml --project-name adaptive-trust-ci ps
```

Expect HTTP 200 JSON with `status=ready`, `policy_digest` hex, `status_publisher=worker-github-app`. In-container healthcheck stays `http://127.0.0.1:8080/health/ready`. Host `127.0.0.1:8080` must remain SearXNG. Host `127.0.0.1:1080` must remain the proxy.

If ready is 503, fix trust-store/postgres; do not start the worker as a workaround.

## Grants

User delegated compose-up on `claw` and protected-path for runbook/README if those product files are edited.

Hook fact: `docker compose` is **not** classified as `production_action` today. Mint the grant anyway as named operational evidence. Mint **after** untracked bootstrap (gitignored files should not move the tree fingerprint) and **before** compose-up. A later product-tree edit invalidates it; do not compose-up on a stale grant if the tree changed.

```bash
python3 scripts/grok_approve.py production --action external-write \
  --resource 'docker compose -f trust-ci/compose.yaml --project-name adaptive-trust-ci' \
  --reason 'M0.1 claw listener: postgres+migrate+api only' --ttl 30
python3 scripts/grok_approve.py external-write --action external-write \
  --resource 'docker compose -f trust-ci/compose.yaml --project-name adaptive-trust-ci' \
  --reason 'M0.1 claw listener: postgres+migrate+api only' --ttl 30
```

No `docker-push`, no `pull-request-merge`, no wildcard resources.

Product-tree writes:

| Path | Hook | Action |
| --- | --- | --- |
| `engineering/runbooks/trust-ci-activation-report.md` | not in `protected_paths` (only `publish-v*.md`) | Structured Write. Still mint protected-path if the implementer wants the user-named grant; not required by the hook. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | not protected | Structured Write. Tick only M0.1 boxes that this turn actually completed. Rewrite the stale “no compose-up” sentence. Leave worker/webhook/`branch-protect` unchecked. |
| `decisions.md` | protected + control plane | Exact `protected-path-write` grant for `decisions.md`, then structured Write. Bootstrap trust-store exception + worker deferred until App IDs exist without PEM. |
| `README.md` | protected | **Do not edit** this slice. |

Do not use `scripts/grok_protected_write.py` shell mutation; use structured Edit/Write after the grant. First successful tree mutation consumes the fingerprint-bound grant — batch or re-mint.

## Product-tree activation-report fields

Keep the “Fill after live M0.2/M0.3” lead, but fill **operator-safe listener facts** now. Never paste secrets.

| Field | M0.1 value |
| --- | --- |
| Report date | ISO date of compose-up |
| Dedicated CI host | `claw` (already) |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |
| Product base SHA | unchanged `48cb9737…` |
| GitHub App slug | `adaptive-trust-ci` |
| App ID / Installation ID | `UNKNOWN` |
| Policy digest / required check | fill digest from `/health/ready` if 200; check name stays `@UNKNOWN` until that digest is written |
| Disposable PR / Check Run / attestation | `UNKNOWN` (M0.2) |
| API/worker/runner images | the ghcr `name@sha256` pins above (worker image is pinned in env, service not started) |
| Holdout digest | measured 64-hex |
| `main` protected | `false` (M0.3 only) |
| Protection `app_id`, kill/backup drills, bootstrap-exception superseded | `UNKNOWN` |
| Secrets | stay `UNKNOWN`; do not add secret columns |

Optional one-line note under the table: published mapping `127.0.0.1:18080→container 8080`; worker/DinD not started; webhook absent.

## Role split to preserve while API-only

- API env: webhook secret + trust-store **public** keys. No App RSA mount (compose already does not mount it into `api`).
- Worker env file may exist on disk for later; worker container off, so PEM/signing key are not live-mounted this turn.
- CI signing private key exists on disk for later worker; API must not receive `TRUST_CI_SIGNING_KEY_PATH`.
- Human approval private key: none on host after bootstrap shred.

## Observability and acceptance

- Compose project name `adaptive-trust-ci`.
- `GET http://127.0.0.1:18080/health/ready` → 200.
- `GET http://127.0.0.1:18080/health/live` → live even if ready fails (debug only; ready is the gate).
- `ss`/`curl`: `8080` still SearXNG; `1080` still proxy; `18080` is Trust CI.
- GitHub: do not call write APIs. Optional read-only confirm hooks empty / `main` protection 404 — do not register anything.
- No `.github/workflows/` added. `test_m0_invariants` remains green.

## Tests / verification

No production code change is required. If only gitignored host files change, skip `grok_verify` (AGENTS.md no-op). If activation-report / M0 plan / `decisions.md` change, run `python3 scripts/grok_verify.py --mode pr` and the route reviews (`code_reviewer`, `test_reviewer`). Keep `python3 -m unittest trust-ci.tests.test_m0_invariants` green; do not assert “main is unprotected” in a way that fights M0.3.

Do not add tests that require compose-up inside unittest.

## Rollback

```bash
docker compose -f trust-ci/compose.yaml --project-name adaptive-trust-ci stop postgres migrate api
```

Prefer `stop` over `down --volumes`. Never `down --volumes` against other projects. Project-prefixed volume `adaptive-trust-ci_trust-ci-postgres` is this stack only; do not delete it unless discarding a failed first boot.

## Implementer sequence

1. Read this ruling + repo_explorer + task_analyst + docs_researcher. Do not read secrets.
2. Out-of-repo bootstrap of untracked env/policy/keys/holdout; shred bootstrap trust-store private key; never print secrets.
3. Mint compose grants on the then-current fingerprint.
4. `up -d postgres migrate api` with `-f trust-ci/compose.yaml --project-name adaptive-trust-ci`.
5. Prove `/health/ready` on `127.0.0.1:18080` without dumping env.
6. Product edits: activation-report operator-safe fields, M0.1 checkboxes, `decisions.md` exception. Protected-path grant for `decisions.md`.
7. Verify/reviews only if the product tree changed.
8. Stop. Webhook, worker, PR #5 merge, M2 are someone else's later slice.
