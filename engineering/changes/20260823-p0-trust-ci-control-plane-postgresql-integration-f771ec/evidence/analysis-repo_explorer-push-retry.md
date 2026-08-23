# Repo explorer — GHCR login and 20:36Z smoke Ids (push retry)

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec` (status `blocked`)  
Active route: `74b20f9abfda` (`allowed_agents` include `repo_explorer`)  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Inspected: 2026-08-23. Read-only except this evidence file. No `.env`, PEM, docker `auth` values, or `gh` token. **Did not** `docker login` or `docker push`.

Narrow question: is GHCR login now present, and are the three local smoke images still the 20:36Z Ids?

---

## GHCR login: **yes**

`~/.docker/config.json` exists. Top-level keys: `auths` only.

| Key set | Value |
| --- | --- |
| `auths` keys (hostnames only) | `["ghcr.io", "https://index.docker.io/v1/"]` |
| `auths` field names (values unread) | `ghcr.io` → `["auth"]`; Hub → `["auth"]` |
| `credHelpers` keys | `[]` |
| `credsStore` | absent |

Previous push analysis had Hub-only `auths`. **`ghcr.io` is now present.** Full config not dumped.

`gh auth status` (scopes only; token not copied): logged in as **Dimkox**, protocol https. Scopes: **`gist`, `read:org`, `repo`, `workflow`, `write:packages`**. `write:packages` was missing on the last pass; it is present now.

Docker `auths` and `gh` scopes are independent credentials. Presence of a `ghcr.io` `auth` key plus `write:packages` on `gh` is the login evidence; write permission is not proven until a later `docker push`.

---

## Image Ids vs 20:36Z smoke: **yes, all six names match**

Expected smoke:

| Image | Expected `.Id` |
| --- | --- |
| api | `sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` |
| worker | `sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` |
| runner | `sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` |

| Inspected name | Created | `.Id` match |
| --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | yes |
| `adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | yes |
| `adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | yes |
| `ghcr.io/dimkox/adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | yes (same Id; tag from failed push still local) |
| `ghcr.io/dimkox/adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | yes |
| `ghcr.io/dimkox/adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | yes |

Not rebuilt. Not leftovers from 18:46Z. `RepoTags` pair each local name with `ghcr.io/dimkox/…:2.1.0`. `RepoDigests` still include host-bearing `ghcr.io/dimkox/…@sha256:<same as .Id>` from **local tag only** (Engine 29). Those are **not** registry pins; the last `docker push` was denied.

---

## Remint

Prior grant `505dcbeb77d6e91e` must **not** be reused (tree already drifted after that push-fail evidence). This report dirties the tree again; the write owner remints against the **then-current** fingerprint after this file lands. Preconditions for that remint are met: GHCR docker login key present, `write:packages` on `gh`, smoke Ids unchanged, GHCR tags already on the daemon.

Do not push from this agent. Do not reuse the old grant.

---

login present yes/no: **yes**  
Ids match yes/no: **yes**  
ready to remint grant yes/no: **yes**
