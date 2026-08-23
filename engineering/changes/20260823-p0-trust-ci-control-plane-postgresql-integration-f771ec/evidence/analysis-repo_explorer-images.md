# Repo explorer — images / compose / supply-chain / host ops (handoff step 3)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `d2ba49e0570d` (`allowed_agents` include `repo_explorer`; write owner is `general_implementer`)  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane` (tracks origin)  
Package status: `ready` after docs/K16/toolchain resume  
Inspected: 2026-08-23. Read-only. No `.env` contents, no `*.pem` contents, no image vulnerability scan, no stop, no push, no merge, no deploy.

This answers: what is the actual next implementable product/ops slice on this tree after the docs resume.

Do **not** commit `engineering/changes/20260817-user-query-вычисти-*`. Do **not** `git push origin main`. Do **not** write measured image IDs into tracked `*.example` files.

---

## 0. Tree / dirty-state facts that bound the next slice

Docs/K16/toolchain resume is already in the working tree (uncommitted). `tasks.md` still has:

```text
[ ] Build and pin immutable images and holdout digest (operational; local build-without-push only after docs verify; no invented digests in git).
[ ] Create/install GitHub App (worker-only key, API-only webhook secret).
[ ] Deploy isolated API/worker/postgres/holdout/TLS intake.
[ ] Prove webhook → App-owned check on PR #2.
[ ] Apply app-bound branch protection only after that check exists.
[ ] Commit, update draft PR #2, record independent reviews.
```

Dirty product files (keep; do not revert): `README.md`, `QUICKSTART.md`, `trust-ci/README.md`, `decisions.md`, `mistakes.md`, `tests/test_structure.py`, `tests/test_toolchain.py`, `.grok-stack/config/toolchain.json`, `engineering/runbooks/trust-ci-rollout.md`, plus this change package `state.json` / `tasks.md`.

Untracked leftover: `engineering/changes/20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2/` — **do not commit**.

No filled `trust-ci/.env` or `trust-ci/env/*.env` exists. No `trust-ci/runtime/policy.json` or `trust-store.json`. A gitignored file `trust-ci/runtime/github-app-private-key.pem` exists (mode `0600`, 1675 bytes). **Do not read, copy, or commit it.**

---

## 1. compose.yaml vs compose.build.yaml vs compose.test.yaml

Paths:

- `/home/pall/grok-projects/adaptive-grok-build-pro/trust-ci/compose.yaml`
- `/home/pall/grok-projects/adaptive-grok-build-pro/trust-ci/compose.build.yaml`
- `/home/pall/grok-projects/adaptive-grok-build-pro/trust-ci/compose.test.yaml`
- interpolation template: `/home/pall/grok-projects/adaptive-grok-build-pro/trust-ci/.env.example`

`tests/test_ops.py::test_production_compose_uses_prebuilt_images_and_isolated_dind` locks: production compose has **no** `build:` and requires `TRUST_CI_{POSTGRES,API,WORKER,DIND}_IMAGE:?`.

### 1.1 Required interpolation vars (`:?` fails closed if unset)

Any parse of `compose.yaml` (including `docker compose -f compose.yaml -f compose.build.yaml … build`) interpolates **all** services, so these are required even when only building:

| Variable | File | Used by |
| --- | --- | --- |
| `TRUST_CI_POSTGRES_IMAGE` | `compose.yaml`, `compose.test.yaml` | `postgres` / `postgres-test` |
| `TRUST_CI_API_IMAGE` | `compose.yaml` | `migrate`, `api` **image name / tag** |
| `TRUST_CI_WORKER_IMAGE` | `compose.yaml` | `worker`, `runner-loader` **image name / tag** |
| `TRUST_CI_DIND_IMAGE` | `compose.yaml` | `docker-engine` |
| `TRUST_CI_RUNNER_IMAGE` | `compose.yaml` | `worker` and `runner-loader` env; **not** the build tag |
| `TRUST_CI_HOLDOUT_SOURCE_PATH` | `compose.yaml` | bind-mount into `docker-engine` and `worker` |
| `TRUST_CI_PYTHON_BASE_IMAGE` | `compose.build.yaml`, `compose.test.yaml` | `build.args.PYTHON_BASE_IMAGE` |

Optional with defaults:

| Variable | Default | Where |
| --- | --- | --- |
| `TRUST_CI_RUNNER_BUILD_TAG` | `adaptive-trust-ci-runner:2.1.0` | **only** `compose.build.yaml` `runner-image.image` |
| `TRUST_CI_TEST_BUILD_TAG` | `adaptive-trust-ci-test:2.1.0` | `compose.test.yaml` `postgres-integration.image` |

There is **no** `TRUST_CI_API_BUILD_TAG` / `TRUST_CI_WORKER_BUILD_TAG`.

Runtime `env_file` paths (`./env/postgres.env`, `./env/common.env`, `./env/api.env`, `./env/worker.env`, `./env/migration.env`) are required to **start** those services. They are currently missing. They are not required to reason about tags. `docker compose up` without them fails; do not create tracked copies.

### 1.2 Tags `compose.build.yaml` actually sets

Exact override file:

- `migrate`: `build` from `Dockerfile.api` only. **No `image:`.** Merged tag comes from `compose.yaml` → `${TRUST_CI_API_IMAGE:?…}`.
- `api`: `build` from `Dockerfile.api` only. **No `image:`.** Merged tag → `${TRUST_CI_API_IMAGE:?…}`.
- `worker`: `build` from `Dockerfile.worker` only. **No `image:`.** Merged tag → `${TRUST_CI_WORKER_IMAGE:?…}`.
- `runner-image`: `profiles: ["build"]`, `build` from `runner.Dockerfile`, **`image: ${TRUST_CI_RUNNER_BUILD_TAG:-adaptive-trust-ci-runner:2.1.0}`**. This is the only service whose tag is set in the override. It is **not** `TRUST_CI_RUNNER_IMAGE`.

Documented inspect command (already in `QUICKSTART.md`, `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`):

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

Inspect **`$TRUST_CI_*_IMAGE`**, not `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0`, unless those strings were exported as `TRUST_CI_API_IMAGE` / `TRUST_CI_WORKER_IMAGE`. `compose.build.yaml` does not assign those names.

`--profile build` is required to include `runner-image`. A two-file `build` without that profile builds `migrate`/`api`/`worker` only.

### 1.3 Can local `docker compose -f compose.yaml -f compose.build.yaml --profile build build` succeed without a registry?

**Build of artifacts: yes, if interpolation uses pullable-or-local names, not `REPLACE_WITH_*`.** `docker compose build` does not `--push`. `trust-ci/scripts/supply-chain-release.sh` is the path that pushes.

Constraints:

1. Copying `.env.example` verbatim cannot work. Values like `python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST` are not a 64-hex digest. `FROM` / `docker pull` of that reference fails.
2. Host already has local bases (no Hub pull needed if these names are used):
   - `python:3.12-slim-bookworm` `sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134`
   - `postgres:17.6-bookworm` `sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`
   - `docker:29-dind-rootless` `sha256:8a213afdd096a44dff403aaf8eb58b7a96a63113f18a4b094b98b7d0ed7d948b`
3. Dockerfiles still run `apt-get` and `pip install`. That needs Debian/PyPI (or a warm build cache), **not** an image registry for the Trust CI artifacts.
4. For tagging, set local **name:tag** values, e.g. `TRUST_CI_API_IMAGE=adaptive-trust-ci-api:2.1.0` and `TRUST_CI_WORKER_IMAGE=adaptive-trust-ci-worker:2.1.0`. A merged `image: registry.example.com/…@sha256:REPLACE_WITH_*` is not a valid local tag.
5. `TRUST_CI_HOLDOUT_SOURCE_PATH` must be an existing absolute directory even for a build parse of `compose.yaml` (compose interpolates the bind source). Do not invent a tracked holdout inside git.

Host already has previously built local images (created 2026-08-23, before the uncommitted docs README edit):

| RepoTags | Id (also local RepoDigest hex) | Created |
| --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0`, `:latest` | `sha256:9b957043dc6ee6fc152be5e50d4440f08a34e2ecb4a466ca66b4dc3887f2de8f` | 18:46:13Z |
| `adaptive-trust-ci-worker:2.1.0`, `:latest` | `sha256:ef58751c8ae5bf2548c56981c245889748ff246a78af57a14f3266d70b2dd9b0` | 18:50:11Z |
| `adaptive-trust-ci-runner:2.1.0` | `sha256:8ceb98cdb78a74d942418c738509b107a452d2be386469c12b030e53774ed5ac` | 18:48:20Z |
| `adaptive-trust-ci-test:2.1.0` | `sha256:597d83ff9e6a7a8337b6aaf2db6d54b08bf2c957089731b40974b914592abd2d` | 17:56:14Z |

On Docker Engine **29.7.2**, `RepoDigests` is **not** empty for these local images. It is the local name `@sha256:<same as Id>`, e.g. `adaptive-trust-ci-api@sha256:9b957043dc6e…`. That is **not** a registry.example.com digest and must **not** be committed as a production pin. `docker pull adaptive-trust-ci-api@sha256:…` still talks to Docker Hub.

`runner-loader` in `compose.yaml` does `docker pull "$TRUST_CI_RUNNER_IMAGE"` then asserts `RepoDigests[0] == TRUST_CI_RUNNER_IMAGE` **inside DinD** (`DOCKER_HOST=tcp://docker-engine:2375`). Host-local images are invisible to that daemon. Local build-without-push therefore **cannot** satisfy `runner-loader` without a registry or a `docker load` into DinD (no in-tree load path). QUICKSTART already splits: `up postgres migrate api worker` for API readiness; runner jobs need `docker-engine` + `runner-loader` / systemd.

`compose.test.yaml` service name is **`postgres-integration`**, image default `adaptive-trust-ci-test:2.1.0`. Makefile target `trust-ci-postgres-test` uses `--exit-code-from postgres-integration`. Live 8/8 is already recorded in `tasks.md`.

---

## 2. supply-chain-release.sh / verify-supply-chain.sh / Makefile

### 2.1 `trust-ci/scripts/supply-chain-release.sh`

Usage: exactly `./trust-ci/scripts/supply-chain-release.sh --confirm-push` (exit 64 otherwise).

PATH tools required: `docker`, `python3`, `trivy`, `syft`, `cosign`, `sha256sum`, `git`. It does **not** `command -v buildx`; it runs `docker buildx build`.

Required env:

- `TRUST_CI_PYTHON_BASE_IMAGE` — must match `@sha256:[0-9a-f]{64}` (stricter than compose.build)
- `TRUST_CI_API_REPOSITORY` / `TRUST_CI_WORKER_REPOSITORY` / `TRUST_CI_RUNNER_REPOSITORY` — registry repos **without** tag/digest
- `TRUST_CI_RELEASE_VERSION`
- `TRUST_CI_POLICY_TEMPLATE`
- `TRUST_CI_SUPPLY_CHAIN_DIR`
- `COSIGN_PRIVATE_KEY` — human-controlled cosign key path

Behavior: `docker buildx build … --push --sbom=true --provenance=mode=max`, then `trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed`, `syft … cyclonedx-json`, `cosign sign`, rewrite `sandbox.image` in a **new** `policy.json` under the output dir, `sha256sum` + `cosign sign-blob` of `supply-chain.manifest.json`.

This is **not** the local build-without-push slice. It always pushes. Cosign is **absent** on this host. Do not run it. Do not point it at a human approval key.

### 2.2 `trust-ci/scripts/verify-supply-chain.sh`

PATH tools: `docker`, `python3`, `cosign`, `sha256sum`.

Required env: `TRUST_CI_SUPPLY_CHAIN_DIR`, `COSIGN_PUBLIC_KEY`. Optional: `TRUST_CI_COMPOSE_ENV_FILE` (default `trust-ci/.env`), `TRUST_CI_DEPLOY_POLICY_PATH` (default `trust-ci/runtime/policy.json`).

Checks signed manifest, matching deployed policy bytes, and `TRUST_CI_{API,WORKER,RUNNER}_IMAGE` in compose env **equal** to `images.{api,worker,runner}` (`name@sha256:64hex`). Then `cosign verify` + **`docker pull`** of each image.

`trust-ci/systemd/adaptive-trust-ci-compose.service` `ExecStartPre=` this script; `ExecStart=` `docker compose up -d --wait` of `postgres migrate api docker-engine runner-loader worker`. No `--build`. Cannot start until a signed supply-chain directory exists.

### 2.3 Makefile (`/home/pall/grok-projects/adaptive-grok-build-pro/Makefile`)

Image/holdout-related targets:

| Target | Command |
| --- | --- |
| `trust-ci-compose` | `docker compose -f trust-ci/compose.yaml config` |
| `docker-compose-build-config` | `docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config` (not in `.PHONY`) |
| `trust-ci-postgres-test` | `compose.test.yaml up --build --abort-on-container-exit --exit-code-from postgres-integration` + `down -v` trap |
| `trust-ci-holdout-digest` | `PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli holdout-digest --path trust-ci/holdout.example` |
| `trust-ci-test` / `trust-ci-compile` | unit tests / compileall |

**No** Makefile target builds, pins, pushes, or verifies supply-chain images. `make trust-ci-compose` / `make docker-compose-build-config` fail until the `:?` vars are set (currently no `.env`).

Holdout CLI also: `adaptive-trust-ci holdout-digest --path <absolute reviewed dir>`. Example policy digest is locked to `trust-ci/holdout.example` by `tests/test_ops.py::test_example_holdout_digest_matches_example_bundle`. Deployed holdout is **outside** the checkout (`TRUST_CI_HOLDOUT_SOURCE_PATH`).

---

## 3. env examples and `config/policy.example.json` — keep `REPLACE_WITH_*` in git

### 3.1 `trust-ci/.env.example` (compose interpolation only)

Must stay as placeholders in git:

- `TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST`
- `TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:REPLACE_WITH_POSTGRES_DIGEST`
- `TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:REPLACE_WITH_DIND_DIGEST`
- `TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST`
- `TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST`
- `TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST`

`TRUST_CI_RUNNER_BUILD_TAG` / `TRUST_CI_TEST_BUILD_TAG` / `TRUST_CI_HOLDOUT_SOURCE_PATH=/srv/adaptive-trust-ci/holdout` are examples, not secrets.

### 3.2 `trust-ci/env/*.example`

| File | Placeholders that must remain in git |
| --- | --- |
| `api.env.example` | `REPLACE_WITH_URLENCODED_API_PASSWORD`, `REPLACE_WITH_LONG_RANDOM_SECRET`, `REPLACE_WITH_LONG_RANDOM_READ_TOKEN` |
| `worker.env.example` | `REPLACE_WITH_URLENCODED_WORKER_PASSWORD`, `REPLACE_WITH_APP_ID`, `REPLACE_WITH_INSTALLATION_ID` |
| `postgres.env.example` | `REPLACE_WITH_LONG_RANDOM_{ADMIN,API,WORKER,MIGRATOR,BACKUP}_PASSWORD` |
| `migration.env.example` | `REPLACE_WITH_URLENCODED_MIGRATOR_PASSWORD` |
| `backup.env.example` | `REPLACE_WITH_URLENCODED_BACKUP_PASSWORD` |
| `common.env.example` | no `REPLACE_WITH_*` (`https://ci.example.com`) |
| `supply-chain.env.example` | host paths only; no digest placeholders |

Filled copies are gitignored (`trust-ci/env/*.env`, `.env`, `trust-ci/runtime/*`).

### 3.3 `trust-ci/config/policy.example.json`

Must stay:

```text
sandbox.image = adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST
```

`tests/test_structure.py::test_trust_ci_policy_uses_immutable_sandbox_and_external_status` allows **either** that exact suffix **or** a real `sha256:<64-hex>` / `name@sha256:<64-hex>`. Do not take that as permission to commit a local daemon ID.

`Policy.load` / `SandboxSpec.from_dict` (`trust-ci/src/adaptive_trust_ci/policy.py`) **reject** `REPLACE_WITH_*` (not 64 hex). Deployed `runtime/policy.json` must be a gitignored copy with a measured digest. `Worker.build()` requires `TRUST_CI_RUNNER_IMAGE == policy.sandbox.image`.

Holdout digest in the example (`b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`) is the digest of `trust-ci/holdout.example` and **is** allowed in git. A reviewed external bundle may differ; that digest belongs only in untracked `runtime/policy.json`.

### 3.4 `trust-ci/config/trust-store.example.json`

Keep `REPLACE_WITH_KEY_ID_FROM_KEYGEN`, `REPLACE_WITH_HUMAN_IDENTITY`, `REPLACE_WITH_MULTILINE_ED25519_PUBLIC_KEY_PEM`. `/health/ready` is 503 until an **active** human public key exists. Private approval keys stay off this workspace.

---

## 4. Host toolchain (`command -v` + `toolchain.json`; no image scans)

`.grok-stack/config/toolchain.json` (dirty vs HEAD) catalogs optional `required: false` tools:

| id | built/fallback | host `command -v` | notes |
| --- | --- | --- | --- |
| `docker` | built `29.7.2` | **PRESENT** `/usr/bin/docker` | client=server **29.7.2**; compose plugin **v5.5.0** at `/usr/libexec/docker/cli-plugins/docker-compose` |
| (no standalone `docker-compose` id) | — | **ABSENT** `docker-compose` | use `docker compose` |
| (no `buildx` tool id) | — | **ABSENT** `buildx` on PATH | `docker buildx version` = **v0.36.1**; plugin `/usr/libexec/docker/cli-plugins/docker-buildx` |
| `syft` | built `1.51.0` | **PRESENT** `/usr/local/bin/syft` **1.51.0** | |
| `trivy` | built `0.74.0` | **PRESENT** `/usr/local/bin/trivy` **0.74.0** | not invoked |
| `cosign` | min 2.0 / fallback 2.4 / linux pin v2.4.3 | **ABSENT** | blocks `supply-chain-release.sh` and `verify-supply-chain.sh` |

`tests/test_toolchain.py` asserts those four ids exist and are `required: false`. Missing cosign does **not** fail `grok_doctor`. Local compose **build** needs docker + compose plugin + buildx plugin (all present). It does not need syft/trivy/cosign.

`gh` is present (`/snap/bin/gh`) and logged in as GitHub user `Dimkox` with scopes `gist`, `read:org`, `repo`, `workflow`. That is **not** a GitHub App installation token and is **not** `TRUST_CI_GITHUB_ADMIN_TOKEN` unless a later exact delegated grant says so. Do not create `.github/workflows/**`.

---

## 5. Port 8080 occupancy (services were not stopped)

`ss` shows `LISTEN 127.0.0.1:8080`.

`docker ps`: container `searxng-instance` (`searxng/searxng:2026.6.11-4dd0bf486`) publishes `127.0.0.1:8080->8080/tcp`.

`GET http://127.0.0.1:8080/health/live` and `/health/ready` return **HTTP 404** SearXNG HTML (`searxng/2026.6.11+4dd0bf486`), not Trust CI.

`trust-ci/compose.yaml` hardcodes:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

No env override. A live `docker compose up` of `api` **would collide** with SearXNG. Do not stop SearXNG. `engineering/changes/…/architecture.md` already rules: deploy on a free loopback port + HTTPS reverse proxy, not by stealing 8080.

No Trust CI containers are running. Other live stacks (n8n, postgres:16, mongo, nginx 8083, etc.) are unrelated; do not stop them.

---

## 6. GitHub App / webhook / branch-protect paths that cannot run without secrets

In-tree code is present; live activation is not.

| Path | Secret / external input | Without it |
| --- | --- | --- |
| `GitHubAppAuth.installation_token` in `trust-ci/src/adaptive_trust_ci/github_app.py` | RSA private key bytes + positive `app_id` / `installation_id`; POST `https://api.github.com/app/installations/{id}/access_tokens` | JWT/token fail. Worker cannot publish Checks. |
| `Worker.build` in `trust-ci/src/adaptive_trust_ci/worker.py` | `WorkerSettings`: `TRUST_CI_GITHUB_APP_ID`, `TRUST_CI_GITHUB_INSTALLATION_ID`, `TRUST_CI_GITHUB_APP_PRIVATE_KEY_PATH`, `TRUST_CI_SIGNING_KEY_PATH`, immutable `TRUST_CI_RUNNER_IMAGE` matching policy | Process will not start. |
| `GitHubClient.ensure_check_run` / `complete_check_run` in `trust-ci/src/adaptive_trust_ci/github.py` | installation token from App auth | Cannot create `adaptive-trust-ci/verified@<policy-sha12>`. |
| Workspace fetch (`workspace.py`, token via `github_token_provider`) | same installation token (`contents:read`) | Cannot checkout the PR SHA. |
| `POST /webhooks/github` in `trust-ci/src/adaptive_trust_ci/api.py` | `TRUST_CI_WEBHOOK_SECRET` HMAC (`X-Hub-Signature-256`) | 4xx; no enqueue. API still has **no** `GitHubClient` / `GitHubAppAuth` (holdout `validate.py` forbids it). |
| `adaptive-trust-ci branch-protect` in `cli.py` | `TRUST_CI_GITHUB_ADMIN_TOKEN` **and** App ID **and** deployed `policy.json`; PUT `/repos/{repo}/branches/{branch}/protection` | `SystemExit`: admin token required. |
| `adaptive-trust-ci doctor` (worker role) | readable App PEM to `generate_app_jwt` | `github-app-key` check fails. |
| systemd compose | `COSIGN_PUBLIC_KEY` + signed supply-chain dir + filled `.env` | `ExecStartPre=verify-supply-chain.sh` cannot pass. |
| GitHub App **create/install** | GitHub UI / App manifest; not implemented in this repo | `gh` `repo` scope cannot mint an App ID. Do not invent `REPLACE_WITH_APP_ID`. |

Draft PRs **do enqueue** (`test_draft_pull_request_is_enqueued`; `parse_pull_request_event` ignores `draft`). First live proof should still be a disposable docs PR, not branch-protect on draft PR #2.

API-only vs worker-only split: `compose.yaml` mounts `github-app-private-key.pem` **only** under `worker`. `env/api.env.example` has webhook secret, not App ID.

---

## 7. What must NOT be committed

- `engineering/changes/20260817-user-query-вычисти-*`
- `trust-ci/.env`, `trust-ci/env/*.env` (non-example)
- `trust-ci/runtime/**` except `.gitkeep` (includes `github-app-private-key.pem`, future `policy.json`, signing keys)
- Any `*.pem`, `*.key`, webhook secrets, App ID/install filled as if they were examples
- Local image IDs (`9b957043dc6e…`, `ef58751c8ae5…`, `8ceb98cdb78a…`, python/postgres/dind Ids) written into tracked `.env.example` or `policy.example.json`
- Invented `registry.example.com/…@sha256:<random 64 hex>`
- `compose.override.yaml` if created for port remap (Compose auto-loads it; **not** gitignored today)
- `.github/workflows/**`
- Cosign private key, `TRUST_CI_GITHUB_ADMIN_TOKEN`, human Ed25519 **private** key
- Direct push to `main`

Measured pins belong in **untracked** deploy files and in this change-package evidence, labeled as **local daemon IDs**, not registry attestations.

---

## Recommended next slice

The next coherent slice is **handoff step 3 only: local image build-without-push + measure + untracked pin**, not GitHub App, not `compose up`, not branch-protect, not commit of PR #2. On this host, docker/compose/buildx/syft/trivy and local `python:3.12-slim-bookworm` / `postgres:17.6-bookworm` / `docker:29-dind-rootless` plus `adaptive-trust-ci-{api,worker,runner,test}:2.1.0` already exist; cosign does not, so `supply-chain-release.sh` / `verify-supply-chain.sh` / systemd start are out of scope. The write owner should export local tags (not `REPLACE_WITH_*`) plus `TRUST_CI_PYTHON_BASE_IMAGE` and an absolute holdout path, run `docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image` (rebuild if they want current `trust-ci/` sources in the image; existing images predate the dirty README), inspect `$TRUST_CI_{API,WORKER,RUNNER}_IMAGE` for `.Id` and `RepoDigests[0]`, run `make trust-ci-holdout-digest` against a reviewed external directory (not as a git pin of a new digest), and copy those **measured** values only into gitignored `trust-ci/.env` and `trust-ci/runtime/policy.json`. Leave every `REPLACE_WITH_*` in tracked examples. Do not `docker compose up` (SearXNG owns `127.0.0.1:8080`; `runner-loader` needs a registry or DinD load). Do not stop SearXNG. Record the measured IDs in change-package evidence as local-only.

**Files the write owner (`general_implementer`) may touch**

- Untracked operator copies only: `trust-ci/.env`, `trust-ci/env/*.env`, `trust-ci/runtime/policy.json` (from `config/policy.example.json`), optional untracked extra compose file **if** kept out of git
- Evidence / package: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec/evidence/*`, `tasks.md`
- **Do not** edit `trust-ci/.env.example`, `trust-ci/env/*.example`, `trust-ci/config/policy.example.json`, `trust-ci/config/trust-store.example.json` to insert local IDs
- **Do not** edit `trust-ci/compose.yaml` port in this slice (that is deploy / 8080 collision, step 5)
- **Do not** add Makefile push/release targets or install cosign unless a later supply-chain slice is explicitly ordered
- **Do not** create/install the GitHub App, register a webhook, or run `branch-protect`
- **Do not** commit the leftover `20260817-user-query-вычисти-*` package or any `trust-ci/runtime/*.pem`
- Product docs already dirty from the docs resume may stay as-is; step 9 is the commit of that tree after external evidence exists
