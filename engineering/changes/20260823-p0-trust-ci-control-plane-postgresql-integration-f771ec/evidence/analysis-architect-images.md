# Analysis — architect (local image build-without-push)

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `d2ba49e0570d` · write=`general_implementer` · reviews=`code_reviewer`+`test_reviewer`  
HEAD: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Human gates on this route: none. Record this design and continue. Do not reopen product design.

Read-only. No product-file edits from this agent. No `.env`, keys, push, merge, deploy, GitHub App, or image push. Did not read `trust-ci/runtime/github-app-private-key.pem` (present, gitignored).

Narrow question: bounded next slice for **local image build-without-push** — evidence vs git, compose tags / honest inspect, fail-closed against fake tracked digests, holdout, out-of-slice ops, and whether to commit the docs tree first.

Disagree with two prior facts and keep the rest:

| Prior claim | This host / tree |
| --- | --- |
| `RepoDigests` is empty until registry push | **False on Docker Engine 29.7.2.** Leftover local images already have `RepoDigests[0] == name@sha256:<same hex as .Id>` with **no registry host**. That string matches `_IMAGE_DIGEST_RE` and would pass `Policy.sandbox.image`. It is **not** a pullable pin. |
| Copy `trust-ci/.env.example` → `trust-ci/.env` for smoke, no grant | **Blocked.** `.env` / `**/.env` / `trust-ci/**` are protected paths. Prefer an env-file **outside** the repo. |

---

## Ruling (one screen)

**Freeze the reviewed docs tree. Run a local two-file compose *build* with no push and no `up`. Record Ids as evidence. Do not complete handoff §3. Do not write any digest into git.**

Handoff §3 (“pin immutable artifacts in **deployed** server-side policy” + SBOM + scan + CI public key + holdout digest) is **not** this slice. A local smoke cannot produce a registry pin. Example files stay `REPLACE_WITH_*`. Product identity stays **2.0.11**; Trust CI stays **2.1.0**.

| Confirm | Rule |
| --- | --- |
| Tracked examples | Keep every `REPLACE_WITH_*`. Holdout example digest already locked to `trust-ci/holdout.example` is the **only** committed 64-hex image-adjacent field. |
| Untracked smoke env | `/tmp` (or `$XDG_RUNTIME_DIR`) env-file, **not** `trust-ci/.env`. Local API/worker/runner values are **mutable tags**, not `name@sha256:`. |
| Inspect | After **this** build: `.Id` + `json .RepoTags` + `json .RepoDigests`. Do not inspect leftover `adaptive-trust-ci-api:2.1.0` from a previous daemon. Do not treat `RepoDigests[0]` as a pin because it equals `.Id`. |
| Makefile / `supply-chain-release.sh` | **Do not add** `make trust-ci-build` this slice (docs would go stale; protected grant). **Do not run** `--confirm-push`. Fail-closed = `git diff --exit-code` on example files. |
| Holdout | Example bundle only. `/srv`, `/opt`, `/etc` holdout paths are **absent**. Production digest waits. |
| Docs commit | **Yes, isolate it.** Do not mix smoke dirt with the K16/toolchain diff. |
| Out of slice | Registry push, GitHub App, `compose up`, TLS webhook, `branch-protect`, merge. |

---

## 1. Valid local evidence vs illegal git

### 1.1 May exist, must not be committed

| Artifact | Where | Why |
| --- | --- | --- |
| Untracked compose env with **measured** public-base `name@sha256:` (python, optionally postgres/dind) and **mutable** local API/worker/runner tags | `/tmp/adaptive-trust-ci-build.env` (preferred) or gitignored `trust-ci/.env` **only if** a new `protected-path-write` names that exact resource | Compose interpolation. Not a pin. |
| Local image `.Id` (`sha256:` + 64 hex) | `trust-ci/runtime/build-smoke/*.txt` (covered by `trust-ci/runtime/*`) | Daemon compile proof. |
| `.RepoTags` / `.RepoDigests` JSON dump labeled `local-daemon-descriptor, not a registry pin` | same gitignored dir | Honesty. On this engine RepoDigests is **not** empty. |
| Optional Syft/Trivy of those local tags | `trust-ci/runtime/build-smoke/` | Handoff §3 retain-list, but **not** the signed supply-chain bundle. |
| Commands, SHA, pass/fail, “not a pin” | `engineering/changes/…-f771ec/evidence/implementation-images.md` | Tracked **summary** only. If an Id is quoted, label `local-image-id, not a registry pin` and do **not** write `name@sha256:<id>`. |

`.gitignore` already ignores `.env`, `trust-ci/runtime/*` (except `.gitkeep`), `*.pem`. It does **not** ignore a `trust-ci/sbom/` or change-package binary dump; do not put CycloneDX/Trivy JSON there.

### 1.2 Must stay placeholders (illegal in git if filled)

```text
trust-ci/.env.example          REPLACE_WITH_{BASE,POSTGRES,DIND,API,WORKER,RUNNER}_DIGEST
trust-ci/config/policy.example.json   sandbox.image = …@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST
trust-ci/env/*.example         secrets / App IDs / webhook
trust-ci/config/trust-store.example.json
```

`Policy.from_dict` **rejects** the example runner image (placeholder is not 64 hex). That is fail-closed for deploying the example unchanged. `tests/test_structure.py::test_trust_ci_policy_uses_immutable_sandbox_and_external_status` currently allows **either** the placeholder **or** a real `@sha256:[0-9a-f]{64}`. Pasting a local Id / leftover RepoDigest into `policy.example.json` would **pass** that test. Do not do it. Do not “fix” the test in this smoke slice (that is a product change + grant + review wave).

### 1.3 Already committed and allowed (do not change)

`policy.example.json` `holdout.digest` = `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`, locked by `test_ops.test_example_holdout_digest_matches_example_bundle` to `trust-ci/holdout.example`. That is the **example** bundle hash, not a production holdout pin.

### 1.4 Never in git, never read by this slice

`trust-ci/.env`, `trust-ci/env/*.env`, `trust-ci/runtime/policy.json`, `trust-ci/runtime/trust-store.json`, `*.pem` (a `github-app-private-key.pem` already sits in `runtime/`), webhook secret, App ID, human private key, Cosign private key, `COSIGN_PRIVATE_KEY`.

Do not invent a policy digest from a policy that still contains `REPLACE_WITH_*` or a local image Id.

---

## 2. How `compose.build.yaml` tags — honest local inspect

Production `compose.yaml` has **no** `build:` keys. The override adds them.

| Service | Build dockerfile | `image:` in override | Tag actually applied on two-file `build` |
| --- | --- | --- | --- |
| `migrate` / `api` | `Dockerfile.api` | none | **Inherited** from compose.yaml: `${TRUST_CI_API_IMAGE:?…}` |
| `worker` | `Dockerfile.worker` | none | `${TRUST_CI_WORKER_IMAGE:?…}` |
| `runner-image` (`profiles: ["build"]`) | `runner.Dockerfile` | `${TRUST_CI_RUNNER_BUILD_TAG:-adaptive-trust-ci-runner:2.1.0}` | that local tag **and** `${TRUST_CI_RUNNER_IMAGE}` if compose merge keeps both |

There is **no** `image: adaptive-trust-ci-api:2.1.0` in the override. Docs are right that inspecting that name as if compose.build.yaml produced it is the wrong *contract*. This **daemon** nevertheless already has leftover:

```text
adaptive-trust-ci-api:2.1.0     Id=sha256:9b957043dc6e…  RepoDigests=["adaptive-trust-ci-api@sha256:9b957043dc6e…"]
adaptive-trust-ci-worker:2.1.0  Id=sha256:ef58751c8ae5…  RepoDigests=["adaptive-trust-ci-worker@sha256:ef58751c8ae5…"]
adaptive-trust-ci-runner:2.1.0  Id=sha256:8ceb98cdb78a…  RepoDigests=["adaptive-trust-ci-runner@sha256:8ceb98cdb78a…"]
python:3.12-slim-bookworm       Id=sha256:a116514e1945…  RepoDigests=["python@sha256:a116514e1945…"]
```

Those leftover Trust CI tags are **stale relative to current source** until **this** smoke rebuilds them. `RepoDigests[0]` equals `.Id` and has **no registry**. Copying that string into policy/env is a fake pin. `runner-loader` does `docker pull` then `test "$resolved" = "$TRUST_CI_RUNNER_IMAGE"`; a local-only descriptor will not survive a clean daemon or another host.

`python@sha256:…` **is** a measured Hub digest (image was pulled). It may be written only into the **untracked** smoke env-file as `TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:<measured>`. Re-`docker pull` then inspect; do not copy a hex from this report into git.

### 2.1 Honest local command (cwd `trust-ci/` **or** `--env-file` from repo root)

Do **not** leave `TRUST_CI_API_IMAGE=registry.example.com/…@sha256:REPLACE_WITH_API_DIGEST` during build: that is not a valid local tag target. Untracked smoke env:

```text
TRUST_CI_PYTHON_BASE_IMAGE=<measured python:3.12-slim-bookworm@sha256:64hex after docker pull>
TRUST_CI_POSTGRES_IMAGE=<placeholder from .env.example is enough for build; optional measured pin>
TRUST_CI_DIND_IMAGE=<same>
TRUST_CI_API_IMAGE=adaptive-trust-ci-api:2.1.0          # mutable local tag, not a pin
TRUST_CI_WORKER_IMAGE=adaptive-trust-ci-worker:2.1.0
TRUST_CI_RUNNER_IMAGE=adaptive-trust-ci-runner:2.1.0
TRUST_CI_RUNNER_BUILD_TAG=adaptive-trust-ci-runner:2.1.0
TRUST_CI_HOLDOUT_SOURCE_PATH=/srv/adaptive-trust-ci/holdout   # interpolation only; path is absent
```

Build (no push, no up):

```bash
docker compose --env-file /tmp/adaptive-trust-ci-build.env \
  -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml \
  --profile build build api worker runner-image
```

Honest inspect **after that build**, of the tags the env-file actually used:

```bash
docker image inspect adaptive-trust-ci-api:2.1.0 \
  --format '{{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
docker image inspect adaptive-trust-ci-worker:2.1.0 \
  --format '{{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
docker image inspect adaptive-trust-ci-runner:2.1.0 \
  --format '{{.Id}} tags={{json .RepoTags}} digests={{json .RepoDigests}}'
```

Use `{{json .RepoDigests}}`, not `{{index .RepoDigests 0}}`. Indexing a present local descriptor looks like a pin. Operator docs that inspect `"$TRUST_CI_*_IMAGE"` are the **deploy** recipe (registry pin already in host env). This smoke must say in evidence: **local tag inspect; RepoDigests on Engine 29 may be a local descriptor; not a pin.**

Do not `docker compose up`. `compose.yaml` binds `127.0.0.1:8080:8080`; this host already listens there (searxng). Build does not bind the port.

`FROM ${PYTHON_BASE_IMAGE}` requires a **real** python digest. Postgres/dind `:?` vars only need to be non-empty for this build. Measure python. Measuring postgres/dind is optional noise unless the write owner wants them recorded as public-base evidence.

---

## 3. Script / Makefile — fail-closed against fake tracked digests

**Not this slice.**

`docs_researcher-images.md` already warns: adding `make trust-ci-build` would stale QUICKSTART (“commands match the Makefile”) and the “do not invent `make trust-ci-build`” analysis. `Makefile` and `trust-ci/**` and `tests/test_*.py` are protected. Grant `762816e981e59918` is consumed. A Makefile/test change forces `grok_verify` + both reviewers.

Fail-closed **this turn** (no product edit):

```bash
git diff --exit-code -- \
  trust-ci/config/policy.example.json \
  trust-ci/.env.example \
  trust-ci/env \
  trust-ci/config/trust-store.example.json
git ls-files -o --exclude-standard | grep -E '\.env$|runtime/policy|REPLACE_WITH' && exit 1 || true
```

Refuse to write those files. Do not add `--no-push` to `supply-chain-release.sh` (it is push-only by design; `_production_action` already gates `docker push`).

**Next product slice (after the docs commit, separate grant):** tighten `test_trust_ci_policy_uses_immutable_sandbox` to **placeholder-only** for `policy.example.json` `sandbox.image`, and assert `.env.example` image lines still contain `REPLACE_WITH_` and do not contain `[0-9a-f]{64}`. That is the durable lock. Optional `make trust-ci-build-local` only if docs are updated the same day.

---

## 4. Holdout digest — wait for a reviewed external bundle

| Path | Status |
| --- | --- |
| `trust-ci/holdout.example/` | In-tree **template**. Digest already in example policy + unit test. A PR can mutate it; it cannot be the trusted external bundle. |
| `/srv/adaptive-trust-ci/holdout` (`.env.example`) | **ABSENT** |
| `/opt/adaptive-trust-ci-holdout` (README/runbook) | **ABSENT** |
| `/etc/adaptive-trust-ci/holdout` (in-worker path in example policy) | **ABSENT** |

Do not install a host copy this slice. Do not invent a production digest. Do not collapse the three documented paths.

`make trust-ci-holdout-digest` runs `python3 -m adaptive_trust_ci.cli`, which imports FastAPI via `cli.py`. Default host Python here has **no** `fastapi` (`ModuleNotFoundError` on that CLI). Honest check:

```bash
PYTHONPATH=trust-ci/src python3 -m unittest \
  trust-ci.tests.test_ops.OperationsTests.test_example_holdout_digest_matches_example_bundle
```

Do not “fix” the CLI import graph in this slice.

---

## 5. Out of slice — push, App, deploy, TLS, branch protection

| Action | Why out |
| --- | --- |
| `docker push` / `supply-chain-release.sh --confirm-push` | Named `docker-push` production action; only source of a **registry** digest; needs an explicit registry URL + grant. Script always `--push`. |
| Pin `name@sha256:` into host `runtime/policy.json` / compose env | Deployed trust domain, outside the PR. Impossible until a registry digest exists. |
| GitHub App create/install, webhook secret, App RSA | Browser/manifest; worker-only key; API-only secret. Do not invent IDs. Do not read leftover `runtime/*.pem`. |
| `docker compose up`, systemd, `/health/ready` | Deploy. Port **8080 already bound** on `127.0.0.1`. Architecture: pick a free loopback + HTTPS proxy later. |
| TLS GitHub webhook | HTTP-only intake is forbidden. No in-tree proxy. |
| `branch-protect` | Only after an App-owned check exists on an exact SHA. Admin token is human-only. |
| Update/merge draft `#2` | `git-push-branch` / merge after commit + live check. Not this smoke. |
| Human Ed25519 `approval-create` | Private key stays off this environment. |

`docker compose … build` is **not** `_production_action`. If PreToolUse still classifies it as “control-plane shell mutation” (this session blocked `docker compose config` with `TRUST_CI_*` exports), **stop and request an exact grant**. Do not bypass with python/tee. Do not skip ahead to GitHub App.

---

## 6. Architectural blocker — commit / freeze docs first

**Yes. Do not mix image-smoke dirt with the K16 docs diff.**

Working tree vs `5915b56` is already the independently reviewed docs/toolchain slice (`code-review-resume.md` + `test-review-resume.md` PASS; change `state.json` `ready`):

```text
README.md  trust-ci/README.md  QUICKSTART.md
.grok-stack/config/toolchain.json
tests/test_structure.py  tests/test_toolchain.py
engineering/runbooks/trust-ci-rollout.md
decisions.md  mistakes.md
engineering/changes/…-f771ec/{state.json,tasks.md}
```

Mixing is a blocker because:

1. Smoke needs an untracked env-file and may write `trust-ci/runtime/build-smoke/`. `git add -A` would be the failure mode (fake digest, `.env`, PEM, SBOM).
2. Any product-file touch after those reviews **invalidates** fingerprint-bound receipts (AGENTS.md). Makefile/tests/compose tag edits are product touches.
3. If the build fails, the docs slice must remain a clean, already-reviewed commit — not a half-smoke tree.
4. Leftover untracked `engineering/changes/20260817-вычисти*` must stay unstaged (prior ruling).
5. Identity: do not bump `VERSION` `2.0.11` or collapse Trust CI `2.1.0`.

Sequence:

1. **Isolate docs:** either commit the reviewed docs set now (no smoke files, no `20260817-*`) **or** freeze those files (`git diff --exit-code` on them after smoke). Prefer a docs-only commit **before** creating the tmp env-file if the user wants a local commit this session. Commit does not need a grant; `git push` does — do not push unless a later grant names the post-commit SHA.
2. **Smoke** with `/tmp` env-file, two-file build, inspect, example-holdout unittest, `git diff --exit-code` on examples.
3. **Evidence only:** `evidence/implementation-images.md`. If product files were not edited, skip a new analysis/review wave (`AGENTS.md` skip no-op). If they were edited, `grok_verify --mode pr` then both reviewers.

Do not bind 8080. Do not `compose up`.

---

## Return block (write owner = `general_implementer`)

1. Do not edit `README.md`, `trust-ci/README.md`, compose files, Makefile, example policy/env, or tests in this slice.
2. If committing: docs/toolchain/change-package evidence **only**, before smoke. Never `20260817-вычисти*`, never `.env`, never `runtime/*`.
3. Write `/tmp/adaptive-trust-ci-build.env` (not `trust-ci/.env` unless a new protected-path grant names it). Measure `python:3.12-slim-bookworm` with `docker pull` + inspect. Set API/worker/runner to mutable `:2.1.0` tags.
4. Two-file `--profile build build api worker runner-image`. No `--push`, no `up`, no `supply-chain-release.sh`.
5. Inspect the three **just-built** tags with `.Id` + JSON RepoTags/RepoDigests. Dump under `trust-ci/runtime/build-smoke/`. Label not-a-pin. Optional syft/trivy there; skip cosign.
6. Re-run `test_example_holdout_digest_matches_example_bundle`. `git diff --exit-code` on example policy/env.
7. Write `evidence/implementation-images.md`. Stop. Ask the user for registry URL + `docker-push` grant before any pin; GitHub App / TLS / deploy / `branch-protect` remain later named grants.

---

## Single recommended design ruling the write owner must follow

**Treat this slice as a daemon compile with frozen product files: two-file compose build, no push, no up, no Makefile, no digest in git. Isolate the already-reviewed docs tree (commit it first or `git diff --exit-code` on it). Use a `/tmp` env-file with a measured python base and mutable local `:2.1.0` tags; inspect those tags’ `.Id` and JSON `RepoDigests` and record them only under gitignored `trust-ci/runtime/build-smoke/` plus a summary evidence file. On Docker 29 a non-empty `RepoDigests` that equals `.Id` is still not a registry pin — never copy it into `policy.example.json` or `.env.example`. Example holdout digest stays test-locked; production holdout waits because `/srv` and `/opt` bundles do not exist. Handoff §3, registry push, GitHub App, deploy, TLS webhook, and branch protection are out of slice.**
