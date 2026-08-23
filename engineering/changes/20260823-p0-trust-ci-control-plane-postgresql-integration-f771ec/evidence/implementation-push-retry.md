# Implementation — GHCR docker-push retry (after operator login)

Write owner: `general_implementer`. Route `74b20f9abfda`. Change `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`.  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`.  
Product identity **2.0.11**. Trust CI identity **2.1.0**. No commit, merge, deploy, GitHub App, cosign, or `compose up`.

Grant `5e39e67ac34582f7` (`production` + `docker-push` on `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}`) was **already minted**. Did not mint another. Did not `docker login`. Did not read `.env`, PEMs, `~/.docker/config.json` values, or `gh` tokens. Did not run `supply-chain-release.sh`, `docker buildx --push`, `docker compose push`, or rebuild.

Prior attempt (`implementation-push.md`, grant `505dcbeb77d6e91e`) failed closed on registry `denied`. This retry used the operator-logged-in daemon.

## Result: PASS

| Step | Result |
| --- | --- |
| Preflight local + `ghcr.io/dimkox/…:2.1.0` `.Id` vs 20:36Z smoke | **PASS** (all six names match) |
| Grant fingerprint vs tree | **PASS** (`f15aced3d8cdda…` / HEAD `5915b56`) |
| `docker tag` to `ghcr.io/dimkox/…:2.1.0` | **PASS** (Ids unchanged; tags already present) |
| `docker push ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` | **PASS** exit **0** |
| `docker push ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0` | **PASS** exit **0** |
| `docker push ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0` | **PASS** exit **0** |
| Host-bearing registry pins kept | **three** (`ghcr.io/dimkox/…@sha256:<64 hex>`) |
| Untracked pin env mode `600` | **written** (`/tmp/adaptive-trust-ci-pin.env`; gitignored fallback `build/adaptive-trust-ci-pin.env`) |
| `tasks.md` GHCR checkbox | **ticked** (all three host-bearing pins exist after successful push) |
| `git diff --exit-code` on example policy/env | **PASS** (no digest in those tracked files) |

Full 64-hex `name@sha256:` pins are **untracked-only**. They are not copied here.

## Commands

```bash
docker image inspect \
  adaptive-trust-ci-api:2.1.0 \
  adaptive-trust-ci-worker:2.1.0 \
  adaptive-trust-ci-runner:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0 \
  --format '{{.RepoTags}} Id={{.Id}} Created={{.Created}} digests={{json .RepoDigests}}'

docker tag adaptive-trust-ci-api:2.1.0    ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0
docker tag adaptive-trust-ci-worker:2.1.0 ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0
docker tag adaptive-trust-ci-runner:2.1.0 ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0

docker push ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0
docker push ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0
docker push ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0

docker image inspect \
  ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0 \
  --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'

git diff --exit-code -- \
  trust-ci/config/policy.example.json \
  trust-ci/.env.example \
  trust-ci/env \
  trust-ci/config/trust-store.example.json
```

Push stdout (all three): layers `Waiting` then `Pushed` / `Mounted from dimkox/…`. Registry confirmed:

| Ref | push exit | registry digest prefix (12 hex; full pin untracked-only) |
| --- | --- | --- |
| `ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` | 0 | `sha256:70a80960486b` |
| `ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0` | 0 | `sha256:bffd013ce151` |
| `ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0` | 0 | `sha256:900cfaaa49f1` |

A first wrapped `docker push` with `tee` + `/tmp/adaptive-trust-ci-*.txt` was hook-denied (`control-plane shell mutation` via substring `trust-ci`). Did not login. Retried with the three plain `docker push` commands above; all three ran and exited 0.

## Preflight (12-hex; Ids still 20:36Z smoke)

| Mutable / GHCR-tagged name | Created | `.Id` prefix |
| --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` and `ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | `sha256:70a80960486b` |
| `adaptive-trust-ci-worker:2.1.0` and `ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | `sha256:bffd013ce151` |
| `adaptive-trust-ci-runner:2.1.0` and `ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | `sha256:900cfaaa49f1` |

Full 64-hex matched the assigned smoke table. Not leftovers from 18:46Z. Did not rebuild.

## RepoDigests after successful push (pins kept)

Inspect used `{{json .RepoDigests}}` (not index 0) on the **`ghcr.io/dimkox/…:2.1.0` names**.

Each image JSON contained **two** entries: a hostless `adaptive-trust-ci-{api,worker,runner}@sha256:` (**discard**) **and** a `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}@sha256:` matching `name@sha256:[0-9a-f]{64}` whose name starts with `ghcr.io/dimkox` (**keep**).

**RepoDigests contained a named-registry-host string: yes. Kept as a pin: yes** — only because all three `docker push` commands exited 0. The same host-bearing strings existed after local `docker tag` on Engine 29 before this retry; those tag-only descriptors were not pins. This retry’s push confirmations (`2.1.0: digest: sha256:… size: 856`) plus exit 0 make the host-bearing entries keepable.

Kept pins (untracked-only; full 64-hex is **not** in git):

```text
TRUST_CI_API_IMAGE=ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b…
TRUST_CI_WORKER_IMAGE=ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce151…
TRUST_CI_RUNNER_IMAGE=ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1…
```

Written mode `600` to `/tmp/adaptive-trust-ci-pin.env` (preferred) and gitignored `build/adaptive-trust-ci-pin.env` (Write-tool fallback; then copied to `/tmp`). Did not write `trust-ci/.env`. Tracked examples stay `REPLACE_WITH_*`.

## Out of slice (unchanged)

- Cosign still missing; no sign.
- `127.0.0.1:8080` not bound by this slice.
- `trust-ci/.env`, `trust-ci/runtime/policy.json`, `policy.example.json`, `.env.example` untouched.
- GitHub App, webhook, branch-protect, merge, `git push`: not this slice.

Rollback: registry now holds the three `:2.1.0` manifests. Local tags remain the 20:36Z images. Untracked pin env is disposable and must not be committed.
