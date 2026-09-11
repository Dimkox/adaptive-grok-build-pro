# Architect ruling — Tailscale Funnel path `/webhooks/github` (route 813a02b06dfc)

Change: `engineering/changes/20260824-user-query-github-app-adaptive-trust-ci-post-htt-813a02`  
Write owner: `integration_implementer`. This agent does not run Funnel add/`off`, PATCH GitHub App, recreate compose, read PEM/`.env`/webhook secrets, push, merge, or protect `main`.

Sources (no secrets): user Funnel command (verbatim); sibling `analysis-repo_explorer.md`, `analysis-docs_researcher.md`; `api.py` HMAC-first `POST /webhooks/github`; `webhooks.py` HMAC-over-raw-body; `settings.py` `TRUST_CI_PUBLIC_BASE_URL`; `runner.py` `details_url`; tracked `trust-ci/compose.yaml` loopback publish; `test_m0_invariants.py`; plan/spec/activation report; Tailscale CLI `funnel` docs (`--set-path` + `off`; `reset` wipes all); n8n TikTok RUNBOOK `/webhook` (keep, do not reset).

## Ruling (one paragraph)

**Execute the user’s Funnel command as specified.** Do not invent Apache, Caddy, or nginx for this path. FastAPI is unchanged (HMAC already first). Host change is **add Funnel path only**: `--set-path=/webhooks/github` **and** target `http://127.0.0.1:18080/webhooks/github` (Funnel strips the public mount, so the path must appear twice). Keep n8n `/webhook` if present; **never** `tailscale funnel reset`; **never** `tailscale funnel --bg 443 on`. Do not PATCH the GitHub App this slice. Do not claim M0.2 complete. Do not protect `main`. Leave `TRUST_CI_PUBLIC_BASE_URL` on loopback (`http://127.0.0.1:18080`) — HMAC is over the raw body, not the public base. Unsigned public POST **401** `missing or malformed webhook signature` is **live host evidence**, not a CI HTTP probe. After that 401, operator docs name `https://claw.taild9f611.ts.net/webhooks/github` as the public webhook URL; characterization tests assert that string in docs. Rollback removes **only** `/webhooks/github` via Funnel `off` with `--set-path`; never reset.

---

## Live facts (sibling explorer, this host)

| Plane | Fact |
| --- | --- |
| Funnel | `sudo -n tailscale funnel status --json` → `{}`. Human status: **No serve config**. Paths: **none**. |
| n8n `/webhook` | **Not present** on this node’s Funnel/Serve config right now. Keep = do not reset / do not `443 on`. Do **not** restore n8n in this slice. |
| Loopback API | `GET http://127.0.0.1:18080/health/live` **200**; `/health/ready` **200**. |
| Compose publish | `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"`. Invariant forbids `0.0.0.0` and host `:8080`. |
| `TRUST_CI_PUBLIC_BASE_URL` (key only) | `http://127.0.0.1:18080` (legal loopback HTTP). |
| Public Funnel POST | **Not proven** (no path yet). Do not treat absence as FastAPI failure. |
| Apache leftover | Prior slice leftover; **not** this edge. Leave untouched. Funnel is Tailscale userspace TLS, not host Apache `:443`. |
| GitHub App hook | Still unregistered. Loopback HMAC Check Runs exist; they are not this slice. |

---

## Frozen contract (FastAPI unchanged)

| Item | Frozen value |
| --- | --- |
| Intake | `POST /webhooks/github` |
| Auth | `verify_webhook_signature` **first** (`X-Hub-Signature-256` over **raw** body), then `parse_pull_request_event` |
| Missing / not `sha256=` | HTTP **401** `{"detail":"missing or malformed webhook signature"}` |
| Signed unsupported event (e.g. `ping`) | HTTP **200** `{"accepted": false, "reason": "ignored-event"}` |
| HMAC input | Raw bytes + `TRUST_CI_WEBHOOK_SECRET`. **Not** Host, public URL, or `TRUST_CI_PUBLIC_BASE_URL`. |
| Publish | Loopback `127.0.0.1:18080` → container 8080 |
| Public webhook URL (after 401) | `https://claw.taild9f611.ts.net/webhooks/github` (no trailing slash) |
| App / repo hook registration | **Out.** Do not PATCH `/app/hook/config`. Do not `gh api …/hooks`. |
| M0.2 | Stays incomplete. Plan checkbox stays `[ ]` **not done**. |
| `main` | Unprotected. Do not `branch-protect`. |

Unsigned proof (`X-GitHub-Event: ping`, body `{}`, **no** signature) hits 401 **before** the parser. That is intended. It is **not** ignored-event 200.

Do not edit `trust-ci/src/**`, `trust-ci/compose.yaml`, or gitignored `env/*.env`.

---

## Dual path (mount strip)

Public request:

```text
GitHub App  →  POST https://claw.taild9f611.ts.net/webhooks/github
               Tailscale Funnel (TLS)
            →  http://127.0.0.1:18080/webhooks/github
               FastAPI HMAC
```

`--set-path=/webhooks/github` is the **public mount**. Funnel **strips** that prefix before proxying. Target `http://127.0.0.1:18080` (no path) would hit FastAPI `/` → **404**, not HMAC 401. Target **must** include `/webhooks/github`.

Do not add a trailing slash (FastAPI `redirect_slashes` can 307 POST and drop the body).

Do not Funnel `/` (would publish health/metrics/jobs). Do not Funnel `/approvals` this slice (not in the user command).

HMAC-safe: Funnel is a reverse proxy; HMAC is payload bytes, not framing. Do not add `--proxy-protocol`, body filters, or a second terminator.

---

## Exact host commands

User-named Funnel add is the **only** host write. Route `human_gates` is empty; the verbatim command is the operational consent for **these lines only** (status, add-path, proof curls). It is not consent for App PATCH, env recreate, `compose down -v`, `funnel reset`, Apache, or `branch-protect`.

### 0. Preflight (read-only)

```bash
sudo tailscale funnel status --json
sudo tailscale funnel status
curl -i http://127.0.0.1:18080/health/live
```

Expect live **200**. Record whether `/webhook` is present. **Do not reset** even if status is empty (`{}` / “No serve config” is the current fact).

If `health/live` is not 200: **stop**. Do not Funnel a down API.

If Funnel already has `/webhooks/github`: skip add; go to proof.

If add would require wiping other paths: **stop**. Do not `reset`. Do not `443 on`.

### 1. Add path only (user exact)

```bash
sudo tailscale funnel --bg --https=443 \
  --set-path=/webhooks/github \
  http://127.0.0.1:18080/webhooks/github
```

**Forbidden:**

```bash
sudo tailscale funnel reset
sudo tailscale funnel --bg 443 on
```

`443 on` is the old TikTok RUNBOOK enable; it can overwrite the **root** handler. The modern command with a target creates the handler and enables Funnel.

If the CLI says `funnel not allowed`: **stop**. Do not edit tailnet ACL from this repository.

### 2. Confirm

```bash
sudo tailscale funnel status
```

Expect `/webhooks/github` → `http://127.0.0.1:18080/webhooks/github`. If `/webhook` was present in step 0, it **must still be present**. If it vanished: **stop**; do not `reset` to “fix”.

If Funnel was empty, adding this path does **not** restore n8n. Restoring n8n is **out of this slice**.

### 3. Proof (live evidence, not CI)

```bash
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-GitHub-Event: ping' \
  --data '{}' \
  https://claw.taild9f611.ts.net/webhooks/github
```

Expect:

```text
HTTP/2 401
missing or malformed webhook signature
```

Store the **status line + body snippet** under this change package `evidence/` (no secrets). That file is the host receipt. **Do not** add a unittest that HTTP-probes `claw.taild9f611.ts.net`.

If TLS fails or the response is not FastAPI JSON 401: **stop**. Do not write operator docs that name the URL as live. Do not PATCH GitHub.

Optional loopback sanity (not a substitute for the public 401):

```bash
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-GitHub-Event: ping' \
  --data '{}' \
  http://127.0.0.1:18080/webhooks/github
```

Same 401 proves FastAPI HMAC independently of Funnel.

---

## `TRUST_CI_PUBLIC_BASE_URL` — leave loopback this slice

User did not list env recreate. HMAC does not read the public base (`webhooks.py` uses secret + raw body only). `public_base_url` is Check Run `details_url` `{base}/jobs/{id}` (`runner.py`).

| Location | This slice |
| --- | --- |
| gitignored `trust-ci/env/common.env` | **Leave** `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. No `sed`. No `force-recreate`. |
| Activation-report table cell | **Leave** `http://127.0.0.1:18080`. |
| After unsigned 401 | Operator docs name the **webhook URL** `https://claw.taild9f611.ts.net/webhooks/github`. Do **not** put the webhook path in the public-base cell. Do **not** set public base to `https://claw.taild9f611.ts.net` this slice. |

**Overrule** sibling `docs_researcher` on flipping the activation-report `TRUST_CI_PUBLIC_BASE_URL` cell this slice. That flip implies api **and** worker recreate so new Check Runs get HTTPS `details_url`. Not required for HMAC or unsigned 401. A later named slice may sed + recreate after the edge is proven.

`https://claw.taild9f611.ts.net` **would** be a legal `CommonSettings` public form (HTTPS outside localhost). `http://claw.taild9f611.ts.net` would crash api/worker. Do not use HTTP public. Do not set it now.

---

## Product files (only after unsigned 401)

Do **not** land docs that claim the Funnel URL is live before the 401. Characterization tests go **with** those docs in the same tree so `grok_verify` is green.

### Required (write owner)

| File | Change |
| --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | After docs: assert `https://claw.taild9f611.ts.net/webhooks/github` appears in operator docs that name the public webhook URL (`PLAN`, `REPORT`, `DECISIONS` — not a live HTTP client). Keep `local HMAC` and (`not done` **or** `no public HTTPS`). Keep `ii-tonya` negative scan. **Do not** GET/POST the Funnel host from unittest. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Keep M0.2 webhook `[ ]`. Reword “repo webhook” / “no public HTTPS” so the line still says **not done** (App hook unregistered) and names `https://claw.taild9f611.ts.net/webhooks/github`. Do **not** `[x]`. Do **not** drop both `not done` and `no public HTTPS`. |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Host TLS for **this path** is Funnel, not Apache. Rollout step 2 (register webhook) stays **later**. Keep “M0.2 incomplete”. |
| `engineering/runbooks/trust-ci-activation-report.md` | Add an operator-safe row/note: public webhook URL = `https://claw.taild9f611.ts.net/webhooks/github` (unsigned 401; **App hook unregistered**). **Do not** change the `TRUST_CI_PUBLIC_BASE_URL` cell. Keep `main protected = false`. |
| `decisions.md` | ≤3-sentence 2026-08-24 entry: named public HTTPS path is Funnel `https://claw.taild9f611.ts.net/webhooks/github`; dual path because Funnel strips mount; HMAC unchanged; leave public base loopback this slice; never `funnel reset`. «Приложуха» remains the GitHub App, not Funnel. |

### This change package (fill stubs; not the invariant scan)

`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `rollback.md`, `release.md`, `tasks.md`, `change-spec.yaml`. Store the live 401 snippet under `evidence/` (no secrets).

### Do not change

- `trust-ci/src/adaptive_trust_ci/api.py`, `webhooks.py`, `settings.py`, `runner.py`, `worker.py`
- `trust-ci/compose.yaml`, untracked host-socket overlay
- gitignored `trust-ci/env/common.env` / `api.env` / `worker.env`
- `trust-ci/tests/test_api.py`, `test_webhooks_github.py` (HMAC already covered; no public HTTP probe)
- Host Apache leftover, n8n Caddy, SearXNG `:8080`
- GitHub App webhook config, repository hooks, `branch-protect`, leftover Actions workflow
- VERSION / CHANGELOG / README stack graph (not a release)
- Sibling `engineering/changes/**` (ChatGPT hostname evidence stays historical)

---

## Tests

| Kind | What | Where |
| --- | --- | --- |
| P0 live | Unsigned Funnel POST → HTTP 401 FastAPI JSON | Host curl; evidence file; **not** CI |
| P0 unit (existing) | HMAC missing/malformed/invalid → `WebhookError` / API 401 | `test_webhooks_github.py`, `test_api.py` — **do not rewrite** |
| P0 characterization (new, after 401 + docs) | Operator docs contain `https://claw.taild9f611.ts.net/webhooks/github`; plan still `not done` / local HMAC; no `ii-tonya` in the five-doc scan | `test_m0_invariants.py` |
| Out | unittest `requests`/`urllib` to `claw.taild9f611.ts.net` | Forbidden |

---

## Rollback (path only)

Trigger: Funnel 502/404 instead of HMAC 401; n8n `/webhook` disappeared; user abort.

CLI **allows** removing one mount without reset (`off`; original flags required; target optional):

```bash
sudo tailscale funnel --https=443 --set-path=/webhooks/github off
```

Equivalent (target optional):

```bash
sudo tailscale funnel --https=443 --set-path=/webhooks/github \
  http://127.0.0.1:18080/webhooks/github off
```

Then:

```bash
sudo tailscale funnel status
curl -fsS http://127.0.0.1:18080/health/live
```

**Never:**

```bash
sudo tailscale funnel reset
sudo tailscale funnel --https=443 off
```

Bare `--https=443 off` drops **all** 443 mounts (including n8n `/webhook` if restored later). `reset` wipes Serve/Funnel entirely.

Leave FastAPI, compose, env, Apache leftover, and n8n container as they were. After rollback, public POST to the Funnel webhook URL must not reach FastAPI.

---

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User | Funnel command + dual path; no reset; keep n8n `/webhook` | **Binding.** Execute add-path only. |
| User / this question | FastAPI unchanged; leave public base; no App PATCH; no M0.2 complete | **Binding.** |
| Sibling explorer | Funnel `{}`; n8n `/webhook` absent; loopback 200 | **Wins on facts.** Add github path anyway; do not restore n8n; do not reset. |
| Sibling docs_researcher | After 401, set activation-report `TRUST_CI_PUBLIC_BASE_URL` to `https://claw.taild9f611.ts.net` | **Overruled this slice.** Name the **webhook URL** in docs; leave the public-base **cell and env** on loopback. Recreate is extra risk and not required for HMAC. |
| Spec Host | TLS reverse proxy to `/webhooks/github` **and** `/approvals` | Funnel **webhook path only** this slice. `/approvals` stays loopback. |
| Spec/plan | Register webhook; “no public HTTPS” | Unsigned 401 ≠ registration. Keep `[ ]` **not done**. After 401, drop stale “no public HTTPS” **only if** `not done` remains. |
| Prior Apache slice / leftover | Apache as public TLS | **Superseded for this path.** User named Funnel. Leave Apache leftover untouched. |
| n8n TikTok RUNBOOK | `funnel --bg 443 on` + `--set-path=/webhook` without dual target | **Do not run `443 on`.** Do not restore n8n here. Dual-path rule is for FastAPI. |
| `AGENTS.md` | No production write without named grant; no GitHub Actions | Funnel add is the named host write. No App PATCH. No `.github/workflows`. |

---

## Out of scope (explicit)

- FastAPI / compose / env recreate / `TRUST_CI_PUBLIC_BASE_URL` HTTPS switch
- Apache / Caddy / nginx / Certbot / DNS A for any other hostname
- `tailscale funnel reset` or `443 on`
- Restoring n8n `/webhook` (operator may re-add later **without** reset; not this slice)
- Funnel `/` or `/approvals` or `/health/*`
- GitHub App webhook PATCH / repository webhook
- Claiming M0.2 complete; `branch-protect`; merge; tag; VERSION
- Reading or committing PEM, webhook secret, App RSA, human approval keys
- CI HTTP probe of the Funnel URL
- Publishing API on `0.0.0.0` or host `:8080`

---

## Success metric

1. `sudo tailscale funnel status` shows `/webhooks/github` → `http://127.0.0.1:18080/webhooks/github`.
2. Any pre-existing `/webhook` still present (today: none — do not invent it).
3. `GET http://127.0.0.1:18080/health/live` still 200; compose still loopback.
4. Unsigned `POST https://claw.taild9f611.ts.net/webhooks/github` → **HTTP 401** FastAPI `missing or malformed webhook signature`.
5. Operator docs (plan, activation report note, `decisions.md`) name that URL; `TRUST_CI_PUBLIC_BASE_URL` cell **and** env still `http://127.0.0.1:18080`.
6. `test_m0_invariants` asserts the URL in those docs and still sees **not done** / local HMAC.
7. No GitHub App hook PATCH; M0.2 unchecked; `main` unprotected; no `funnel reset`.

**Go/no-go:** Funnel path + unsigned 401 **GO**. App registration / M0.2 complete / public-base recreate / `main` protect **NO-GO**.
