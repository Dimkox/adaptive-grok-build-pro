# Docs research — real registry pin vs local image Id

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `f70d038b336f` (`docs_researcher` allowed; write-owner `general_implementer`)  
Agent: `docs_researcher` (read-only except this report)  
Date: 2026-08-23  
User option: **1 — registry + docker-push**

This report recovers what tracked docs, ADRs, and contracts already require for a **real pin**. It does **not** invent a registry URL, image digest, policy-epoch 12-hex, GitHub App ID, or Check Run ID. No `.env`, PEM, Cosign private key, App key, webhook secret, or human private key was read. No push, merge, or deploy.

`engineering/adr/` is empty. `engineering/contracts/openapi/` and `engineering/contracts/schemas/` contain no image-pin schema. The machine-readable pin contract is Compose interpolation + example env/policy placeholders + `supply-chain-release.sh` / `verify-supply-chain.sh`.

---

## Sources (requested order)

| File | Pin / grant content |
| --- | --- |
| `GROK_BUILD_HANDOFF.md` §3 | Remaining operational pin: **deployed** policy/env, not a local Id. Retain image digests, policy digest, SBOM, vuln scan, CI public key, holdout digest. Do not commit production env. |
| `trust-ci/README.md` | Inspect recipe; untracked `name@sha256:`; do not inspect `adaptive-trust-ci-api:2.1.0`. |
| `QUICKSTART.md` Operator | Same inspect recipe; `REPLACE_WITH_*` on copy; `supply-chain-release.sh --confirm-push` + **cosign**. |
| `engineering/runbooks/trust-ci-rollout.md` | Same inspect recipe; “put exact image and holdout sha256 values into deployment env and `runtime/policy.json`.” |
| `trust-ci/scripts/supply-chain-release.sh` | Only argv is `--confirm-push`. Requires **cosign**. Always `docker buildx … --push`. |
| `scripts/grok_approve.py --help` | Named action `docker-push`. Local grants never satisfy Trust CI. |
| `AGENTS.md` grant rules | Exact action + resource; no wildcard; production mutation needs a delegated grant. |

Supporting (not invented): `trust-ci/.env.example`, `trust-ci/config/policy.example.json`, `trust-ci/scripts/verify-supply-chain.sh`, `trust-ci/compose.yaml` `runner-loader`, `trust-ci/tests/test_supply_chain.py`, `.grok-stack/adaptive_grok/policy.py` (`docker push` → `docker-push`), change-package `requirements.md` / `architecture.md` / `tasks.md`. Prior local-smoke reports (`analysis-docs_researcher-images.md`, `implementation-images.md`) record that a local `.Id` is **not** this pin.

---

## 1. Real pin vs local Id

Docs split three things. Option 1 is the first of these. Local compose smoke already happened and does **not** count as HANDOFF §3.

| Kind | What it is | Where it may live | Completes HANDOFF §3? |
| --- | --- | --- | --- |
| **Local Id** | `docker image inspect` `.Id` (`sha256:` + 64 hex) after two-file `compose build` **without** `--push` | Evidence only, labeled not a pin | **No** |
| **Local daemon `RepoDigests`** | On Engine 29 may equal `.Id` with **no registry host** (`adaptive-trust-ci-api@sha256:<same as Id>`) | Evidence only | **No** — not pullable; `runner-loader` fails |
| **Real pin** | Registry `name@sha256:<64 hex>` produced by `supply-chain-release.sh --confirm-push` (`containerimage.digest` after `buildx --push`), then `docker pull` + `RepoDigests[0]` matching that string | **Untracked** host `.env` and host `runtime/policy.json` | **Yes**, together with holdout digest, SBOM, scan, CI public key |

HANDOFF §3 (the remaining operational step):

```text
### 3. Build and pin immutable artifacts

Build API, worker, runner, and holdout artifacts. Replace mutable image tags with immutable digests in the deployed server-side policy. Generate and retain:

image digests
policy digest
SBOM
vulnerability scan report
CI public attestation key
holdout bundle digest

Do not commit private keys or production environment files.
```

`requirements.md` acceptance for artifacts:

> Given built API/worker/runner/holdout artifacts, when policy and compose env are written, then every image reference is `name@sha256:<64 hex>` and no mutable tag is used for deploy.

`architecture.md`:

> Example policy may keep an explicit runner-digest placeholder; deployed policy must use a real digest.
>
> On Docker Engine 29 a non-empty `RepoDigests` that equals `.Id` is still not a registry pin. … Never copy that string into `policy.example.json` or `.env.example`.

`tasks.md` still open:

```text
- [ ] Build and pin immutable images and holdout digest (operational; needs registry `docker-push` grant; no invented digests in git).
```

Code that a local Id cannot satisfy (`trust-ci/compose.yaml` `runner-loader`):

```sh
docker pull "$TRUST_CI_RUNNER_IMAGE"
resolved="$(docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{index .RepoDigests 0}}')"
test "$resolved" = "$TRUST_CI_RUNNER_IMAGE"
```

`Policy.sandbox.image` and `TRUST_CI_RUNNER_IMAGE` must be `sha256:<64-hex>` or `name@sha256:<64-hex>` (`trust-ci/src/adaptive_trust_ci/policy.py`, `settings.py`). `REPLACE_WITH_*` is not 64 hex: loading the **example** policy as deployed policy fails closed. A local Id formatted as `adaptive-trust-ci-runner@sha256:<id-hex>` **would** match the regex and is therefore illegal in git even though it parses.

`verify-supply-chain.sh` then requires the three compose env values to equal the signed manifest `images.{api,worker,runner}` (`repository@sha256:…`), `cosign verify`, and `docker pull`. systemd `ExecStartPre` runs that verifier. A local-only image never reaches that path.

---

## 2. Inspect recipe (quoted)

The same three lines appear in `QUICKSTART.md` “Build and pin images”, `trust-ci/README.md` “Build and pin the images”, and `engineering/runbooks/trust-ci-rollout.md` Deploy. Cwd for those blocks is `trust-ci/` after `cd trust-ci`.

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

QUICKSTART immediately after:

> Inspect `$TRUST_CI_*_IMAGE`. Do not inspect `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0` — `compose.build.yaml` does not set those tags for api/worker. Put immutable digests into `.env` and `runtime/policy.json`. Rebuilding the runner or changing policy/holdout changes the policy digest and the required check name.

`trust-ci/README.md` immediately after:

> Inspect `$TRUST_CI_*_IMAGE`; do not inspect `adaptive-trust-ci-api:2.1.0`. Put measured `name@sha256:` values into untracked deploy env and host `runtime/policy.json`. Rebuilding the runner or changing any policy or holdout input changes the policy digest, changes the required check name, and intentionally invalidates old jobs and approvals.

Runbook:

> Put exact image and holdout sha256 values into deployment env and `runtime/policy.json`.

**Operator-doc gap (do not paper over):** those three inspect lines sit **after** a local two-file `compose build` with no `--push`. For option 1 the **deployable** `RepoDigests[0]` is the value **after** `supply-chain-release.sh --confirm-push` (or after `docker pull` of that pin). Indexing `RepoDigests[0]` on a local-only image can look like a pin (Engine 29) and is still not a registry pin. The README sentence that belongs to option 1 is “Put measured `name@sha256:` values into **untracked** deploy env and host `runtime/policy.json`.”

---

## 3. `REPLACE_WITH_*` rule (quoted)

QUICKSTART Operator, after the copy-list:

> Copy templates. Do not commit filled files:

then:

> Replace every `REPLACE_WITH_*` placeholder, including image `name@sha256:` pins in `.env`. `runtime/trust-store.json` stays invalid until a real human public key is inserted.

`trust-ci/README.md` Bootstrap:

> Copy the environment templates. Do not commit the resulting files:
>
> Replace every placeholder.

HANDOFF §3:

> Do not commit private keys or production environment files.

Tracked placeholders that must stay placeholders (from `trust-ci/.env.example`):

```text
TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST
TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:REPLACE_WITH_POSTGRES_DIGEST
TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:REPLACE_WITH_DIND_DIGEST
TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST
TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST
TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST
TRUST_CI_RUNNER_BUILD_TAG=adaptive-trust-ci-runner:2.1.0
TRUST_CI_TEST_BUILD_TAG=adaptive-trust-ci-test:2.1.0
```

`trust-ci/config/policy.example.json`:

```text
"image": "adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST"
```

`tests/test_structure.py` currently allows **either** that placeholder **or** a real `@sha256:[0-9a-f]{64}`. Filling the example with a registry pin would still pass that test. Docs forbid it anyway: examples are templates; pins go in untracked deploy files.

The only committed 64-hex image-adjacent field is example `holdout.digest`, test-locked to `trust-ci/holdout.example`. That is **not** a production holdout pin and is not an image registry pin.

---

## 4. `supply-chain-release.sh` needs cosign + `--confirm-push`

QUICKSTART “Operator-only image release”:

```bash
trust-ci/scripts/supply-chain-release.sh --confirm-push
```

> That script requires host tools **docker**, **trivy**, **syft**, and **cosign**.

Script header (the only accepted argv):

```bash
if [[ "${1:-}" != "--confirm-push" || $# -ne 1 ]]; then
  printf 'usage: %s --confirm-push\n' "$0" >&2
  exit 64
fi
```

Required host tools in the script: `docker`, `python3`, `trivy`, `syft`, **`cosign`**, `sha256sum`, `git`. Missing tool → exit 69.

Required env (no default registry URL):

```text
TRUST_CI_PYTHON_BASE_IMAGE   # must match name@sha256:[0-9a-f]{64}
TRUST_CI_API_REPOSITORY      # registry repo without tag or digest
TRUST_CI_WORKER_REPOSITORY
TRUST_CI_RUNNER_REPOSITORY
TRUST_CI_RELEASE_VERSION
TRUST_CI_POLICY_TEMPLATE
TRUST_CI_SUPPLY_CHAIN_DIR
COSIGN_PRIVATE_KEY           # human-controlled cosign private key path
```

Each image: `docker buildx build … --tag "$repository:$TRUST_CI_RELEASE_VERSION" --push --sbom=true --provenance=mode=max`, pin `repository@containerimage.digest`, Trivy HIGH/CRITICAL `--exit-code 1`, Syft CycloneDX, **`cosign sign --yes --key "$COSIGN_PRIVATE_KEY" "$immutable"`**. Then `cosign sign-blob` on `supply-chain.manifest.json`.

`trust-ci/tests/test_supply_chain.py` asserts the script contains `--push`, `--sbom=true`, `--provenance=mode=max`, `trivy`, `syft`, `cosign sign`, and `confirm-push`.

There is **no** `--no-push` mode. Local two-file compose build is a different path.

`verify-supply-chain.sh` requires **`cosign verify`** + `docker pull` of those three pins. Cosign is optional in `toolchain.json` for the developer laptop; it is **mandatory** on the operator push/verify path.

QUICKSTART scanner pin for Cosign (host install, not a registry): `https://github.com/sigstore/cosign/releases/download/v2.4.3/cosign-linux-amd64`.

---

## 5. Grant rules — `grok_approve.py --help` and `AGENTS.md`

`python3 scripts/grok_approve.py --help`:

```text
usage: grok_approve.py [-h] --reason REASON [--ttl TTL]
                       [--source {standing-user-consent,explicit-user-consent}]
                       [--profile {release}]
                       [--action {git-push-branch,git-push-tag,pull-request-merge,docker-push,npm-publish,github-release,external-write,protected-path-write}]
                       [--resource RESOURCE]
                       {production,external-write,protected-path}

Materialize an explicitly delegated local grant bound to the current
repository, route, change, Git HEAD and tree fingerprint. Local grants never
satisfy external Trust CI approvals.
```

`--action docker-push` is a **production** scope action (`SCOPE_ACTIONS['production']`). `--profile release` is branch push + tag push + GitHub Release only — it does **not** include `docker-push`. `--resource`: “Exact path, tool name, URL, or fnmatch pattern for protected/external grants.”

Python `add_approval` requires resources only for `external-write` and `protected-path` scopes. Production `docker-push` can be stored with an empty resource list. That is weaker than the **docs**.

`AGENTS.md` Local delegated grants:

> `scripts/grok_approve.py` does not originate authority. It materializes explicit or standing user consent already present in the working context.
> Every grant must name explicit actions and, for protected/external writes, explicit resources. It is bound to the current repository, route, change, Git HEAD, tree fingerprint and TTL; any tree or commit change invalidates it.
> An agent may invoke `grok_approve.py` only when the user has explicitly delegated the named operation. The wildcard scope is forbidden.

`AGENTS.md` Prohibited routine actions:

> Merge, publish, tag, deploy, production mutation or external write without an exact delegated local grant naming that operation and resource.

HANDOFF “User standing consent”:

> A local grant may authorize the exact requested push, tag, release, protected-path edit, or external write. It must never create the external Trust CI verdict or substitute for a human-signed Trust CI approval.

`.grok-stack/adaptive_grok/policy.py` `_production_action` returns `docker-push` only for `argv[:2] == ['docker', 'push']`. `docker compose … build` is not gated. `docker buildx build … --push` inside `supply-chain-release.sh` is not the two-token `docker push` form; PreToolUse classification of that script is a hook fact, not a documented API. Operator docs still treat `--confirm-push` as the production image-release command that needs the `docker-push` grant.

Do not mint a grant from this report. Do not use wildcard `*`. If a grant is materialized, docs require `--action docker-push` **and** `--resource` naming the actual registry repository URL/pattern the user delegated. Tracked docs do not contain that URL.

---

## 6. No real registry URL in tracked docs

Grep of tracked product files (`*.md`, `*.json`, `*.yml`/`*.yaml`, `*.example`, scripts, tests) for `registry.example.com`, `ghcr.io`, `quay.io`, `gcr.io`:

| Hit | File | Meaning |
| --- | --- | --- |
| `registry.example.com/adaptive-trust-ci-{api,worker,runner}@sha256:REPLACE_WITH_*` | `trust-ci/.env.example` only | Template host, not a live registry |
| `https://ci.example.com` | `trust-ci/env/common.env.example`, `trust-ci/README.md` webhook/approval URL | Public API placeholder, not a container registry |
| `ghcr.io` / `quay.io` / `gcr.io` / `pkg.dev` / `azurecr.io` / `ecr.aws` | **none** | — |

`TRUST_CI_API_REPOSITORY` / `WORKER` / `RUNNER` have **no** example values in tracked docs. The push script refuses a repository that contains `@` or spaces; it does not default a host.

`docker.io` in QUICKSTART is the Ubuntu package `docker.io docker-compose-v2`, not a Trust CI image registry. Public bases (`python:3.12-slim-bookworm`, `postgres:17.6-bookworm`, `docker:29-dind-rootless`) are Hub library names with `REPLACE_WITH_*` digest suffixes in the example file.

**Recovered fact:** there is no real registry URL to copy. Option 1 cannot proceed until the user names an actual `TRUST_CI_*_REPOSITORY` (and a `docker-push` grant bound to that resource). Inventing `ghcr.io/…` or treating `registry.example.com` as reachable is forbidden.

---

## 7. What would go stale if we pushed but did not update tracked examples

**Answer: nothing that the contract allows to change. Examples must stay placeholders.**

Tracked examples (`.env.example`, `policy.example.json`, QUICKSTART/README inspect copy, `REPLACE_WITH_*`) are operator templates. HANDOFF §3, README Bootstrap, and QUICKSTART all say: copy, fill **off-git**, do not commit production env. A successful registry push writes:

- untracked host `.env` `TRUST_CI_{API,WORKER,RUNNER}_IMAGE=real.registry/…@sha256:<64 hex>`
- untracked host `runtime/policy.json` `sandbox.image` = that runner pin
- untracked `TRUST_CI_SUPPLY_CHAIN_DIR` (SBOM, Trivy JSON, signed manifest)

Those are **not** tracked. Updating tracked examples with the real host or digest would:

- violate “Do not commit … production environment files”
- freeze a deploy pin inside the PR trust domain
- make `test_structure`’s “placeholder **or** 64-hex” branch look like a completed pin
- stale on the next rebuild (HANDOFF/README: rebuild changes the digest and the required check name)

If option 1 lands and someone later “fixes” `.env.example` to the live `name@sha256:`, **that** edit is the stale/wrong move. Leaving `registry.example.com` + `REPLACE_WITH_*` is the required post-push state of git.

What **would** be stale if docs were wrongly treated as the live pin map: nothing in git is supposed to be that map. Operator evidence for HANDOFF §3 belongs in this change package (digest **summaries** labeled as registry pins, no secrets) plus the untracked host files. Do not paste Cosign private key paths or filled `.env` into git.

---

## 8. Ruling for option 1 (registry + docker-push)

Docs already require, and do not invent:

1. A **user-named** registry repository for api/worker/runner (not `registry.example.com`).
2. Exact delegated grant: scope `production`, `--action docker-push`, `--resource` that registry URL/pattern, bound to current repo/route/change/HEAD/fingerprint/TTL. No wildcard. Grant does not create the App-owned check.
3. Host tools including **cosign**. Script argv **exactly** `--confirm-push`.
4. Measured `TRUST_CI_PYTHON_BASE_IMAGE=name@sha256:<64 hex>` (public base), not `REPLACE_WITH_BASE_DIGEST`, in **untracked** env only.
5. Output pins `repository@sha256:<64 hex>` into untracked deploy env + host `runtime/policy.json`. Runner pin must equal `policy.sandbox.image`.
6. Retain SBOM, Trivy report, signed supply-chain manifest, CI public attestation key, holdout digest — HANDOFF §3 retain-list. Holdout still uses the documented external path, not `holdout.example` as production.
7. **Do not** write those hex values into tracked examples. Examples must stay `REPLACE_WITH_*`.
8. Local smoke Ids (`70a80960…` / `bffd013c…` / `900cfaaa…` in `implementation-images.md`) remain `local-image-id, not a registry pin`. Do not reuse them as the option-1 pin.

Blocked without further user input (not missing from docs — missing from the tree):

- real registry URL
- live `docker-push` grant for this route/HEAD/fingerprint
- Cosign key (human-controlled; agent must not generate or read the private key)

Route `f70d038b336f` analysis complete. Write owner is `general_implementer`.
