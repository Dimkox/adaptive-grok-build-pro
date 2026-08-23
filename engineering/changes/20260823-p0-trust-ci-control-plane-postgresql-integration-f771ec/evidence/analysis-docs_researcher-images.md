# Docs research — local build-without-push and image-pin contract

Change: `engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `d2ba49e0570d` (`docs_researcher` allowed; write-owner `general_implementer`)  
Agent: `docs_researcher` (read-only)  
Date: 2026-08-23

This report recovers what the tree already requires for a **local build-without-push**. It does **not** invent APIs, image digests, policy-epoch 12-hex, GitHub App IDs, or Check Run IDs. No `.env`, PEM, App key, webhook secret, or human private key was read. No push, merge, or deploy.

`engineering/adr/` is empty. Machine-readable image contract is Compose interpolation + example env/policy placeholders, not a separate OpenAPI.

## Sources (requested order)

| File | Image-pin / local-build content |
| --- | --- |
| `GROK_BUILD_HANDOFF.md` §3 onward | Remaining operational sequence. Step 3 is **deployed** pin, not a compose recipe. |
| `trust-ci/README.md` | Operator contract: two-file compose build, `$TRUST_CI_*_IMAGE` inspect, untracked pins. |
| `QUICKSTART.md` Operator | Same two-file command; cwd `trust-ci/`; “do not build against `compose.yaml` alone.” |
| `engineering/runbooks/trust-ci-rollout.md` | Same two-file build/inspect; incomplete bootstrap copy-list. |
| `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md` | **No image-pin section.** Task 7 is “Dockerfile, Compose, systemd…”. Tech Stack still says PostgreSQL 16. Task 8 still says “Update product identity to 2.1.0”. |
| `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` | **No artifact-pinning section.** Trusted “deployed Trust CI container image”; policy digest; rollout is status-publication, not `name@sha256`. |
| `trust-ci/scripts/supply-chain-release.sh` | Operator **push** path only: `usage: … --confirm-push`. Always `docker buildx build … --push`. |
| `trust-ci/scripts/verify-supply-chain.sh` | Verifies signed `name@sha256:` pins already in env + policy; `docker pull`; not a local build. |
| Change package `tasks.md` / `requirements.md` / `release.md` / `rollback.md` | Task 9 still open: local build-without-push only after docs verify; no invented digests in git. |
| `evidence/implementation-resume.md`, `evidence/code-review-resume.md` | K16/two-file landed. RepoDigests empty until registry push. |

Supporting (not invented): `Makefile`, `trust-ci/compose.yaml`, `trust-ci/compose.build.yaml`, `trust-ci/compose.test.yaml`, `trust-ci/.env.example`, `trust-ci/config/policy.example.json`, `.grok-stack/adaptive_grok/policy.py` (`docker push` is `docker-push`; `docker compose … build` is not).

---

## 1. What local build-without-push already is

Local compile of API/worker/runner images is the **two-file Compose merge**. It is **not**:

- `docker compose --profile build build` against `compose.yaml` alone (`compose.yaml` has **no** `build:`);
- `make trust-ci-build` (that target **does not exist**);
- `trust-ci/scripts/supply-chain-release.sh` (requires `--confirm-push` and always `--push`);
- writing a digest into git (`REPLACE_WITH_*` stays in examples);
- completing handoff §3 (that step pins **deployed** policy/env).

`tasks.md` still open:

```text
- [ ] Build and pin immutable images and holdout digest (operational; local build-without-push only after docs verify; no invented digests in git).
```

`requirements.md` acceptance for artifacts:

> Given built API/worker/runner/holdout artifacts, when policy and compose env are written, then every image reference is `name@sha256:<64 hex>` and no mutable tag is used for deploy.

`implementation-resume.md` residual:

> Image pin, GitHub App, deploy, `docker push`, and merge were **not** started. A later build-without-push smoke still cannot pin (`RepoDigests` empty until registry push).

`analysis-architect-resume.md` §5.2 (still the ruling after the docs pass):

- `policy.py` `_production_action` gates `docker push`, not `docker compose … build`. Local two-file build is not a named production action.
- `compose.build.yaml` requires `TRUST_CI_PYTHON_BASE_IMAGE` as `name@sha256:<64 hex>`. `.env.example` still has `REPLACE_WITH_BASE_DIGEST`. Inventing that hex is forbidden.
- `docker image inspect "$TRUST_CI_*_IMAGE"` `RepoDigests` is empty until a registry push/load. Local image **Id** is not a deployable `name@sha256:` pin. `policy.example.json` runner digest must stay `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`.
- Measure a real `python:3.12-slim-bookworm` digest from the registry (not invented) and two-file `compose build` **without** `push` is **conditionally** a host smoke compile. Record image Ids in **evidence**, not as committed pins.
- Handoff §3 is **not** completed by a local build-without-push.

Handoff §3 (the remaining operational step, not a local compose recipe):

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

SBOM / Trivy / Cosign are produced by `supply-chain-release.sh --confirm-push`, not by the two-file `compose build`.

---

## 2. Exact commands the operator docs already require

Cwd for QUICKSTART / `trust-ci/README.md` Bootstrap / runbook Deploy: **`trust-ci/`** after `cd trust-ci`.

Cwd for `trust-ci/README.md` Verification and Makefile: **repository root** (`trust-ci/` prefixes).

### 2.1 Two-file compose merge (local build)

From `trust-ci/` (QUICKSTART, `trust-ci/README.md` Bootstrap, runbook):

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
```

From repository root (`trust-ci/README.md` Verification):

```bash
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image
```

Makefile two-file **config** (not a build; not in `.PHONY`):

```make
docker-compose-build-config:
	docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config
```

There is **no** Makefile target that runs the two-file `--profile build build`.

### 2.2 Inspect `$TRUST_CI_*_IMAGE` (and RepoDigests)

Same three lines in QUICKSTART, `trust-ci/README.md`, and the runbook:

```bash
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
```

Production `runner-loader` in `trust-ci/compose.yaml` uses the same field and **requires** it to equal the pin after `docker pull`:

```sh
docker pull "$TRUST_CI_RUNNER_IMAGE"
resolved="$(docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{index .RepoDigests 0}}')"
test "$resolved" = "$TRUST_CI_RUNNER_IMAGE"
```

That check cannot succeed on a local-only image with empty `RepoDigests`.

### 2.3 Do not inspect `adaptive-trust-ci-api:2.1.0`

`compose.build.yaml` facts (do not invent other tags):

| Service | Dockerfile | `image:` in build override |
| --- | --- | --- |
| `migrate` / `api` | `Dockerfile.api` | none (production `image:` is `${TRUST_CI_API_IMAGE:?…}`) |
| `worker` | `Dockerfile.worker` | none (`${TRUST_CI_WORKER_IMAGE:?…}`) |
| `runner-image` (`profiles: ["build"]`) | `runner.Dockerfile` | `${TRUST_CI_RUNNER_BUILD_TAG:-adaptive-trust-ci-runner:2.1.0}` |

QUICKSTART:

> Inspect `$TRUST_CI_*_IMAGE`. Do not inspect `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0` — `compose.build.yaml` does not set those tags for api/worker. Put immutable digests into `.env` and `runtime/policy.json`. Rebuilding the runner or changing policy/holdout changes the policy digest and the required check name.

`trust-ci/README.md`:

> Inspect `$TRUST_CI_*_IMAGE`; do not inspect `adaptive-trust-ci-api:2.1.0`. Put measured `name@sha256:` values into untracked deploy env and host `runtime/policy.json`. Rebuilding the runner or changing any policy or holdout input changes the policy digest, changes the required check name, and intentionally invalidates old jobs and approvals.

QUICKSTART also:

> Commands below match the Makefile; do not build against `compose.yaml` alone.

Stale `docker compose --profile build build` against `compose.yaml` alone, `compose.yaml build api worker`, and inspect of `adaptive-trust-ci-api:2.1.0` as a **command** are gone from product docs. Remaining mentions of that tag are the **do not inspect** warnings.

### 2.4 Do not commit invented digests

Tracked placeholders that must stay placeholders:

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

Handoff §3: “Do not commit private keys or production environment files.”  
`trust-ci/README.md` Bootstrap: “Copy the environment templates. Do not commit the resulting files.”  
`code-review-resume.md`: “Example pins stay `REPLACE_WITH_*`.”  
`implementation-resume.md`: “Example policy/env still use `REPLACE_WITH_*` placeholders. No digest was invented or committed.”

None of the operator docs contain a real API/worker/runner/policy digest. Pins go in **untracked** `.env` / host `runtime/policy.json`.

### 2.5 Holdout digest (not an image; three documented paths)

Do not collapse these into one invented path:

| Source | Command |
| --- | --- |
| `trust-ci/README.md` | `adaptive-trust-ci holdout-digest --path /opt/adaptive-trust-ci-holdout` |
| `QUICKSTART.md` (cwd `trust-ci/`) | `PYTHONPATH=src python3 -m adaptive_trust_ci.cli holdout-digest --path /absolute/reviewed/holdout` |
| `Makefile` (repo root) | `PYTHONPATH=trust-ci/src python3 -m adaptive_trust_ci.cli holdout-digest --path trust-ci/holdout.example` |

### 2.6 Live harness vs production image build

These are **not** the production two-file image build. `compose.test.yaml` builds `postgres-integration` from `Dockerfile.test` (default tag `adaptive-trust-ci-test:2.1.0`) and still interpolates `TRUST_CI_POSTGRES_IMAGE` + `TRUST_CI_PYTHON_BASE_IMAGE` as immutable digests.

From repository root:

```bash
make trust-ci-postgres-test
# or
./trust-ci/scripts/postgres-integration.sh
./trust-ci/scripts/postgres-restart-drill.sh
```

Makefile `trust-ci-postgres-test` (and the script) use `--exit-code-from postgres-integration`. There is **no** service named `tests`.

### 2.7 Operator push path (not local build-without-push)

QUICKSTART:

```bash
trust-ci/scripts/supply-chain-release.sh --confirm-push
```

Script header:

```bash
if [[ "${1:-}" != "--confirm-push" || $# -ne 1 ]]; then
  printf 'usage: %s --confirm-push\n' "$0" >&2
  exit 64
fi
```

Required host tools: `docker`, `python3`, `trivy`, `syft`, `cosign`, `sha256sum`, `git`. Required env: `TRUST_CI_PYTHON_BASE_IMAGE` (must match `name@sha256:[0-9a-f]{64}`), `TRUST_CI_API_REPOSITORY` / `WORKER` / `RUNNER` (registry repo **without** tag or digest), `TRUST_CI_RELEASE_VERSION`, `TRUST_CI_POLICY_TEMPLATE`, `TRUST_CI_SUPPLY_CHAIN_DIR`, `COSIGN_PRIVATE_KEY`.

Each image: `docker buildx build … --tag "$repository:$TRUST_CI_RELEASE_VERSION" --push --sbom=true --provenance=mode=max`, then pin `repository@containerimage.digest`, Trivy HIGH/CRITICAL, Syft CycloneDX, `cosign sign`.

`verify-supply-chain.sh` then requires those three `name@sha256:` values to match signed manifest, deployed policy runner image, and `TRUST_CI_API_IMAGE` / `TRUST_CI_WORKER_IMAGE` / `TRUST_CI_RUNNER_IMAGE` in compose env, then `cosign verify` + `docker pull`.

`scripts/grok_approve.py` action list includes `docker-push`. `_production_action` returns `docker-push` only for `argv[:2] == ['docker', 'push']`.

### 2.8 Start is deploy, not build

QUICKSTART:

```bash
docker compose -f compose.yaml up -d postgres migrate api worker
```

`trust-ci/README.md` / runbook:

```bash
docker compose up -d postgres migrate api worker
```

QUICKSTART: manual `up` of those four is enough to exercise API readiness; jobs that need a runner require systemd (`docker-engine` + `runner-loader` after `verify-supply-chain.sh`). That is **not** local build-without-push.

---

## 3. What would make the docs stale if scripts / Makefile change

Product docs copy these **Makefile** and **script** surfaces. Changing them without a matching doc edit leaves a stale map.

| Code surface today | Docs that copy it | Change that would stale docs |
| --- | --- | --- |
| No `make trust-ci-build`; two-file `compose build` is documented as compose, not make | QUICKSTART “Commands below match the Makefile”; prior analysis “do not invent `make trust-ci-build`” | Adding `trust-ci-build` (docs would under-claim make); renaming/removing the two-file command (docs would over-claim make) |
| `docker-compose-build-config` two-file `config`, **not** in `.PHONY` | `trust-ci/README.md` Verification uses two-file **build** + production-only `compose.yaml config` (`trust-ci-compose`) | Merging build into `trust-ci-compose`, or documenting `make docker-compose-build-config` then deleting the target |
| `trust-ci-postgres-test` → `--exit-code-from postgres-integration postgres-integration` + `down -v` trap | QUICKSTART, `trust-ci/README.md`, runbook | Renaming service `postgres-integration`, dropping `--build`, or changing `compose.test.yaml` |
| `./trust-ci/scripts/postgres-integration.sh` same `--exit-code-from postgres-integration` | QUICKSTART | Same |
| `trust-ci-holdout-digest` → `PYTHONPATH=trust-ci/src` + `trust-ci/holdout.example` | Makefile vs QUICKSTART `/absolute/reviewed/holdout` vs README `/opt/adaptive-trust-ci-holdout` | Changing the example path or collapsing the three paths |
| `trust-ci-test` `PYTHONPATH=trust-ci/src` (no `trust-ci/tests`); `trust-ci-compile` includes `trust-ci/tests` | `trust-ci/README.md` Verification uses `PYTHONPATH=trust-ci/src:trust-ci/tests` and `compileall` **only** `trust-ci/src` | Aligning Makefile to README or vice versa without editing the other |
| `supply-chain-release.sh` usage is **only** `--confirm-push`; always `--push` | QUICKSTART “Operator-only image release” | Adding `--no-push` / local metadata-only mode without updating QUICKSTART; changing required tools (`trivy`, `syft`, `cosign`) |
| `verify-supply-chain.sh` requires exactly `{api,worker,runner}` `name@sha256:[0-9a-f]{64}` matching compose env + policy `sandbox.image` | systemd `ExecStartPre`; QUICKSTART “starts … after `verify-supply-chain.sh`” | Extra image keys, tag-only refs, or skipping `docker pull` |
| `compose.build.yaml` does not tag api/worker `*:2.1.0` | “Do not inspect `adaptive-trust-ci-api:2.1.0`” | Adding those tags would make the warning false; removing `runner-image` local tag would stale `TRUST_CI_RUNNER_BUILD_TAG` |
| `compose.yaml` has **no** `build:` | “do not build against `compose.yaml` alone” | Putting `build:` back into production compose |
| `runner-loader` `RepoDigests[0] == TRUST_CI_RUNNER_IMAGE` after pull | inspect format `{{index .RepoDigests 0}}` | Switching to `.Id` / `RepoDigest` elsewhere |
| `_production_action` gates `docker push` only | architect resume: local compose build is not a production action | Classifying `docker compose … build` or `buildx --push` as `docker-push` without a grant/doc update |
| Optional toolchain ids `docker`/`syft`/`trivy`/`cosign` `required: false` | QUICKSTART scanner installs; README Requirements | Making docker required, adding `grype`, or a standalone `docker-compose` tool id |

QUICKSTART scanner pins that would stale if doctor/install scripts change: Docker Engine `docker.io docker-compose-v2`; Syft `https://get.anchore.io/syft`; Trivy `v0.74.0`; Cosign `v2.4.3`. Grype is “not a product pin, not in `toolchain.json`”.

---

## 4. Remaining documentation contradictions after the K16 / two-file resume

The **two-file build command itself is now consistent** across QUICKSTART, `trust-ci/README.md`, and the runbook. Stale `compose.yaml`-alone build and `--exit-code-from tests` are gone from product docs (`code-review-resume.md` PASS). Remaining contradictions/gaps:

### 4.1 Local inspect is documented as if it produced a deployable pin

Operator docs tell the operator to two-file `compose build` (no `--push`) and then `inspect … {{index .RepoDigests 0}}` and “put immutable / measured `name@sha256:` values” into `.env` and `runtime/policy.json`.

Evidence after K16 (`implementation-resume.md`, `code-review-resume.md` residual 5, `analysis-architect-resume.md` §5.2): **`RepoDigests` is empty until a registry push/load. Local `.Id` is not a deployable pin.** Production `runner-loader` will fail the `test "$resolved" = "$TRUST_CI_RUNNER_IMAGE"` check on an unpushed image.

**None of QUICKSTART / `trust-ci/README.md` / the runbook state that `RepoDigests` is empty after a local-only build.** That is the remaining operator-doc vs contract contradiction for build-without-push.

### 4.2 “Commands below match the Makefile” over-claims

QUICKSTART: “Commands below match the Makefile; do not build against `compose.yaml` alone.”

Makefile matches `trust-ci-postgres-test` / `--exit-code-from postgres-integration`. The **build** command is compose-only. `docker-compose-build-config` is not `.PHONY` and is not named in QUICKSTART. If a reader looks for `make … build`, they will not find it.

### 4.3 Runbook bootstrap copy-list still short

`code-review-resume.md` residual 1 (still true in the runbook file):

> `engineering/runbooks/trust-ci-rollout.md` bootstrap copy list still omits `.env.example`, `migration.env.example`, and `backup.env.example`. QUICKSTART and `trust-ci/README.md` include them. `compose.yaml` `migrate` requires `env/migration.env`. Copy-paste of the runbook-only bootstrap is incomplete; the two-file merge itself is correct.

Runbook Deploy still:

```bash
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/postgres.env.example env/postgres.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
```

### 4.4 Handoff §3–9 was not updated in the two-file resume

- Handoff §3 never names `-f compose.yaml -f compose.build.yaml` and treats local “build and pin” as completing deployed pins + SBOM + scan. Operator tree splits that: compose build (local) vs `supply-chain-release.sh --confirm-push` (registry) vs host policy.
- Handoff “Fresh local verification already recorded” still says “PostgreSQL live integration tests: 4 skipped because `TRUST_CI_TEST_DATABASE_URL` was unavailable”. `tasks.md` already checks live 8/8 + restart drill PASS. `engineering/reviews/trust-ci-p0-local-verification.md` still has the four-skipped paragraph.
- Handoff §6 “Update PR #2” / §9 “Finish PR #2” still frames the first proof as the draft product PR. QUICKSTART: “Prove the App-owned check first on a disposable docs PR (draft or not). Do not treat a draft as the first live proof of branch protection.” Code enqueues drafts (K16 resume removed “Draft PRs are ignored”).

### 4.5 Design spec / implementation plan vs the tree (pre-existing; not fixed by K16)

- Plan Tech Stack: “PostgreSQL 16”. Tree / README / QUICKSTART: PostgreSQL 17 / `postgres:17.6-bookworm`.
- Plan Task 8: “Update product identity to 2.1.0”. Tree: product `VERSION` / README H1 **2.0.11**; Trust CI package **2.1.0** as a separate identity sentence.
- Spec GitHub integration: “publish the status context `adaptive-trust-ci/verified`”. Current contract: App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>` bound to App ID.
- Spec trusted set: “the deployed Trust CI container image” (singular). Tree: separate API, worker, runner, postgres, dind images, all digest-pinned at deploy.
- Spec/plan have **no** two-file compose, `RepoDigests`, or `REPLACE_WITH_*` pin recipe. Do not treat them as the image-pin authority.

### 4.6 Small remaining dialect (not command-wrong)

- QUICKSTART start uses `docker compose -f compose.yaml up …`; README/runbook use `docker compose up …` after `cd trust-ci`. Equivalent if cwd is `trust-ci/` and that is the project compose file.
- QUICKSTART “do not inspect” names **api and worker** `:2.1.0`; `trust-ci/README.md` names **api** only. Both are true (`runner-image` *does* default to `adaptive-trust-ci-runner:2.1.0`).
- `trust-ci/README.md` Verification keeps `docker compose -f trust-ci/compose.yaml config` (Makefile `trust-ci-compose`) **and** the two-file build. That matches architect-resume, not the earlier docs_researcher-resume which wanted two-file `config` in that block. Both Makefile targets exist; this is dialect, not a broken command.

### 4.7 Change-package release.md

`release.md` is still the empty template (`## Deployment` with no commands). It does not contradict the two-file recipe because it states nothing. Rollback.md correctly says deployed images/policy/holdout roll back to previous **reviewed digests** and that a policy/holdout rollback changes the epoch.

---

## 5. Ruling for the next write slice

Local build-without-push, as the docs already require:

1. Do **not** invent or commit `sha256:` values. Leave `REPLACE_WITH_*`.
2. Do **not** inspect `adaptive-trust-ci-api:2.1.0` / `adaptive-trust-ci-worker:2.1.0`.
3. Merge **both** compose files: `-f compose.yaml -f compose.build.yaml --profile build build api worker runner-image`.
4. Inspect `"$TRUST_CI_*_IMAGE"` `.Id` and `RepoDigests[0]`.
5. Treat empty `RepoDigests` after a no-push build as **expected**, not as a license to paste a fake digest into git. Record Ids in evidence only.
6. Do **not** run `supply-chain-release.sh` without `--confirm-push` (the script refuses any other argv) and do not run `--confirm-push` without an exact `docker-push` grant.
7. Handoff §3 (deployed pin + SBOM + scan + host policy) is still **open** after a successful local smoke.

If `scripts/` or `Makefile` grow a `trust-ci-build` target, a `--no-push` supply-chain mode, api/worker `:2.1.0` tags, or a renamed `postgres-integration` service, the operator docs quoted above become stale on that same day.

Route `d2ba49e0570d` analysis complete. Write owner is `general_implementer`.
