# Repo explorer — can a registry destination be recovered for a real image pin?

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `f70d038b336f` (`allowed_agents` include `repo_explorer`; write owner `general_implementer`)  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Origin: `https://github.com/Dimkox/adaptive-grok-build-pro.git`  
Inspected: 2026-08-23. Read-only except this evidence file. No `.env`, PEM, docker `auth` values, identity tokens, or full `~/.docker/config.json`. No push, login, tag, or grant mint.

User selected previous-turn option 1 (registry URL + `docker-push` grant for a real pin). This turn’s query is only `1`. **No registry URL was named.** Inferring `ghcr.io/Dimkox/…` or `docker.io/<user>/…` would be invention.

---

## Recoverable registry: **NONE**

| Candidate | Verdict |
| --- | --- |
| In-tree image refs | `trust-ci/.env.example` uses **`registry.example.com`** + `REPLACE_WITH_*`. That host is a placeholder, not a destination. |
| `ghcr.io` / `ghcr.io/Dimkox` | **Zero matches** anywhere in this repository. `Dimkox` is the GitHub owner (`Dimkox/adaptive-grok-build-pro`), not a named container registry. |
| `TRUST_CI_{API,WORKER,RUNNER}_REPOSITORY` | Required by `supply-chain-release.sh`, **unset in every tracked env example**. `trust-ci/env/supply-chain.env.example` has host paths only (`TRUST_CI_SUPPLY_CHAIN_DIR`, `COSIGN_PUBLIC_KEY`, compose env, policy path). |
| Docker client `auths` keys (hostnames only) | Only `https://index.docker.io/v1/`. **No `ghcr.io`, no private registry host.** |
| `credHelpers` keys | `[]`. `credsStore` absent. |
| Docker Hub as implied dest | Not recoverable. Engine 29 `docker info` has **no** `.Username` field. No in-tree `docker.io/<ns>/adaptive-trust-ci-*` path. Hub login hostname ≠ image repository. |
| GitHub Packages | `GET /users/Dimkox/packages?package_type=container` → **403** (`read:packages` missing). `GET /repos/Dimkox/adaptive-grok-build-pro/packages?package_type=container` → **404**. Cannot recover a GHCR package name. |
| Prior analysis | Architect/task_analyst already ruled: user must **name** the registry; do not mint a grant in anticipation. |

Selecting option `1` without a URL is incomplete consent: it names the *kind* of next slice, not a destination.

Do **not** treat `registry.example.com` as pushable. Do **not** substitute `ghcr.io/Dimkox`.

---

## Policy: what is actually gated as `docker-push`

`.grok-stack/adaptive_grok/policy.py` `_production_action`:

```text
argv[:2] == ['docker', 'push']  →  'docker-push'
```

`evaluate_pre_tool` then requires `has_valid_approval(root, 'production', action='docker-push')` with **no `resource=`**.

| Command | Classified `docker-push`? |
| --- | --- |
| `docker push PLACEHOLDER_REGISTRY/adaptive-trust-ci-api:2.1.0` | **Yes** |
| `docker tag adaptive-trust-ci-api:2.1.0 PLACEHOLDER_REGISTRY/…` | **No** (not a production action) |
| `docker image inspect …` | **No** |
| `docker compose … build` (no `--push`) | **No** |
| `docker compose … --push` | **No** (`['docker','compose',…]`) |
| `docker buildx build … --push` | **No** (`['docker','buildx',…]`) |
| `trust-ci/scripts/supply-chain-release.sh --confirm-push` | **No** (script argv, not `docker push`). Inner `docker buildx build --push` is also not classified. Control-plane mention of `trust-ci` does **not** by itself match `_SHELL_MUTATION_SIGNAL`, so PreToolUse may not block the script either. Do not use that gap. |

`supply-chain-release.sh` is the **wrong** tool for already-built local `:2.1.0` images: it always `docker buildx build --push --sbom=true --provenance=mode=max` (rebuild + push), requires `TRUST_CI_{API,WORKER,RUNNER}_REPOSITORY` without tag/digest, `TRUST_CI_PYTHON_BASE_IMAGE` as `name@sha256:64hex`, `TRUST_CI_RELEASE_VERSION`, `TRUST_CI_POLICY_TEMPLATE`, `TRUST_CI_SUPPLY_CHAIN_DIR`, `COSIGN_PRIVATE_KEY`, and PATH tools `docker python3 trivy syft cosign sha256sum git`. **`cosign` is ABSENT** on this host → script exits 69 before any push.

To pin the **already-built** daemon images, use `docker tag` + `docker push` of those tags. That is the only invocation this policy treats as `docker-push`.

---

## `grok_approve.py` / `add_approval()` — is `--resource` required for `docker-push`?

**No.** Production `docker-push` does not require `--resource`.

`scripts/grok_approve.py`: `--resource` is optional `append`. `add_approval()` in `.grok-stack/adaptive_grok/state.py`:

- `docker-push` is a **`production`** scope action (`SCOPE_ACTIONS['production']`).
- Resources are **required** only when `normalized_scope in {'external-write', 'protected-path'}`.
- Empty `resources=[]` is stored and accepted for `production`.
- `has_valid_approval(..., action='docker-push')` (no `resource`) ignores grant `resources` unless a resource is passed in. PreToolUse does **not** pass the push destination, so `--resource` is **documentation only** for this action: it will not bind `docker push` to a hostname.

AGENTS.md: resources are mandatory for protected/external writes; production `docker-push` is the named production action. Wildcard scope is still forbidden. An agent may mint a grant only after the user names the operation **and** (for this slice) the registry.

No live `production`/`docker-push` grant exists. `approvals.json` has eight `protected-path-write` rows for this change (docs/tests/`trust-ci/**`); none is `docker-push`. Several are already past their TTL.

Option `1` is **not** enough to run `grok_approve.py` now: destination still unnamed.

---

## Host facts (no secrets)

### Images — local `:2.1.0` **exist** (same Ids as `implementation-images.md` smoke)

| Tag | Exists | `.Id` (`local-image-id, not a registry pin`) | `RepoDigests` |
| --- | --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` | yes | `sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` | `adaptive-trust-ci-api@sha256:70a809…` (no registry host) |
| `adaptive-trust-ci-worker:2.1.0` | yes | `sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` | local-only, equals `.Id` |
| `adaptive-trust-ci-runner:2.1.0` | yes | `sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` | local-only, equals `.Id` |
| `adaptive-trust-ci-test:2.1.0` | yes | `sha256:597d83ff9e6a7a8337b6aaf2db6d54b08bf2c957089731b40974b914592abd2d` | local-only; **not** a production pin (`compose.test.yaml` only) |

`RepoTags` also include `:latest` on api/worker leftovers. Engine 29 local `RepoDigests` still **lack a registry hostname**. After a real `docker push`, inspect JSON should gain `PLACEHOLDER_REGISTRY/name@sha256:…`.

Do **not** push `adaptive-trust-ci-test:2.1.0` for HANDOFF §3.

### Cosign / scanners

- `command -v cosign` → **ABSENT** (blocks `supply-chain-release.sh` and `verify-supply-chain.sh`, not raw `docker push`).
- `syft` `/usr/local/bin/syft`, `trivy` `/usr/local/bin/trivy` present.
- `docker buildx` plugin **v0.36.1** present (unused for already-built tag/push).

### Docker login (keys only)

`~/.docker/config.json` exists. Top-level keys: `auths` only.

- `auths` keys: `["https://index.docker.io/v1/"]`
- `credHelpers` keys: `[]`
- `credsStore`: absent
- Docker Hub entry field **names** (values unread): `["auth"]`. Full file not dumped.

No `ghcr.io` (or any non-Hub) hostname. Even after the user names a registry, **`docker login` to that host is still required** unless it is Docker Hub *and* that Hub credential is valid for the named namespace (unverified; Username API field missing on Engine 29).

### `gh` / GitHub

`gh auth status`: logged in as **Dimkox**, protocol https, scopes **`gist`, `read:org`, `repo`, `workflow`**. Token value not copied.

Missing for GHCR: `read:packages`, `write:packages`. Even a later invented `ghcr.io/Dimkox/…` push would fail credential/scope checks. Origin is the GitHub git remote, not a container registry.

---

## Exact grant command shape (do not run until URL is named)

Minimum accepted by `add_approval` (resources not required):

```bash
python3 scripts/grok_approve.py production \
  --action docker-push \
  --source explicit-user-consent \
  --ttl 15 \
  --reason 'Push already-built adaptive-trust-ci api/worker/runner:2.1.0 to the user-named registry'
```

Recommended once the user replaces `PLACEHOLDER_REGISTRY` (stored on the grant; **not** enforced against argv):

```bash
python3 scripts/grok_approve.py production \
  --action docker-push \
  --source explicit-user-consent \
  --ttl 15 \
  --reason 'Push already-built adaptive-trust-ci api/worker/runner:2.1.0 to PLACEHOLDER_REGISTRY' \
  --resource 'PLACEHOLDER_REGISTRY/adaptive-trust-ci-api:2.1.0' \
  --resource 'PLACEHOLDER_REGISTRY/adaptive-trust-ci-worker:2.1.0' \
  --resource 'PLACEHOLDER_REGISTRY/adaptive-trust-ci-runner:2.1.0'
```

Bind happens at mint time to current repo `Dimkox/adaptive-grok-build-pro`, route `f70d038b336f`, change `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`, Git HEAD, and tree fingerprint. Any commit or tree edit invalidates it. Do not add `--profile release`. Do not use wildcard scope. Do not mint against `registry.example.com`.

---

## Exact tag / push / inspect (already-built images; `PLACEHOLDER_REGISTRY` only)

Login (human; not classified `docker-push`; do not run without a named host):

```bash
docker login PLACEHOLDER_REGISTRY
```

Retag local smoke images (not gated):

```bash
docker tag adaptive-trust-ci-api:2.1.0    PLACEHOLDER_REGISTRY/adaptive-trust-ci-api:2.1.0
docker tag adaptive-trust-ci-worker:2.1.0 PLACEHOLDER_REGISTRY/adaptive-trust-ci-worker:2.1.0
docker tag adaptive-trust-ci-runner:2.1.0 PLACEHOLDER_REGISTRY/adaptive-trust-ci-runner:2.1.0
```

Push (gated; needs the grant above):

```bash
docker push PLACEHOLDER_REGISTRY/adaptive-trust-ci-api:2.1.0
docker push PLACEHOLDER_REGISTRY/adaptive-trust-ci-worker:2.1.0
docker push PLACEHOLDER_REGISTRY/adaptive-trust-ci-runner:2.1.0
```

Inspect after push (expect a registry hostname inside `RepoDigests`; still do not write into tracked examples):

```bash
docker image inspect PLACEHOLDER_REGISTRY/adaptive-trust-ci-api:2.1.0 \
  --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
docker image inspect PLACEHOLDER_REGISTRY/adaptive-trust-ci-worker:2.1.0 \
  --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
docker image inspect PLACEHOLDER_REGISTRY/adaptive-trust-ci-runner:2.1.0 \
  --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
```

Use `{{json .RepoDigests}}`, not `{{index .RepoDigests 0}}`. A successful registry pin looks like `PLACEHOLDER_REGISTRY/adaptive-trust-ci-api@sha256:<64 hex>`, **not** the current local-only `adaptive-trust-ci-api@sha256:70a809…`.

Do **not** run `supply-chain-release.sh --confirm-push` for this already-built set (rebuilds; needs unnamed `TRUST_CI_*_REPOSITORY`; **cosign absent**). Do not `compose up`. Do not copy any digest into `trust-ci/.env.example` or `policy.example.json`.

---

## Blockers

1. **Registry: NONE recoverable.** User must name a real host/namespace. `registry.example.com` and `ghcr.io/Dimkox` are not usable.
2. **Grant: not minted and must not be minted on this turn.** Option `1` without a URL is not an exact delegated `docker-push`. `--resource` optional for production; destination still required as human input.
3. **Login:** only Docker Hub hostname in `auths`; no GHCR; Hub username unverified. `docker login PLACEHOLDER_REGISTRY` still required after a URL is named. `gh` scopes lack `write:packages` / `read:packages` (GHCR would fail even if invented).
4. **Cosign: ABSENT.** Blocks signed supply-chain release and systemd `verify-supply-chain.sh`. Does **not** block a raw `docker push` of local tags. HANDOFF §3 signed bundle still waits on cosign + named repos after a pin exists.
5. Local `:2.1.0` api/worker/runner images **do exist** and can be tagged/pushed once (1)–(3) clear.

Write owner (`general_implementer`): **stop**. Ask the user to name the registry URL (and, if GHCR, a packages-capable login). Then mint the grant and run the `PLACEHOLDER_REGISTRY` commands with that string substituted. Do not invent `ghcr.io/Dimkox`.

---

recoverable registry or NONE: **NONE**  
exact grant command shape: `python3 scripts/grok_approve.py production --action docker-push --source explicit-user-consent --ttl 15 --reason '…' [--resource 'PLACEHOLDER_REGISTRY/adaptive-trust-ci-{api,worker,runner}:2.1.0']` (resources optional in `add_approval`, not enforced on `docker push`)  
exact docker tag/push/inspect: `docker tag adaptive-trust-ci-{api,worker,runner}:2.1.0 PLACEHOLDER_REGISTRY/adaptive-trust-ci-{api,worker,runner}:2.1.0`; `docker push PLACEHOLDER_REGISTRY/adaptive-trust-ci-{api,worker,runner}:2.1.0`; `docker image inspect PLACEHOLDER_REGISTRY/adaptive-trust-ci-{api,worker,runner}:2.1.0 --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'`  
blockers: **no recoverable registry**; **no docker-push grant** (do not mint until URL named); **no login to a non-Hub/named registry** (Hub-only `auths` key; `gh` lacks packages scopes); **cosign absent** (blocks supply-chain script, not tag+`docker push`).
