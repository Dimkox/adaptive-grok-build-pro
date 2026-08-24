# task_analyst — M0.2-partial live Check Run on claw (route 3e61666b8de2)

**Verdict:** this turn is a **bounded operational proof**, not M0.2 complete and not M0.3. The primary observable result is an **App-owned** Check Run named `adaptive-trust-ci/verified@6737355947c2` on the exact pull-request head SHA, published by GitHub App ID `4694114`. Write owner: `general_implementer`. This agent does not implement, push, merge, read PEM, or deploy.

**Bounded ruling (source-of-truth order):** user standing order «короче делай сам», auto-approved compose-up / feature-branch push, and the named simplest slice outrank spec language that waits for public HTTPS webhook registration. The slice **does not** claim M0.2 exit, does not protect `main`, and does not treat a local HMAC POST as a substitute for a GitHub-registered webhook. It is a loopback characterization of the already-tested `/webhooks/github` contract so the worker can publish a real Check Run while GitHub still cannot POST to `127.0.0.1`.

## Primary outcome

On host `claw`, compose project `adaptive-trust-ci` has a **running worker** that can mint an installation token and call the GitHub Checks API. After one HMAC-signed `POST http://127.0.0.1:18080/webhooks/github` for PR **#5** (or a disposable docs PR), GitHub shows Check Run `adaptive-trust-ci/verified@6737355947c2` on the **exact** head SHA, `app.id = 4694114`, `external_id = <durable job_id>`.

Success for this slice is **publication and ownership**, not `conclusion=success`, not `main` protection, and not a GitHub-delivered webhook.

### Why this slice is the smallest coherent proof

| Blocker now | Slice response |
| --- | --- |
| Nested rootless DinD: `rootlesskit: fork/exec /proc/self/exe: operation not permitted`; `runner-loader`/`worker` stay `Created` | Point loader+worker at the **host** Docker socket so the worker process can start |
| `worker.env` `HTTP_PROXY=http://127.0.0.1:1080` is container loopback, not host glider | `HTTP_PROXY`/`HTTPS_PROXY=http://host.docker.internal:1080` plus compose `extra_hosts: host.docker.internal:host-gateway` |
| GitHub cannot POST to `127.0.0.1:18080`; no public HTTPS | Operator HMAC POST to the loopback API (same headers the unit tests already use) |
| Spec M0.2 wants a registered HTTPS webhook first | Out of this slice; local POST is only enqueue |

`JobRunner.process` calls `ensure_check_run` **before** checkout, holdout commands, or approval-scope evaluation. If the worker can reach `api.github.com` through the proxy, the Check Run appears even if git fetch, host-path mounts, or `needs_approval` fail later.

## Current behavior (facts)

- Branch `milestone/m0-live-trust-authority`, draft PR **#5**, latest pushed SHA `1fc942065a124ce75659bd082519d8ebc37774e8` (confirm before POST; a new push invalidates the payload).
- API healthy: `GET http://127.0.0.1:18080/health/ready` → 200. Host `:8080` is SearXNG. Do not bind Trust CI there.
- Worker/DinD not running. Policy digest `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`; epoch name `adaptive-trust-ci/verified@6737355947c2`.
- App ID `4694114`, Installation ID `156003193` already in gitignored `trust-ci/env/worker.env`. PEM filename exists and is gitignored; **never open it**.
- `main` unprotected. Repo webhook list empty. Leftover Actions workflow `340420982` untouched.
- Tracked compose: isolated privileged DinD, `DOCKER_HOST: tcp://docker-engine:2375`, tests **forbid** `/var/run/docker.sock` (`trust-ci/tests/test_ops.py`, `trust-ci/scripts/smoke.sh`).
- Worker image `USER 10001:10001`, `cap_drop: ALL`, read-only. Docker CLI is in the image; the user is **not** in a docker group.
- `GitWorkspace._git_env` strips the environment to `PATH`/`HOME`/`GIT_*` and does **not** forward `HTTP_PROXY`. `UrllibTransport` **does** honor process proxies. Token mint and Checks API can succeed while `git fetch` later fails.
- Deployed `approval_rules` treat `trust-ci/**`, `.grok/**`, `AGENTS.md`, `decisions.md`, `compose*.yaml`, Dockerfiles as signed-approval scopes. PR #5 is an M0 branch; if its diff hits those globs, the Check Run will complete `action_required` / job `needs_approval`. That is still a published App-owned check.

## In scope

1. Host-local worker/loader topology that uses the **host** Docker engine instead of nested rootless DinD, without stealing existing non-Trust-CI containers, volumes, or networks.
2. Correct container-reachable proxy: `HTTP(S)_PROXY=http://host.docker.internal:1080`, `NO_PROXY` at least `postgres,127.0.0.1,localhost`, `extra_hosts: host.docker.internal:host-gateway` on services that call GitHub or whose urllib/git needs the proxy.
3. Remap `TRUST_CI_WORKSPACE_HOST_ROOT` and `TRUST_CI_HOLDOUT_HOST_PATH` to **host-daemon-visible** absolute paths (bind-mount a host directory; do not reuse DinD-only named-volume paths).
4. Supplementary docker GID (`group_add`) so uid `10001` can use `/var/run/docker.sock`. Do not run the worker as root to “make the socket work.”
5. One HMAC-signed loopback `POST /webhooks/github` for PR #5 (preferred: already exists) or a disposable docs-only PR. Secret from gitignored `trust-ci/env/api.env`; never print it.
6. Observe and record operator-safe Check Run id, `external_id`, `app.id`, name, head SHA. Update the activation report **without secrets**.
7. If tracked product files change: failing/characterization tests first, then `python3 scripts/grok_verify.py --mode pr` and route reviews. If only gitignored env + an untracked compose overlay: skip verify (no-op product tree).
8. Exact local grant for compose-up (and `git-push-branch` only if this branch must move). User auto-approves those two operational actions.

Architect may choose **untracked compose overlay** (`docker compose -f compose.yaml -f <gitignored-or-/tmp overlay>`) over editing `trust-ci/compose.yaml`. Overlay is the smaller product risk: tracked tests/smoke/systemd keep the DinD invariant; live claw topology is an operator exception. Editing tracked compose **requires** rewriting `test_ops.py`, the `test_database_roles.py` `docker-engine` split, `test_supply_chain.py` systemd string, `smoke.sh`, and `trust-ci/systemd/adaptive-trust-ci-compose.service` in the same change.

## Out of scope / forbidden (explicit non-goals)

- **M0.3:** `adaptive-trust-ci branch-protect`, protect `main`, bind App ID on branch protection.
- **Public webhook:** Cloudflare / Caddy / any TLS hostname; `POST https://<public>/webhooks/github` registration; changing `TRUST_CI_PUBLIC_BASE_URL` off loopback HTTP.
- **Merge or ready PR #5.** Do not mark ready. Do not merge.
- **M0.2 remainder:** offline attestation as a required exit (only if the job actually signs one); SHA/policy/holdout retitle drill; kill switch drill; backup/restore/restart drill; human Ed25519 requeue of `needs_approval`.
- **M1–M9**, `factory/`, root `pyproject.toml` / `requirements.txt` / `setup.py`.
- **PEM / JWT / installation token / webhook secret / read token / CI signing key / human approval private keys:** never read into chat, never `cat`, never commit.
- **Forge** `adaptive-trust-ci/verified@*` from another actor, `gh api` check-run create with a user token, or GitHub Actions.
- **`.github/workflows/**`**, Dependabot CI, leftover workflow `340420982` disable (M0.3).
- Publish Trust CI on host **8080**. Rebind `proxy-gateway`. `network_mode: host` for the worker.
- Steal or recreate n8n/Caddy/SearXNG/app-stack containers, volumes, or networks.
- `git add -A`. Direct push to `main`. Force push. Tag/release/VERSION bump.
- Generate or submit a human security-approval envelope.

## Acceptance criteria (provable this slice)

**P0 — Check Run publication (must all pass)**

1. **Given** API is ready on `127.0.0.1:18080` and postgres is the existing `adaptive-trust-ci` volume, **when** loader+worker start against the host Docker socket with host-gateway proxy, **then** `docker compose --project-name adaptive-trust-ci ps` shows `api` healthy, `worker` **running** (not `Created`), and `docker-engine` is either healthy **or not required for this topology**. Host `:8080` remains SearXNG. Host `:1080` remains proxy-gateway.
2. **Given** gitignored `TRUST_CI_WEBHOOK_SECRET` and a `pull_request` JSON body whose `repository.full_name`, `number`, `head.sha`, `head.ref`, `base.sha`, `base.ref` match the live PR, **when** `POST /webhooks/github` is sent with `X-GitHub-Event: pull_request` and `X-Hub-Signature-256: sha256=<hex>` over the raw bytes, **then** the API returns HTTP 200, `accepted: true`, and a `job_id` (first delivery `created: true`; replay of the same repo/PR/SHA/policy returns `created: false` and the same `job_id`).
3. **Given** that job is claimed, **when** the worker mints an installation token through `http://host.docker.internal:1080`, **then** GitHub lists a Check Run on the exact head SHA with:
   - `name` = `adaptive-trust-ci/verified@6737355947c2`
   - `app.id` = `4694114` (slug `adaptive-trust-ci`)
   - `external_id` = the durable `job_id`
   - `head_sha` = the POST body SHA
4. **Given** any inspect of env or logs, **then** PEM, webhook secret, read token, signing key, JWT, and installation token are absent from the activation report, chat, and git.

**P1 — Honest terminal states (any one is acceptable after P0)**

| Terminal | When it is the expected honest result |
| --- | --- |
| `in_progress` long enough to screenshot, then `failure` | Checkout/git-proxy, docker.sock permission, or host-path mount failed **after** `ensure_check_run` |
| `action_required` / job `needs_approval` | PR #5 (or overlay) touched governance/production/database globs; **do not** forge a human approval |
| `success` + stored attestation | Only if the PR diff is outside approval globs **and** holdout+commands pass; not required to close this slice |

**P2 — Optional, still this slice if cheap**

- Disposable docs-only PR whose diff is outside `approval_rules`, to chase `conclusion=success`. Do not block P0 on it.
- Forward `HTTP_PROXY` in `GitWorkspace._git_env` **only if** P0 already holds and checkout is the remaining failure. That is a small product change with a characterization test.

Non-criteria for this slice: `GET .../hooks` stays empty; `GET .../branches/main/protection` stays 404; no GitHub Actions runs.

## Empty, loading, and error states

Treat these as **expected closed-loop failures**, not improvisation:

| Signal | Meaning | Operator action |
| --- | --- | --- |
| Webhook 401 `invalid` / `malformed` | HMAC missing, not `sha256=`+64 hex, or secret mismatch | Stop. Recompute over **raw** bytes. Do not print the secret. Do not retry with a guessed secret. |
| Webhook 403 | `repository` not in server policy (`Dimkox/adaptive-grok-build-pro` only) | Stop. Do not widen policy this slice. |
| Webhook 503 | Kill switch file present or API not ready | Do not remove `STOP` unless this session created it. Confirm `/health/ready`. |
| `accepted: false`, `ignored-event` | Wrong `X-GitHub-Event` or unsupported action | Use `pull_request` + `opened`/`synchronize`/`reopened`/`ready_for_review`. Drafts **must** enqueue. |
| 200 + `created: true` + worker `Created`/exited | Job queued, no publisher | Do not claim a Check Run. Fix worker/socket/proxy; do not re-POST forever (idempotent). |
| Worker logs `GitHub request failed` / proxy connection refused | `127.0.0.1:1080` still in container, missing `extra_hosts`, or glider down | Fix proxy path. Do not disable TLS verification. |
| Worker `cannot read GitHub App private key` | Mount/path/permission; **do not open the PEM** | Fix bind mode (`:ro`) and path only. |
| `permission denied` on docker.sock | uid 10001 not in host docker GID | `group_add` host `docker` GID; do not chmod `666` the socket; do not `user: "0:0"`. |
| `docker run` mount errors / empty workspace | `TRUST_CI_WORKSPACE_HOST_ROOT` still DinD path | Bind-mount a host dir and set both roots to that absolute path. Same for holdout host path = `TRUST_CI_HOLDOUT_SOURCE_PATH`. |
| Check Run exists but `app.id` ≠ `4694114` | Another actor used the same text | **Fail the slice.** Do not complete or mimic it. |
| Job `needs_approval` | Protected globs in the PR | Record scopes. Do not sign approvals. P0 still passes. |
| Job `dead` after retries | Infrastructure errors exhausted; `publish_dead_job` should still leave an App-owned `failure` check | That failure check **satisfies P0** if name/app/SHA/`external_id` match. |
| Second POST, same SHA | `created: false`, same `job_id` | Expected idempotency. |

Loading: after 200, poll job status and GitHub check-runs with a bound (lease 300s, `max_attempts` 3). Do not busy-loop. Do not wait for human HTTPS.

## Permissions and secrets handling

- **Compose-up** of worker/loader (and overlay) is authorized by the user’s standing operational grant. Mint an exact `grok_approve.py` grant bound to repo, route, change, HEAD, tree fingerprint, action, resource, TTL. No wildcard.
- **`git-push-branch`** on `milestone/m0-live-trust-authority` only if tracked files change. No push to `main`.
- Local loopback POST is **not** an external GitHub write and does not need a webhook-registration grant.
- Reading Check Runs / PR metadata via `gh` is read-only.
- `trust-ci/env/*.env` and `trust-ci/runtime/*` stay untracked. Load `TRUST_CI_WEBHOOK_SECRET` and `TRUST_CI_READ_TOKEN` into shell variables without `echo`/`set -x`/`cat`. HMAC in Python or `openssl dgst -sha256 -hmac` with secret from env.
- API holds webhook secret + trust-store **public** keys. Worker holds App ID/install ID/PEM path + CI signing key. Do not copy webhook secret into `worker.env` or App PEM into `api.env`.
- Worker installation token permissions remain `checks:write`, `contents:read`, `pull_requests:read`. Do not grant Administration to the App.
- Host Docker socket in the worker is a **residual security regression** vs isolated DinD (worker+PEM+full host Docker API on an engine that also runs SearXNG/n8n). Accepted only to unblock this proof. Socket must not be mounted into `api`, `postgres`, or the **runner** container (`sandbox.py` does not pass it; keep that). Do not persist this as silent default without architect documentation if tracked compose is changed.

## Observability (inspect without dumping secrets)

Proof commands (operator-safe):

```text
curl -fsS http://127.0.0.1:18080/health/ready
docker compose --project-name adaptive-trust-ci ps
gh api repos/Dimkox/adaptive-grok-build-pro/commits/<exact-sha>/check-runs
```

Filter check-runs locally for `name==adaptive-trust-ci/verified@6737355947c2` and `app.id==4694114`. Record `id`, `external_id`, `status`, `conclusion`, `head_sha`.

Job/metrics (Bearer read token, never printed):

- `GET /jobs/{job_id}` — status, policy digest, failure_code; tails are stripped by `_public_result`
- `GET /metrics` — `adaptive_trust_ci_jobs{status=...}`, `policy_epoch`, `check_name`
- `GET /attestations/{job_id}` — 404 is normal for `needs_approval` / pre-attestation failure

Logs: `docker compose --project-name adaptive-trust-ci logs --tail 200 worker api` — redact if a token ever appears; prefer not to paste logs that follow a GitHub 201 token response.

Do not `docker exec` into the worker to `cat` `/run/secrets/github-app-private-key.pem`.

Activation report fields to fill after P0: disposable PR number (or `#5`), head SHA, Check Run id, `external_id`. Keep `main protected = false`. Keep `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`.

## API / event / data compatibility

- No schema/migration this slice. Reuse existing `trust_ci_jobs` idempotency (`repository + pr_number + head_sha + pipeline + policy_digest`).
- Webhook contract unchanged: HMAC, `pull_request`, drafts enqueue, closed cancels.
- Check name stays policy-epoch `@6737355947c2` until policy bytes change. Do not retitle by editing `status_context` this slice.
- Local POST body is a GitHub-shaped event, not a new API. Minimum fields: `action`, `repository.full_name`, `pull_request.number`, `head.sha/ref`, `base.sha/ref`. Fetch those from `gh api repos/Dimkox/adaptive-grok-build-pro/pulls/5` without mixing in the webhook secret.

## Observability success metric

One App-owned Check Run on the exact SHA. Secondary: worker container state `running`; webhook `accepted`; job row exists. Do not use local receipts or delegated grants as the metric.

## Rollback

Trigger: worker cannot be made healthy, socket mount threatens other stacks, or a Check Run is published by the wrong app.

1. `docker compose --project-name adaptive-trust-ci stop worker runner-loader` (and any overlay-defined docker-socket service). Leave `postgres` + `api` up.
2. Remove host-socket overlay / unmount `/var/run/docker.sock`. Restore gitignored `worker.env` proxy only if this session changed it; do not commit the restore.
3. Do **not** `compose down -v`. Named volume `trust-ci-postgres` stays.
4. Queued jobs may sit until lease expiry; optional closed-event POST cancels the PR’s jobs. Do not SQL-delete blindly.
5. A published Check Run cannot be unpublished. Do not PATCH it to `success`. A later honest `failure`/`action_required` is acceptable. `main` is unprotected, so this cannot lock the repository.
6. Tracked compose/tests: revert the feature branch commit if product files were changed and the overlay approach is chosen instead.
7. Verify after rollback: `/health/ready` 200; no Trust CI container still has `/var/run/docker.sock`; `main` still unprotected; hooks still empty.

## What still requires a human later

- **Cloudflare (or other) HTTPS tunnel** and GitHub webhook registration to `/webhooks/github` with the API HMAC secret. Local POST is not that webhook.
- **Temporary human administration token** for `adaptive-trust-ci branch-protect` **after** an unambiguous live check (M0.3). App must not gain Administration.
- **Disable leftover Actions workflow `340420982`.**
- **Human Ed25519** `adaptive-trust-ci approval-create` on a human machine for `needs_approval` requeue of the **same** Check Run / exact SHA. Agents must not generate, read, or simulate that private key.
- Offline attestation verify with the published CI **public** key (private signing key stays worker-only).
- Supersede bootstrap-exception language in `decisions.md` / README once live authority is real (M0.3).
- PEM rotation, trust-store private keys, production mutation, merge of PR #5.

## Product vs operator overlay (architect gate, not a user question)

Recoverable from the tree: changing tracked `compose.yaml` fights `test_ops`, `smoke.sh`, systemd, and `test_database_roles` split. User asked for the simplest proof. **Default ruling:** prefer an **untracked overlay + gitignored env** so P0 does not require a product-topology inversion in PR #5. If overlay is insufficient (GID, binds, extra_hosts), make the smallest tracked change with tests in the same commit.

If product files change, `trust-ci/**` is both `protected_paths` and `control_plane_paths`: no shell `sed` of compose; structured Edit/Write or `grok_protected_write.py` with an exact grant.

## Non-functional

- **Security:** role split intact; host-socket residual documented; runner stays `network=none` / no socket / no token; secrets never printed.
- **Reliability:** idempotent webhook; lease 300s; max_attempts 3; fail-closed on HMAC/proxy/PEM.
- **Performance:** sandbox `memory_mb: 4096` on ~16 GiB ECC is tight but in-policy; do not raise memory this slice; one job at a time.
- **Compatibility:** no GitHub Actions; no public port change; no policy digest change.

## Risks

- Host Docker socket + App PEM on a shared engine is host-root equivalent if the worker is compromised. Mitigation: overlay-only, runner argv unchanged, no socket in api/runner, rollback stops worker first.
- `host.docker.internal:host-gateway` reaching `127.0.0.1:1080` depends on Docker Engine extra_hosts behavior. If it fails, stop; do not rebind proxy-gateway or use `network_mode: host` without a new ruling.
- PR #5 likely trips `needs_approval`. That is not a P0 failure.
- PreToolUse denies opaque `trust-ci` shell mutations. Plan grants and structured edits before implementer starts.

## Go / no-go

**Go** when P0 Check Run is App-owned on the exact SHA and secrets stayed off the record.

**No-go / stop** if the only way to proceed is protecting `main`, merging #5, reading PEM, forging a check, adding GitHub Actions, publishing `:8080`, or registering a non-HTTPS GitHub webhook.
