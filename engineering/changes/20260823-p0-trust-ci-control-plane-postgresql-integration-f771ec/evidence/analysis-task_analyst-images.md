# Task analyst — next slice: local build-without-push smoke

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `d2ba49e0570d` (intent=feature, write=`general_implementer`, reviews=`code_reviewer`+`test_reviewer`, evidence=`verification`+`code_review`+`test_review`)  
HEAD last recorded: `5915b56db7d6aedcd52a6c023418db84d45dd98f` on `feat/trust-ci-control-plane`  
Agent: `task_analyst` (read-only except this report)

`GROK_BUILD_HANDOFF.md` remains the user-approved order. This is not a new product design.

---

## Chosen slice for this turn

**HANDOFF §3 local subset only:** two-file Compose **build without push**, measure local image Ids, recompute the **example** holdout digest, keep evidence off tracked product files.

This is the smallest coherent vertical that `general_implementer` can finish **without secrets, without invented digests, and without GitHub App creation**. It does **not** complete HANDOFF §3 “pin immutable artifacts in deployed policy”. Local `Id` is not a registry pin. `RepoDigests` stays empty until a later registry push.

Do not start HANDOFF §4–§9 in this turn.

---

## Already done (do not redo)

| Item | Evidence |
| --- | --- |
| Baseline repairs, draft-PR enqueue, live PostgreSQL 8/8 + restart drill PASS | `tasks.md`, prior reviews on `5915b56` |
| Docs/graph resume: K16 README, two-file compose docs, optional docker/syft/trivy/cosign, QUICKSTART drafts enqueue | `evidence/implementation-resume.md`; independent `code-review-resume.md` + `test-review-resume.md` **PASS** |
| Example holdout digest locked to `trust-ci/holdout.example` | `test_ops.test_example_holdout_digest_matches_example_bundle`; `policy.example.json` `holdout.digest` = `b78d1700…d7d5db8` |
| Example runner image still a placeholder | `adaptive-trust-ci-runner@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST` |
| Grant `762816e981e59918` consumed | further protected writes need a **new** fingerprint-bound grant; this slice must not need one |

Working tree is still **dirty and uncommitted**. Leave that docs/toolchain/test set in place. Do not revert it. Do not commit `engineering/changes/20260817-вычисти*`.

---

## A. Local product / git that can land now

**Ruling: land no product digest, and do not make git the work of this slice.**

| Candidate | This turn? | Why |
| --- | --- | --- |
| Edit `README.md` / `trust-ci/README.md` / `decisions.md` / `QUICKSTART.md` / toolchain | **No** | Docs slice is independently reviewed. Grant `762816` is consumed. `trust-ci/**` and README are protected. |
| Fill `REPLACE_WITH_*` in `.env.example` or `policy.example.json` with local Ids or guessed hex | **Forbidden** | Invented or non-registry pins. Structure test allows the runner placeholder. |
| New `build-local.sh` / `TRUST_CI_API_BUILD_TAG` on api/worker in `compose.build.yaml` | **No** | Nice-to-have, not required. Would need a new `protected-path-write` on `trust-ci/**` and would contradict the documented “api/worker have no local tag in compose.build.yaml”. Untracked `.env` can set `TRUST_CI_API_IMAGE=adaptive-trust-ci-api:2.1.0` for build-only. |
| Characterization tests for `--confirm-push` or placeholder lock | **No** | `supply-chain-release.sh` already hard-requires `--confirm-push`. Holdout digest already tested. Extra tests are scope creep. |
| Tracked smoke **summary** under this change `evidence/` | **Yes, after smoke** | Change-package evidence is not a protected path. Record commands + pass/fail. Do not copy deploy pins into examples. |
| `git add` / `commit` of the dirty docs tree | **Allowed later, not this slice** | No secrets required. Still **not** the vertical. Commit does not need a grant; `git push` does. Defer so smoke artifacts cannot accidentally enter the index, and so one later commit can include this evidence file. |
| Update draft PR `#2` | **No** | Needs `production` + `git-push-branch` on the **post-commit** SHA. No such grant. |
| `grok_verify` + route reviews | **Skip if product tree unchanged** | AGENTS.md: skip no-op analysis/review when only paperwork/status. If any `trust-ci/**` or test file is touched, then `grok_verify --mode pr` and `code_reviewer`/`test_reviewer` on the new fingerprint. |

Stageable later (not now), if the user asks for a local-only commit after this smoke:

```text
README.md
trust-ci/README.md
QUICKSTART.md
.grok-stack/config/toolchain.json
tests/test_structure.py
tests/test_toolchain.py
engineering/runbooks/trust-ci-rollout.md
decisions.md
mistakes.md
engineering/changes/20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec/**
```

Never stage: filled `.env`, `trust-ci/env/*.env`, `trust-ci/runtime/**`, `*.pem`, SBOMs, trivy JSON, local image Ids used as pins, leftover `20260817-вычисти*`.

---

## B. Local docker build-without-push smoke

`docker compose … build` is **not** a `production_action`. `docker push` and `supply-chain-release.sh --confirm-push` **are**. Live PostgreSQL already used `compose.test.yaml`, so Docker Engine was present on this host; the write owner must re-confirm before building. If Engine is missing or a public base digest cannot be **measured**, **stop and report blocked**. Do not invent hex. Do not skip ahead to GitHub App.

### B1. Untracked operator env (do not read existing `.env` / PEMs)

If `trust-ci/.env` is missing, copy `.env.example` to `trust-ci/.env` (gitignored). Do not open `trust-ci/runtime/github-app-private-key.pem` if it exists.

Measure public bases (real `RepoDigests`, not guessed):

```bash
docker pull python:3.12-slim-bookworm
docker pull postgres:17.6-bookworm
docker pull docker:29-dind-rootless
docker image inspect python:3.12-slim-bookworm --format '{{index .RepoDigests 0}}'
docker image inspect postgres:17.6-bookworm --format '{{index .RepoDigests 0}}'
docker image inspect docker:29-dind-rootless --format '{{index .RepoDigests 0}}'
```

Write those three **measured** `name@sha256:<64 hex>` values into **untracked** `trust-ci/.env` as `TRUST_CI_PYTHON_BASE_IMAGE`, `TRUST_CI_POSTGRES_IMAGE`, `TRUST_CI_DIND_IMAGE`. Compose interpolates all `:?` vars even when only building api/worker/runner-image.

For **locally built** API/worker/runner, use mutable **build-only tags** in the same untracked `.env` (not digest pins):

```text
TRUST_CI_API_IMAGE=adaptive-trust-ci-api:2.1.0
TRUST_CI_WORKER_IMAGE=adaptive-trust-ci-worker:2.1.0
TRUST_CI_RUNNER_IMAGE=adaptive-trust-ci-runner:2.1.0
```

`compose.build.yaml` already default-tags `runner-image` as `${TRUST_CI_RUNNER_BUILD_TAG:-adaptive-trust-ci-runner:2.1.0}`. api/worker inherit `image:` from `compose.yaml`, so the untracked tag is what `compose build` will apply. Do not retag a local `Id` as `name@sha256:<id>` and call it a pin.

`TRUST_CI_HOLDOUT_SOURCE_PATH` can stay the example path in `.env.example` (`/srv/adaptive-trust-ci/holdout`) for interpolation. Do **not** install a host holdout bundle this turn.

### B2. Build (no up, no push)

From `trust-ci/`:

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{json .RepoDigests}}'
```

Expect: `.Id` is `sha256:` + 64 hex; `.RepoDigests` is `[]` for the three locally built images.

Holdout (example bundle only):

```bash
make trust-ci-holdout-digest
# must equal trust-ci/config/policy.example.json holdout.digest
```

Optional, if host tools exist (syft `1.51.0` / trivy `0.74.0` previously present; cosign was **not** installed):

```bash
syft "$TRUST_CI_API_IMAGE" -o cyclonedx-json=trust-ci/runtime/build-smoke/api.cdx.json
trivy image --severity HIGH,CRITICAL --ignore-unfixed --format json \
  --output trust-ci/runtime/build-smoke/api.trivy.json "$TRUST_CI_API_IMAGE"
# same for worker + runner
```

Missing cosign is **not** a fail. Do **not** run `cosign sign`. Do **not** run `trust-ci/scripts/supply-chain-release.sh`. Do **not** run `smoke.sh` or `docker compose up`.

### B3. Where evidence lives

| Keep | Location | Tracked? |
| --- | --- | --- |
| Inspect JSON, image Ids, RepoDigests dump, optional SBOM/trivy | `trust-ci/runtime/build-smoke/` (covered by `trust-ci/runtime/*`) | **No** |
| Filled `.env` with measured public-base digests + local build tags | `trust-ci/.env` | **No** |
| Commands, SHA, pass/fail, “RepoDigests empty, pins not committed” | `engineering/changes/…-f771ec/evidence/implementation-images.md` | Yes (summary only) |
| Example holdout digest | already in `policy.example.json`, test-locked | Yes (do not change) |

### B4. Must not be written into tracked files

- Any `sha256:` 64-hex for API/worker/runner (local `Id` or invented).
- Public python/postgres/dind RepoDigests copied into `.env.example`.
- Filled `runtime/policy.json` (gitignored if under `trust-ci/runtime/`; do not add a tracked copy).
- SBOM, trivy reports, cosign signatures.
- App ID, installation ID, webhook secret, PEM, `TRUST_CI_READ_TOKEN`.
- A “policy digest” computed from a policy that still has `REPLACE_WITH_*` or a local image Id in `sandbox.image`.

Local image **Id** may appear in the **untracked** smoke directory. If the tracked summary mentions Ids at all, label them `local-image-id, not a registry pin` and do not format them as `name@sha256:`.

---

## C. Human / ops work — STOP and ask

HANDOFF standing consent is **order**, not a live grant. None of the following is this slice. Ask the user by name; do not mint grants in anticipation.

| Work | Why stop | Exact later grant / actor |
| --- | --- | --- |
| `docker push` / `supply-chain-release.sh --confirm-push` | Registry write; only source of real `RepoDigests` | `production` + `docker-push` with explicit registry URL. User must name the registry. |
| Pin `name@sha256:` into **deployed** `.env` / host `runtime/policy.json` | Outside the PR trust domain; needs registry digest | Host files only (gitignored). Still not this turn. |
| CI attestation `keygen` on this host | Creates worker-only PEMs; not GitHub App, but expands scope | Optional later; never the human approval key. |
| Copy holdout to `/opt` or `/srv` and pin that digest in deployed policy | External holdout is a deploy artifact | Human/ops on the CI host. |
| Create/install GitHub App | Browser/manifest; App ID, installation ID, worker-only RSA, API-only webhook secret | Human. No `grok_approve` action creates an App. Agent must not invent IDs or read the existing `runtime/*.pem`. |
| TLS reverse proxy + public webhook URL | No in-tree proxy; GitHub will not use HTTP intake | Human. Architecture residual: do **not** steal `127.0.0.1:8080` (searxng). |
| `docker compose up -d postgres migrate api worker` / systemd enable | Deploy / production mutation | Named deploy/external grant + free loopback port. `smoke.sh` needs a live API. |
| Register webhook; prove App-owned check on PR `#2` | GitHub mutation + App key | `external-write` + worker credentials the agent must not mint. |
| Human Ed25519 approval proof | Private key stays off this environment | Human runs `adaptive-trust-ci approval-create` off-box. |
| `branch-protect` on `main` | Lockout if the App-owned check does not exist | Temporary human admin token; App must not have `administration`. |
| `git push origin feat/trust-ci-control-plane` / `gh pr ready` / merge | External write | `git-push-branch` on post-commit SHA; merge only on a later explicit user order after the App-owned check. Never `origin main`. |

Do not treat a leftover `trust-ci/runtime/github-app-private-key.pem` as “App already created”. Do not read it.

---

## Acceptance criteria (this slice only)

- [ ] Docker Engine is present. If not, slice is **blocked** (not failed-open into App/deploy).
- [ ] `TRUST_CI_PYTHON_BASE_IMAGE` (and postgres/dind for interpolation) in **untracked** `.env` are `name@sha256:` values **inspected after `docker pull`**, not invented.
- [ ] `docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image` exits 0. No `--push`, no `compose up`, no `supply-chain-release.sh`.
- [ ] Inspect of the three locally built images shows a local `.Id` and **empty** `RepoDigests`.
- [ ] `make trust-ci-holdout-digest` on `trust-ci/holdout.example` still matches `policy.example.json` `holdout.digest`. Example runner image is still `REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`.
- [ ] Raw inspect/SBOM/trivy (if run) live under `trust-ci/runtime/build-smoke/` or equivalent gitignored path.
- [ ] Tracked product files still have `REPLACE_WITH_*` image placeholders. No new digest hex in `.env.example`, `policy.example.json`, README, or QUICKSTART.
- [ ] No GitHub App, TLS, webhook, `branch-protect`, `git push`, merge, human approval key, or filled tracked env.
- [ ] `.github/workflows/` still absent. VERSION still `2.0.11`.
- [ ] If product files were not edited, do not dispatch reviews or treat local receipts as merge authority.

## Non-goals (this slice)

- Completing HANDOFF §3 pin into **deployed** policy (impossible without registry `RepoDigests`).
- GitHub App, webhook, Checks API, branch protection, PR `#2` update, merge.
- `docker compose up`, TLS, backups, systemd, `/health/ready`.
- CI or human key generation (human approval key is always forbidden).
- Committing, pushing, tagging, GitHub Release, VERSION bump, zip rebuild.
- Inventing or committing image/holdout/policy digests.
- Changing `compose.build.yaml` to add api/worker local tags.
- Re-running live PostgreSQL 8/8 unless this smoke dirties that harness.
- Reading `.env`, PEMs, or `github-app-private-key.pem`.
- Adding `grype`, root `Dockerfile` / `docker-compose.yml`, or GitHub Actions.

---

## Recommended task list (`general_implementer`, ≤6)

- [ ] Confirm Docker Engine. Copy `trust-ci/.env.example` → untracked `trust-ci/.env` if needed. `docker pull` python/postgres/dind; write **measured** RepoDigests into that `.env`; set API/worker/runner to local `:2.1.0` tags for build-only. Do not read existing PEMs.
- [ ] `docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image` (no push, no up).
- [ ] Inspect the three images; keep `.Id` + `RepoDigests` JSON under `trust-ci/runtime/build-smoke/`. Optional syft/trivy there. Skip cosign.
- [ ] `make trust-ci-holdout-digest`; confirm it matches the example policy holdout digest. Do not edit `policy.example.json`.
- [ ] Write `evidence/implementation-images.md`: commands, HEAD, pass/fail, “RepoDigests empty; no pin committed”. No product-file digest substitution.
- [ ] **Stop.** Ask the user for (1) registry URL + `docker-push` grant, (2) GitHub App create/install + untracked worker/API secrets, (3) TLS/port (not searxng `:8080`) + deploy grant, in that order. Do not commit/push unless they name a local-only commit of the existing docs tree as a separate follow-up.

---

Route `d2ba49e0570d` analysis complete. Write owner is `general_implementer`. Reviews after any **product** change: `code_reviewer`, `test_reviewer`. Local receipts, this file, and delegated grants are not the App-owned Check Run `adaptive-trust-ci/verified@<policy-sha12>`.
