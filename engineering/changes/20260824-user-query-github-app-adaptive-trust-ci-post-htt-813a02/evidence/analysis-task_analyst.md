# task_analyst — Tailscale Funnel `/webhooks/github` (route 813a02b06dfc)

**Verdict:** this slice is **one additive Tailscale Funnel path** on host `claw` plus two probes. It is **not** a `TRUST_CI_PUBLIC_BASE_URL` / compose-recreate change, **not** GitHub App webhook registration, **not** a repository webhook, **not** PEM, **not** M0.2 complete.

Write owner: **`integration_implementer`**. This agent does not implement, push, merge, read PEM/`.env`/webhook secret, PATCH `/app/hook/config`, or `funnel reset`.

Skills: `/adaptive-delivery`, `feature-workflow`, `api-event-change`. Allowed agents only. Analysis is read-only except this evidence file. Route `human_gates`: **none**.

---

## 1. Outcome of THIS slice

**Observable result:** From the public Internet, `POST https://claw.taild9f611.ts.net/webhooks/github` terminates TLS on **Tailscale Funnel :443** and is proxied to the already-running Trust CI API at **loopback** `http://127.0.0.1:18080/webhooks/github`. Unsigned POSTs still die at FastAPI HMAC with **HTTP 401** `missing or malformed webhook signature`. Compose still publishes **only** `127.0.0.1:18080:8080`.

This is the **public Funnel edge for one path**. It is **not** GitHub App webhook **registration**. The user named the URL as the address GitHub will later require; this slice only **proves the path** (`проверка до настройки GitHub`).

Live facts (sibling `analysis-repo_explorer.md`; no secrets):

| Plane | State |
| --- | --- |
| Host | `claw`. SearXNG owns host `:8080`. |
| Funnel / serve | **Empty** (`{}` / “No serve config”). Expected n8n `/webhook` is **not** present right now. `/webhooks/github` is **not** mounted. |
| Loopback | `GET http://127.0.0.1:18080/health/live` **200**; `/health/ready` **200**. |
| Compose | `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"`. |
| Activation report | `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`; App `4694114`; Installation `156003193`; Check Runs via **local HMAC**; **no public GitHub hook**. |
| Plan M0.2 | `[ ] Register repo webhook … — **not done** (no public HTTPS)`. |
| FastAPI | `POST /webhooks/github` already HMAC-first; signed non-`pull_request` (e.g. ping) → 200 `ignored-event`. Frozen this slice. |

---

## 2. Direct answers to the two scope questions

### Is `TRUST_CI_PUBLIC_BASE_URL` change in this slice?

**No.** Out of this slice.

User-approved scope (source of truth #1) lists Funnel inspect, Funnel add-path, Funnel status, local `/health/live`, public unsigned ping. It does **not** list `sed` of gitignored `trust-ci/env/common.env`, `docker compose … --force-recreate`, or an activation-report cell rewrite.

Why recreate would be required if the URL *were* in scope (it is not):

- `api` and `worker` both `env_file: ./env/common.env`. Compose applies `env_file` at **container create**.
- `docker compose restart` does **not** re-read env. A live URL flip needs `up -d --force-recreate api worker` (named services only, same untracked host-socket overlay, **never** postgres / `down -v`).
- User did not list that recreate. Do not invent it.

Why the 401 proof does not need the env var:

- `TRUST_CI_PUBLIC_BASE_URL` is Check Run `details_url` origin (`{base}/jobs/{id}`), not webhook routing.
- HMAC uses `TRUST_CI_WEBHOOK_SECRET`. `GET /health/live` does not read the public URL.
- `CommonSettings` already allows loopback HTTP; HTTPS is required only **outside** localhost. Leave the running process on `http://127.0.0.1:18080`.

Contrast: Apache TLS slice `010964` **did** list step 7 (`TRUST_CI_PUBLIC_BASE_URL=https://…` + recreate `api worker`) because that user order named it. This order does not.

**Bounded ruling vs sibling docs_researcher:** after a later named slice that lists recreate, flip gitignored env **and** the activation-report cell together to origin `https://claw.taild9f611.ts.net` (no webhook path in the cell). Do **not** do that here. Do not leave docs claiming HTTPS origin while containers still have loopback `details_url`.

### Is GitHub App webhook registration in this slice?

**No.** Out of this slice.

User heading: **«Проверка до настройки GitHub»**. User-forbidden this slice: GitHub App **form**, App **PATCH** `/app/hook/config`, **repository webhook**, **PEM**.

`PATCH /app/hook/config` needs an App JWT minted from the App private key. `AGENTS.md` forbids reading that PEM. Do not substitute a repo hook (`decisions.md`: webhook config lives on App `adaptive-trust-ci`, not as a substitute repository webhook).

Unsigned public ping **401** means Funnel reached FastAPI HMAC. It does **not** mean GitHub delivered. Plan checkbox stays `[ ]` **not done**. M0.2 stays incomplete. Registration is a **later named slice** after 401 (operator UI on `https://github.com/settings/apps/adaptive-trust-ci`, secret never printed).

---

## 3. In scope / out of scope

### In scope

1. **Inspect** `sudo tailscale funnel status --json` (and human `funnel status`). **No reset.** Snapshot existing paths first.
2. **Add** one Funnel path **next to** whatever is already there (including a missing n8n `/webhook` — see residual risk):

   ```bash
   sudo tailscale funnel --bg --https=443 \
     --set-path=/webhooks/github \
     http://127.0.0.1:18080/webhooks/github
   ```

   Dual path is **required**: Funnel strips the public mount point before proxying; the target must keep `/webhooks/github` so FastAPI matches `POST /webhooks/github`. No trailing slash.
3. **Re-inspect** `sudo tailscale funnel status`. Expect `/webhooks/github` → `http://127.0.0.1:18080/webhooks/github`. Do not remove other paths if any appear.
4. **Local** `curl -i http://127.0.0.1:18080/health/live` → **200** (already true; re-check after Funnel add).
5. **Public unsigned** ping (no `X-Hub-Signature-256`):

   ```bash
   curl -i -X POST \
     -H 'Content-Type: application/json' \
     -H 'X-GitHub-Event: ping' \
     --data '{}' \
     https://claw.taild9f611.ts.net/webhooks/github
   ```

   Expect **HTTP 401** (HTTP/2 or HTTP/1.1) and body detail `missing or malformed webhook signature`. That is success.

6. **Change-package evidence** of the four commands + responses. FastAPI / compose / policy / holdout / images stay frozen.

User-listed Funnel write is the only named host mutation. Mint a local grant only for that exact `funnel --bg --https=443 --set-path=/webhooks/github` (plus status). Wildcard forbidden.

### Out of scope (explicit)

| Item | Why out |
| --- | --- |
| `sudo tailscale funnel reset` | User-forbidden. Would wipe n8n/TikTok if present; still forbidden while Funnel is empty. |
| `sudo tailscale funnel --bg 443 on` | User-forbidden old CLI. Target command creates the handler. |
| **`TRUST_CI_PUBLIC_BASE_URL` sed / activation-report cell / `compose … --force-recreate`** | User did not list recreate. HMAC 401 does not need it. Later slice. |
| **GitHub App form / `PATCH /app/hook/config` / App JWT** | «Проверка до настройки GitHub». PEM forbidden. |
| **Repository webhook** (`gh api …/hooks`, UI Add webhook) | User-forbidden. App already installed; do not substitute. |
| **PEM**, `.env` dump, `TRUST_CI_WEBHOOK_SECRET` print, human approval private key | Forbidden. Unsigned 401 does not need the secret. |
| Restore n8n `/webhook` / TikTok Funnel | Explorer: current Funnel is empty. User did not give an n8n target. Add GitHub path without reset; do not rebuild n8n this slice. |
| Funnel `/approvals`, `/jobs`, `/metrics`, `/health/*` | User listed only `/webhooks/github`. |
| Publish API on `0.0.0.0:18080` or host `:8080` | Tracked compose stays loopback. SearXNG keeps 8080. |
| Apache / certbot / `trust-ci.ii-tonya.ru` | Voided ChatGPT hostname. Do not probe or complete TLS for it. |
| FastAPI / worker / policy / holdout / image pin edits | Contract already HMAC-first. |
| `compose down`, `down -v`, postgres recreate | Not listed; catalog risk. |
| Signed public ping / signed `pull_request` / enqueue a job via Funnel | Would need the webhook secret. Not listed. |
| `branch-protect`, merge, push `main`, tag, Release, M0.2 `[x]` | Later authority work. |

Rollback (if needed, still no reset): turn **off that path only**, e.g. `sudo tailscale funnel --https=443 --set-path=/webhooks/github off`. Leave any other Funnel/serve config untouched.

---

## 4. Acceptance criteria

- [ ] **Given** Funnel status inspected with **no reset**, **when** the additive `--set-path=/webhooks/github` command runs with target `http://127.0.0.1:18080/webhooks/github`, **then** `funnel status` shows that path and does not claim a reset of other handlers.
- [ ] **Given** API on loopback, **when** `GET http://127.0.0.1:18080/health/live`, **then** HTTP **200**.
- [ ] **Given** Funnel path live, **when** unsigned `POST https://claw.taild9f611.ts.net/webhooks/github` with `X-GitHub-Event: ping` and body `{}`, **then** HTTP **401** and detail `missing or malformed webhook signature` (JSON FastAPI, not nginx/Apache HTML).
- [ ] **Given** this slice complete, **when** GitHub App hook config / repo hooks / PEM / `common.env` / compose recreate are inspected, **then** they are **unchanged**. Plan M0.2 webhook line stays **not done**.

Failure signals (not success):

| Response | Meaning |
| --- | --- |
| TLS/DNS error | Funnel not serving `claw.taild9f611.ts.net` yet |
| 404 | Mount stripped and target missing `/webhooks/github`, or path not added |
| 502/503 | Loopback API down (re-check `/health/live`) |
| 405 HTML | Hit the wrong public edge (historical nginx), not FastAPI |
| 200 `ignored-event` on **unsigned** ping | HMAC bypassed — **fail closed**; do not proceed to GitHub registration |
| 401 on **local** `/health/live` | Wrong URL; live is GET, not POST webhook |

---

## 5. Constraints

- **Compatibility:** FastAPI `POST /webhooks/github` unchanged. Dual Funnel path preserves that contract despite mount-point strip.
- **Security:** Public path is POST webhook only. HMAC fail-closed before JSON. Do not print secrets. Do not funnel the rest of the API.
- **Operational:** Additive Funnel only. Empty current config is **not** a license to `reset` or to restore n8n. No compose recreate this slice.
- **Docs:** Change-package evidence may record the proven Funnel origin. Do not rewrite activation-report `TRUST_CI_PUBLIC_BASE_URL` or tick M0.2 until a later named slice that includes env recreate **and** App registration as separate steps.

---

## 6. Residual risk

Funnel is currently empty; n8n `/webhook` the user expected is not on this host’s serve config. Adding `/webhooks/github` is still additive. If n8n later needs its own path, that is a **separate** `--set-path=/webhook` with n8n’s target — never `funnel reset`, never the old `443 on`.
