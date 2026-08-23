# Implementation — GHCR docker-push (real pin attempt)

Write owner: `general_implementer`. Route `f70d038b336f`. Change `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`.  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`.  
Product identity **2.0.11**. Trust CI identity **2.1.0**. No commit, merge, deploy, GitHub App, cosign, or `compose up`.

Grant `505dcbeb77d6e91e` (`production` + `docker-push` on `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}`) was **already minted**. Did not mint another. Did not `docker login`. Did not read `.env`, PEMs, `~/.docker/config.json`, or `gh` tokens. Did not run `supply-chain-release.sh`, `docker buildx --push`, `docker compose push`, `docker image push`, or rebuild.

## Result: FAIL-CLOSED (registry denied)

| Step | Result |
| --- | --- |
| Preflight local `:2.1.0` `.Id` vs 20:36Z smoke | **PASS** (all three match) |
| `docker tag` to `ghcr.io/dimkox/…:2.1.0` | **PASS** (Ids unchanged) |
| `docker push ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` | **FAIL** — `error from registry: denied` / `denied` (401/403-class) |
| worker / runner push | **not attempted** (`&&` short-circuit after api) |
| Host-bearing **registry** pin kept | **none** |
| `/tmp/adaptive-trust-ci-pin.env` (or gitignored `build/` fallback) | **not written** (no complete pin set) |
| `tasks.md` GHCR checkbox | **left unchecked** |
| `git diff --exit-code` on example policy/env | **PASS** (exit 0; no digest in tracked files) |

**Block:** GHCR rejected the first `docker push` with registry `denied`. Fail-closed. Operator must authenticate **outside the agent**: `docker login ghcr.io` with a token that has `write:packages` on `ghcr.io/dimkox`. Do not scrape credentials. Do not retry from this slice.

## Commands

```bash
docker image inspect \
  adaptive-trust-ci-api:2.1.0 \
  adaptive-trust-ci-worker:2.1.0 \
  adaptive-trust-ci-runner:2.1.0 \
  --format '{{.RepoTags}} Id={{.Id}} Created={{.Created}} digests={{json .RepoDigests}}'

docker tag adaptive-trust-ci-api:2.1.0    ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0
docker tag adaptive-trust-ci-worker:2.1.0 ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0
docker tag adaptive-trust-ci-runner:2.1.0 ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0

docker image inspect \
  ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0 \
  ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0 \
  --format '{{.RepoTags}} Id={{.Id}}'

docker push ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0
# && docker push ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0
# && docker push ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0
# worker and runner never ran

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

Push stderr (api only): layers `Waiting`, then `error from registry: denied` / `denied`. Exit **1**.

## Preflight (12-hex; Ids still 20:36Z smoke)

| Mutable local tag | Created | `.Id` prefix |
| --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | `sha256:70a80960486b` |
| `adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | `sha256:bffd013ce151` |
| `adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | `sha256:900cfaaa49f1` |

Full 64-hex matched the assigned smoke table. Not leftovers from 18:46Z. Did not rebuild.

## RepoDigests after failed push (not pins)

Inspect used `{{json .RepoDigests}}` (not index 0) on the **`ghcr.io/dimkox/…:2.1.0` names**.

Each image JSON contained **two** entries: a hostless `adaptive-trust-ci-{api,worker,runner}@sha256:` (discard) **and** a `ghcr.io/dimkox/adaptive-trust-ci-{api,worker,runner}@sha256:` whose hex equalled `.Id`.

**RepoDigests contained a named-registry-host string: yes. Kept as a pin: no.**

Those `ghcr.io/dimkox/…@sha256:` strings appeared after **local `docker tag` only**. The registry denied the push. On Engine 29 a tag can fabricate a host-bearing RepoDigest with hex equal to `.Id` without a successful registry write. Hex equality is expected on this engine and is **not** proof of a pin. Fail-closed: do not copy tag-only descriptors into env. Do not keep a partial set.

Untracked pin env was **not** created. No 64-hex pin is recorded here (would be committed later).

## Out of slice (unchanged)

- Cosign still missing; no sign.
- `127.0.0.1:8080` not bound by this slice.
- `trust-ci/.env`, `trust-ci/runtime/policy.json`, `policy.example.json`, `.env.example` untouched.
- GitHub App, webhook, branch-protect, merge, `git push`: not this slice.

## Next (operator, not this grant window)

1. `docker login ghcr.io` with `write:packages` for `ghcr.io/dimkox`.
2. Re-mint a fingerprint-bound `docker-push` grant if this tree/HEAD/fingerprint drifted (this evidence file is a tracked change).
3. Re-preflight the same three local Ids, then `docker push` the three already-tagged `ghcr.io/dimkox/…:2.1.0` refs only.
4. Keep `name@sha256:` only after **successful** push, and only host-bearing names starting with `ghcr.io/dimkox` (casefold). Write untracked env only.

Rollback: none (no registry write succeeded). Local tags remain the 20:36Z images. Grant `505dcbeb77d6e91e` must not be reused after this tree change.
