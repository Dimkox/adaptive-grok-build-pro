# Repo explorer: skip nested rootless DinD, use host Docker socket + host.docker.internal:1080

Route `3e61666b8de2`. Read-only map. No product edits.

## Intent

If `docker-engine` (privileged rootless DinD in `trust-ci/compose.yaml`) is dropped, `runner-loader` and `worker` must talk to the **host** Docker daemon (typically `unix:///var/run/docker.sock`) and worker outbound GitHub HTTP(S) must use `host.docker.internal:1080` instead of container-loopback `127.0.0.1:1080`.

`host.docker.internal` is **not** referenced anywhere in this tree today.

---

## 1. Files and assertions that fail if `docker-engine` is removed or `DOCKER_HOST` changes

| File | Current assertion / coupling |
|---|---|
| `trust-ci/compose.yaml` | Service `docker-engine` (`TRUST_CI_DIND_IMAGE`, `privileged: true`, TCP `0.0.0.0:2375` + unix `/run/user/1000/docker.sock` **inside** DinD). `runner-loader` and `worker` set `DOCKER_HOST: tcp://docker-engine:2375`. `runner-loader` `depends_on: docker-engine` `service_healthy`. `worker` `depends_on: runner-loader` `service_completed_successfully`. Volume `trust-ci-docker-data`. Holdout + workspaces bind/volume on DinD. |
| `trust-ci/tests/test_ops.py` `test_production_compose_uses_prebuilt_images_and_isolated_dind` | `TRUST_CI_DIND_IMAGE:?`; `'  docker-engine:'`; **`assertNotIn('/var/run/docker.sock', compose)`**; `privileged: true` on docker-engine slice; `trust-ci-docker-data:/home/rootless/.local/share/docker`; **`DOCKER_HOST: tcp://docker-engine:2375` in worker slice**; workspaces + holdout mounts on docker-engine. |
| `trust-ci/tests/test_database_roles.py` `test_compose_uses_role_specific_env_and_initialization` | Splits API block with `compose.split('  api:', 1)[1].split('  docker-engine:', 1)[0]`. Removing the service **breaks the split** even if env files stay. |
| `trust-ci/tests/test_supply_chain.py` `test_systemd_requires_supply_chain_verification_before_start` | `assertIn('docker-engine', service)` and `runner-loader` on systemd unit. |
| `trust-ci/tests/test_m0_invariants.py` | Does **not** name `docker-engine` / `DOCKER_HOST`. Still requires compose loopback publish. Unchanged by DinD skip unless compose port mapping changes. |
| `trust-ci/scripts/smoke.sh` | `grep -q 'docker-engine:'`; `grep -q 'DOCKER_HOST: tcp://docker-engine:2375'`; **exit 1 if rendered compose contains `/var/run/docker.sock`**. |
| `trust-ci/systemd/adaptive-trust-ci-compose.service` | `ExecStart` / `ExecReload`: `docker compose up ... postgres migrate api docker-engine runner-loader worker`. |
| `trust-ci/.env.example` | `TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:...` |
| `trust-ci/env/worker.env.example` | Comments: “Paths as seen by the dedicated **DinD daemon**.” `TRUST_CI_WORKSPACE_HOST_ROOT=/var/lib/adaptive-trust-ci/workspaces` (must match daemon-visible paths). |
| `QUICKSTART.md` | systemd starts `docker-engine` + `runner-loader`; short `up` of `postgres migrate api worker` for API-only. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Explicit `up -d docker-engine runner-loader worker`; records DinD unhealthy. |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Privileged DinD as residual accepted risk on `claw`. |
| `engineering/runbooks/trust-ci-activation-report.md` | Same DinD failure evidence. |
| `decisions.md` | DinD `rootlesskit` `operation not permitted`. |
| `trust-ci/src/adaptive_trust_ci/sandbox.py` | `_runtime_environment()` **allows** `DOCKER_HOST` (and `DOCKER_CONFIG`, `CONTAINER_HOST`) through to `docker` CLI. No hard-coded `tcp://docker-engine:2375`. Changing host via compose env is enough for the Python worker **if** the daemon sees the same bind paths. |
| `build/stage_m02.py` | Git-add helper for activation report / M0 plan / change `421a1d`. No compose topology. |

`test_m0_invariants.py` does not encode isolated DinD. The **hard fail set** is `test_ops.py`, `test_database_roles.py` (split token), `test_supply_chain.py` (systemd string), `smoke.sh`.

---

## 2. How `runner-loader` depends on `docker-engine` health

From `trust-ci/compose.yaml`:

1. `docker-engine` healthcheck: `docker -H tcp://127.0.0.1:2375 info` (30 retries × 5s).
2. `runner-loader` `depends_on.docker-engine.condition: service_healthy`.
3. Loader command (worker image): `docker pull "$TRUST_CI_RUNNER_IMAGE"` then `docker image inspect ... RepoDigests[0]` must **equal** the pin. `DOCKER_HOST=tcp://docker-engine:2375` so the pull lands **in DinD**, not on the host daemon.
4. `worker` waits for `runner-loader` `service_completed_successfully`.

If DinD never becomes healthy (current `claw` state: `rootlesskit: fork/exec /proc/self/exe: operation not permitted`), loader and worker stay `Created`.

A host-socket design must: drop `depends_on` on DinD; set `DOCKER_HOST` to unix socket or `unix:///var/run/docker.sock`; pull the runner image into the **host** engine; keep workspace/holdout paths as the **host** sees them (`TRUST_CI_WORKSPACE_HOST_ROOT` / `TRUST_CI_HOLDOUT_HOST_PATH`). Loader still needs a docker CLI against that socket (worker image already has it).

---

## 3. Is `/var/run/docker.sock` already mentioned?

**Yes, only as a forbidden host mount.**

- `test_ops.py`: compose must **not** contain `/var/run/docker.sock`.
- `smoke.sh`: rendered compose containing that path is a **hard fail** (“worker topology still exposes the host Docker socket”).
- `docs/superpowers/plans/2026-08-23-trust-ci-operations-hardening.md`: “Worker communicates with a restricted Docker API proxy; **only the proxy mounts `/var/run/docker.sock`**.” That proxy **did not ship**; production topology is isolated DinD TCP 2375 instead.
- Compose DinD unix path is **`/run/user/1000/docker.sock` inside the DinD container**, not the host socket.
- `host.docker.internal`: **zero** matches.

Mounting `/var/run/docker.sock` into worker/loader is a **deliberate inversion** of current tests and smoke, not an unused option.

---

## 4. Worker env: gitignored vs committed (`HTTP_PROXY`)

`.gitignore`:

```
trust-ci/env/*.env
!trust-ci/env/*.example
trust-ci/runtime/*
!trust-ci/runtime/.gitkeep
```

- **Committed:** `trust-ci/env/worker.env.example` — DB URL, signing key path, App ID placeholders, workspace/holdout host paths. **No `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`.**
- **Gitignored live file:** `trust-ci/env/worker.env` (present on disk). Grep of the tree showed `HTTP_PROXY=http://127.0.0.1:1080` there. Spec/plan say operator sets proxy in **host-owned** worker env; never commit proxy secrets.
- Compose `worker.env_file` loads `./env/worker.env`. Proxy is **not** a compose `environment:` key.
- Inside the worker container, `127.0.0.1:1080` is **not** host `proxy-gateway`. Prior architect notes already flagged this. Switching to `http://host.docker.internal:1080` belongs in **gitignored** `worker.env` plus compose `extra_hosts: host.docker.internal:host-gateway` (Linux). Example file should document the pattern without committing live values.
- `NO_PROXY` should include `postgres` (and not need `docker-engine` if DinD is gone).

---

## 5. GitHub webhook POST path and HMAC headers

**Path:** `POST /webhooks/github`  
Defined in `trust-ci/src/adaptive_trust_ci/api.py`:

```python
@app.post('/webhooks/github')
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
)
```

FastAPI `Header` maps:

| Parameter | HTTP header |
|---|---|
| `x_hub_signature_256` | **`X-Hub-Signature-256`** |
| `x_github_event` | **`X-GitHub-Event`** |

Verification (`trust-ci/src/adaptive_trust_ci/webhooks.py`): HMAC-SHA256 of raw body with webhook secret; header must start with `sha256=`; 64 hex chars; `hmac.compare_digest`. Event name must be `pull_request` for enqueue; actions `opened|synchronize|reopened|ready_for_review` (+ `closed` cancel).

Tests (`trust-ci/tests/test_api.py`):

```python
return {'X-Hub-Signature-256': f'sha256={signature}', 'X-GitHub-Event': 'pull_request'}
self.client.post('/webhooks/github', content=body, headers=self.headers(body))
```

Spec M0.2: register `POST https://<ci>/webhooks/github` (API-only HMAC). Published mapping today is `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` (default **18080**, not host 8080).

---

## 6. Residual co-location risks if the host socket is used

Current isolation claims (`trust-ci/README.md`, `test_ops` name): worker is privileged but **runner** is `network=none`, `cap-drop ALL`, `no-new-privileges`, read-only rootfs, `.git` ro. API has no Docker. Worker does not mount host sock **today**; it uses DinD TCP on compose network `executor` (unpublished).

Host-socket skip **collapses** the second Docker trust domain:

- Worker (uid 10001, cap-drop ALL, read-only) mounting `/var/run/docker.sock` still gets a **full host Docker API** if the socket is writable: start privileged containers, mount `/`, talk to **n8n/Caddy/SearXNG/app DBs** on the same engine (`claw` already shares that engine — spec already called privileged DinD residual risk).
- Runner isolation (`--network none` etc. in `sandbox.py`) is **argv policy**, not a second daemon. A bug or token leak in worker can `docker run --privileged -v /:/host` on production stacks. Isolated DinD at least confined overlay + named volume `trust-ci-docker-data`.
- `TRUST_CI_WORKSPACE_HOST_ROOT` must be **host** paths. Named volume `trust-ci-workspaces` is visible to DinD as `/var/lib/adaptive-trust-ci/workspaces`. Host dockerd will **not** see that volume path unless it is a bind to the real host directory. Wrong paths → empty workspaces or mounting the wrong tree.
- Loader `docker pull` hits host registry/cache and **host** `HTTP_PROXY` if the daemon uses it; worker urllib still needs container-reachable proxy (`host.docker.internal:1080`). Proxy-gateway bind is `127.0.0.1:1080` only; `host-gateway` reaches host loopback **if** Docker extra_hosts works as on recent Engine.
- Hardening plan’s **restricted Docker API proxy** remains unimplemented. Host socket without that proxy is a **security regression** vs intended (and vs tests), even if it unblocks M0.1 on this kernel (`rootlesskit` denied).
- PreToolUse (`evaluate_pre_tool` / `_mentions_control_plane`): any shell command whose text contains substring `trust-ci` **and** a mutation signal is denied. `trust-ci/**` is both `control_plane_paths` and `protected_paths`. Product compose edits need structured Edit/Write or `scripts/grok_protected_write.py` with an exact protected-path grant — not `sed`/redirect. `scripts/grok_protected_write.py` only applies a manifest via `apply_manifest`; it does not special-case compose.

---

## Must-change list for the skip (product, not this report)

1. `trust-ci/compose.yaml` — remove `docker-engine` + `trust-ci-docker-data`; mount `/var/run/docker.sock` (ro if possible; Engine often needs rw) on loader+worker; `DOCKER_HOST=unix:///var/run/docker.sock`; `extra_hosts` for `host.docker.internal`; rebind workspaces/holdout as host paths; drop executor-only DinD network if unused.
2. `trust-ci/tests/test_ops.py`, `test_database_roles.py` (API split delimiter), `test_supply_chain.py`, `trust-ci/scripts/smoke.sh`.
3. `trust-ci/systemd/adaptive-trust-ci-compose.service`, `trust-ci/.env.example` (`TRUST_CI_DIND_IMAGE` optional/removed).
4. `trust-ci/env/worker.env.example` comments + documented `HTTP_PROXY` pattern; live gitignored `worker.env` proxy URL.
5. Docs: QUICKSTART, M0 spec/plan, activation report, `trust-ci/README.md` isolation paragraph.

`sandbox.py` allowed-env list already supports `DOCKER_HOST`; no code change strictly required for unix vs tcp.

---

## Write path note

`pre_tool_use.py` → `.grok/hooks/pre_tool_use.py` → `adaptive_grok.policy.evaluate_pre_tool`. Control-plane prefix `trust-ci` matches **any** command string containing that substring. Opaque shell mutation of compose is blocked; this analysis file under `engineering/changes/.../evidence/` is not `trust-ci/**`.
