# Analysis — architect (docker-push real pin)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `f70d038b336f` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer`  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Human gates on this route: none. Record this design. Do not reopen product design.

Read-only except this report. No `.env`, keys, push, merge, deploy, GitHub App, `compose up`, or image push. Did not read `trust-ci/runtime/github-app-private-key.pem`, `trust-ci/.env`, `~/.docker/config.json`, or `/tmp/adaptive-trust-ci-build.env`.

Narrow question: bounded next slice after user selected **"1" = docker-push for a real pin**. No registry URL was named.

---

## Ruling (one screen)

**STOP. Do not mint a grant. Do not `docker tag` / `docker push`. Do not write pins. Wait for an explicit registry host + repository prefix.**

Selection `"1"` names the *kind* of next slice (`production` + `docker-push`). It is **not** a registry URL, not a resource, and not enough to call `grok_approve.py`. `.env.example` `registry.example.com` is a documented fake. Do not invent `ghcr.io/Dimkox/…` from `origin`. Local `RepoDigests` that equal `.Id` and lack a registry host are still **not** pins.

When (and only when) the user names a real `PLACEHOLDER_REGISTRY` that contains a hostname, the write owner may mint a fingerprint-bound grant with **three exact repo resources**, tag the already-built `:2.1.0` images, `docker push` those three names, inspect JSON `RepoDigests`, keep only host-bearing `name@sha256:<64 hex>`, and write those strings into **untracked `/tmp` env only**. Fail-closed on login 401/403 or hostless digests. Do **not** run `supply-chain-release.sh` (cosign missing). Do **not** `compose up` (127.0.0.1:8080 still searxng). Do **not** pin `trust-ci/runtime/policy.json` until the user names deploy (option 3).

---

## Host facts this turn (measured, not copied from chat)

| Fact | Value |
| --- | --- |
| Docker | 29.7.2 · Compose v5.5.0 |
| `cosign` | **missing** (`command -v` empty) |
| `127.0.0.1:8080` | **LISTEN** (searxng). Do not bind it. |
| Product / Trust CI identity | `2.0.11` / **2.1.0** |
| `/tmp/adaptive-trust-ci-build.env` | present (unread) |
| Local tags still the 20:36Z smoke | yes (see table) |

| Mutable local tag | Created | `.Id` | `RepoDigests` JSON |
| --- | --- | --- | --- |
| `adaptive-trust-ci-api:2.1.0` | 2026-08-23T20:36:27Z | `sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23` | `["adaptive-trust-ci-api@sha256:70a80960…1207b23"]` |
| `adaptive-trust-ci-worker:2.1.0` | 2026-08-23T20:36:30Z | `sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227` | `["adaptive-trust-ci-worker@sha256:bffd013c…f62227"]` |
| `adaptive-trust-ci-runner:2.1.0` | 2026-08-23T20:36:54Z | `sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2` | `["adaptive-trust-ci-runner@sha256:900cfaaa…291cb2"]` |

Every `RepoDigests[0]` **equals** `.Id` and has **no registry host**. That remains a local-daemon-descriptor. Hex equality is **not** the reject reason after a real push (Engine 29 Hub pull of python also equalled `.Id`). The reject reason is **missing registry host**.

---

## 1. Grant — `"1"` is selection, not a URL

### 1.1 Do not mint now

`scripts/grok_approve.py` may be invoked only for an explicitly delegated named operation **and**, for this slice, named resources. Production scope in code does **not** require `--resource` (`state.add_approval` only forces resources for `external-write` / `protected-path`). This slice **overrides that**: no resource ⇒ no grant. Wildcard resource `*` is forbidden.

PreToolUse (`policy.evaluate_pre_tool`) classifies `argv[:2] == ['docker', 'push']` as `docker-push` and checks `has_valid_approval(..., action='docker-push')` **without** passing the image name as `resource`. A grant with resources still matches that check. The write owner must therefore **process-enforce** the three exact names; the hook will not.

Do **not** use bypasses the classifier misses:

| Command | Classified as `docker-push`? | This slice |
| --- | --- | --- |
| `docker push HOST/repo:2.1.0` | **yes** | only allowed form |
| `docker image push …` | no (`docker image`) | forbidden |
| `docker compose push` | no (`docker compose`) | forbidden |
| `docker buildx build --push` | no | forbidden |
| `trust-ci/scripts/supply-chain-release.sh --confirm-push` | inner `docker buildx --push`; also needs cosign + `COSIGN_PRIVATE_KEY` | **forbidden** (cosign missing; would rewrite a policy file) |

`docker tag` is not a production action. Do not tag until the grant exists and the URL is named (tagging to a guessed host is wasted motion and a leak of intent).

### 1.2 Grant shape **after** the user names `PLACEHOLDER_REGISTRY`

`PLACEHOLDER_REGISTRY` is a registry **host plus optional path prefix**, with no tag and no digest. It must contain a hostname (a `.` in the first path component, or `localhost` / `127.0.0.1` with optional port). Examples of **acceptable shapes** (do not treat these as chosen): `ghcr.io/example-org`, `docker.io/example-user`, `registry.internal.example:5000/ci`.

Reject as the named URL:

- `"1"` / `"docker-push"` / `"yes"`
- `registry.example.com` from `trust-ci/.env.example` (fake)
- Git remote `github.com:Dimkox/adaptive-grok-build-pro` inferred as `ghcr.io/dimkox`
- A mutable tag (`:2.1.0`) or `@sha256:…` in the registry prefix
- Bare Docker Hub `user/repo` with **no** `docker.io/` host (Engine inspect often then yields hostless `user/repo@sha256:…`, which this slice fail-closes)

Exact mint (bind to **then-current** route, change, HEAD, fingerprint; default TTL 15 minutes is enough for three pushes):

```bash
python3 scripts/grok_approve.py production \
  --action docker-push \
  --resource "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-api" \
  --resource "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-worker" \
  --resource "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-runner" \
  --source explicit-user-consent \
  --ttl 15 \
  --reason "user selected docker-push (option 1); registry named ${PLACEHOLDER_REGISTRY}"
```

Three exact resources. No glob. No `git-push-branch`, merge, or `protected-path-write` on this grant. Any tree or HEAD change invalidates it; do not edit product files in this slice so the grant stays live.

`"1"` plus a later named URL in the same task is enough **explicit-user-consent** to mint **that** grant. `"1"` alone is not.

---

## 2. Push method — retag already-built `:2.1.0`, then `docker push`

Do **not** rebuild unless the preflight Id check fails. Do **not** run `supply-chain-release.sh` (requires `cosign`, `COSIGN_PRIVATE_KEY`, `TRUST_CI_*_REPOSITORY`, rebuilds with `buildx --push`, writes `policy.json` under `TRUST_CI_SUPPLY_CHAIN_DIR`). Cosign is absent on this host; skip sign. Optional Syft/Trivy of **pushed** names may land only under `/tmp/adaptive-trust-ci-push-smoke/`; not required for a pin.

### 2.1 Preflight (before tag)

Inspect the three local tags. Ids **must** still be the 20:36Z smoke values above. If missing or different: **STOP**. Do not push leftovers from 18:46Z (`9b957043…` / `ef58751c…` / `8ceb98cd…`). Do not silently rebuild (rebuild is not `docker-push`).

Confirm `PLACEHOLDER_REGISTRY` host rule. Confirm grant id, action `docker-push`, three resources, unexpired, matching HEAD/fingerprint/route/change.

Login: the user must already be authenticated to **that** host. Do not read credential files. Do not `echo` tokens into `docker login`. If the operator must log in, they do it outside the agent. A 401/403 on the first `docker push` is **fail-closed** (see §4).

### 2.2 Tag + push (cwd irrelevant; names are daemon refs)

```bash
docker tag adaptive-trust-ci-api:2.1.0    "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-api:2.1.0"
docker tag adaptive-trust-ci-worker:2.1.0 "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-worker:2.1.0"
docker tag adaptive-trust-ci-runner:2.1.0 "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-runner:2.1.0"

docker push "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-api:2.1.0"
docker push "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-worker:2.1.0"
docker push "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-runner:2.1.0"
```

Push **only** those three refs. Do not push `latest`. Do not push python/postgres/dind. Do not `compose --push` / `up`.

Avoid putting the contiguous token `trust-ci` in a **mutating** shell that the hook treats as control-plane (image names contain that substring; `docker tag` / `docker push` are not `_SHELL_MUTATION_SIGNAL`, so they should pass). Do not wrap with `python3 -c` / `tee`.

---

## 3. After push — host-bearing RepoDigests → untracked env only

Inspect the **registry tags just pushed**, not the hostless local names:

```bash
docker image inspect "${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-api:2.1.0" \
  --format 'Id={{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
# same for worker and runner
```

Use `{{json .RepoDigests}}`. Do **not** `{{index .RepoDigests 0}}` (the first entry on Engine 29 may still be the hostless local descriptor).

Keep a digest iff **all** of:

1. Full match `name@sha256:[0-9a-f]{64}`.
2. `name` **starts with** the named `PLACEHOLDER_REGISTRY` (casefold).
3. First path component of `name` is a registry host: contains `.`, or is `localhost` / `127.0.0.1` (optional `:port`).
4. One kept digest per image.

Discard hostless entries such as `adaptive-trust-ci-api@sha256:70a80960…`. Hex of a kept digest **may** equal `.Id`; that is expected on this engine after a real push/pull.

Write **only** into untracked `/tmp/adaptive-trust-ci-pin.env` mode `600` (preferred; do not write `trust-ci/.env` — protected path). Values:

```text
TRUST_CI_API_IMAGE=<PLACEHOLDER_REGISTRY>/adaptive-trust-ci-api@sha256:<kept hex>
TRUST_CI_WORKER_IMAGE=<PLACEHOLDER_REGISTRY>/adaptive-trust-ci-worker@sha256:<kept hex>
TRUST_CI_RUNNER_IMAGE=<PLACEHOLDER_REGISTRY>/adaptive-trust-ci-runner@sha256:<kept hex>
```

Leave python base / postgres / dind as they already are in the unread smoke env; do not copy them into git. Do not set `TRUST_CI_RUNNER_BUILD_TAG` to a digest.

JSON inspect dumps: `/tmp/adaptive-trust-ci-push-smoke/{api,worker,runner}.inspect.txt` labeled `registry-pin-candidate`. Same `/tmp` rule as the build smoke: creating files whose command string contains `trust-ci` plus a mutation signal is blocked; keep dumps under `/tmp/adaptive-trust-ci-push-smoke/` and do not write `trust-ci/runtime/`.

### 3.1 Illegal destinations (never this slice)

```text
trust-ci/.env.example
trust-ci/config/policy.example.json
trust-ci/env/*.example
trust-ci/config/trust-store.example.json
trust-ci/.env
trust-ci/runtime/policy.json          # option 3 / deploy, not this slice
git index / any tracked file
```

`Policy.from_dict` / `_IMAGE_DIGEST_RE` accept any `name@sha256:<64 hex>`, including a hostless local descriptor. `tests/test_structure.py::test_trust_ci_policy_uses_immutable_sandbox_and_external_status` allows placeholder **or** a real digest in `policy.example.json`. Pasting a pin there would pass the test and **poison git**. Do not “fix” the test this slice.

Tracked evidence `implementation-push.md` may record commands, exit codes, untracked env path, and “RepoDigests contained named registry host: yes/no”. **Do not copy 64-hex pins into that markdown** (it will be committed later). Redact to 12 hex if a proof-of-measurement is needed.

Fail-closed git check after any attempt:

```bash
git diff --exit-code -- \
  trust-ci/config/policy.example.json \
  trust-ci/.env.example \
  trust-ci/env \
  trust-ci/config/trust-store.example.json
```

---

## 4. Fail-closed

| Condition | Action |
| --- | --- |
| No registry URL / URL is `"1"` / `registry.example.com` / inferred GHCR | **STOP** now. No grant, no tag, no push. |
| Local `:2.1.0` Ids ≠ 20:36Z smoke | **STOP**. Do not push. Do not rebuild unless the user names a rebuild. |
| Grant missing, expired, wrong action, missing one of the three resources, or tree/HEAD drift | Do not push. Re-mint only after user-named URL still applies. |
| `docker push` 401/403/unauthorized / login fails | **STOP**. Do not read `~/.docker/config.json`, `.env`, PEMs, or `gh` tokens. Do not retry with scraped creds. |
| Push of any one image fails | **STOP**. Do not treat the other two as a complete pin set. Do not write a partial env. |
| After successful push, JSON `RepoDigests` still has **no** host-bearing name that starts with `PLACEHOLDER_REGISTRY` | **STOP**. Do not copy the hostless local descriptor into env. Not a pin. |
| Temptation to fill examples or `runtime/policy.json` so HANDOFF §3 “looks done” | Refuse. Deployed policy pin is **option 3**. |

---

## 5. Out of slice

| Action | Why |
| --- | --- |
| `docker compose up` / systemd / `/health/ready` | Deploy. Port **8080 already bound**. |
| Write `trust-ci/runtime/policy.json` or host compose env with the new pins | Option **3** (deploy). User selected **1**. |
| Production holdout under `/srv` or `/opt` | Bundles still absent. Example digest stays test-locked. |
| GitHub App, webhook secret, App RSA | HANDOFF §4. Do not read leftover PEM. |
| TLS webhook, `branch-protect`, merge, `git push` | Later named grants. |
| `supply-chain-release.sh`, `cosign sign` | Cosign missing; script rewrites policy; not this method. |
| Product-file edits, Makefile, tests, VERSION bump | Freeze. Skip `grok_verify` / reviews if product tree unchanged (`AGENTS.md` skip no-op). |
| Commit leftover `engineering/changes/20260817-вычисти*` | Prior ruling. |

---

## Return block (write owner = `general_implementer`)

**This turn:** write nothing but analysis. Do not call `grok_approve.py`. Do not `docker tag` / `docker push`. Ask the user for `PLACEHOLDER_REGISTRY` (host + optional path, no tag/digest).

**After the URL is named (not now):**

1. Confirm local `:2.1.0` Ids still match the 20:36Z smoke table.
2. Mint the exact production `docker-push` grant with the three `--resource` repo names.
3. `docker tag` those three images to `${PLACEHOLDER_REGISTRY}/adaptive-trust-ci-{api,worker,runner}:2.1.0`.
4. `docker push` those three refs only. Fail-closed on auth or any one failure.
5. Inspect JSON `RepoDigests`; keep only host-bearing names under the named prefix; write `name@sha256:` into `/tmp/adaptive-trust-ci-pin.env` only.
6. `git diff --exit-code` on example policy/env. Evidence summary without 64-hex pins.
7. Stop. Do not `compose up`. Do not pin deployed `runtime/policy.json`.

---

## Single recommended design ruling the write owner must follow

**STOP until the user names a real registry host and repository prefix. `"1"` selects docker-push and is not a URL — do not mint a grant, do not infer `ghcr.io` from git remote, and do not treat Engine 29 hostless `RepoDigests` that equal `.Id` as pins. After a named `PLACEHOLDER_REGISTRY`, mint `production` + `docker-push` with three exact `--resource` repos, retag the already-built `adaptive-trust-ci-{api,worker,runner}:2.1.0` images, `docker push` those three names (not `supply-chain-release.sh`; cosign is missing), keep only inspect JSON RepoDigests that contain that registry host, and write `name@sha256:` into untracked `/tmp` env only. Fail-closed on login failure or still-hostless digests. Do not write pins into `policy.example.json`, `.env.example`, or git, do not `compose up` on 8080, and do not pin deployed `runtime/policy.json` until the user names deploy (option 3).**
