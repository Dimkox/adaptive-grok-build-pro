# Architect ruling — GitHub App webhook config (route 2cd446440734)

Change: `engineering/changes/20260824-user-query-настраивай-app-user-query-2cd446`  
Write owner: `general_implementer`. This agent is read-only except this report.

Did not read `.env`, `trust-ci/env/api.env`, `trust-ci/runtime/github-app-private-key.pem`, webhook secret values, JWTs, or installation tokens. Did not mint a JWT. Did not `GET`/`PATCH /app/hook/config`. Did not `POST /repos/.../hooks`. Did not Funnel reset. Did not edit FastAPI. Did not print `TRUST_CI_WEBHOOK_SECRET`. Did not push, merge, or deploy.

Sources: GitHub REST `PATCH /app/hook/config` (“You must use a JWT”), GitHub “Modifying a GitHub App registration” / “Viewing webhook deliveries”, sibling `analysis-repo_explorer.md` and `analysis-docs_researcher.md`, Funnel slice `813a02` host receipts, `trust-ci/src/adaptive_trust_ci/{api,webhooks,github,github_app}.py`, `trust-ci/tests/test_m0_invariants.py`.

## Ruling

**UI-only. `PATCH /app/hook/config` is impossible under the named constraints.** GitHub documents JWT-only access. Live `gh api /app` and `gh api /app/hook/config` with the current user token both return **401** `A JSON web token could not be decoded`. `AGENTS.md` forbids reading the App PEM, so this write owner must not mint a JWT. Installation tokens (worker) cannot call `/app/hook/*`. Do not create a repository webhook as a substitute (repo hooks already `[]`). Do not Funnel reset. Do not change FastAPI. Do not print `TRUST_CI_WEBHOOK_SECRET`.

**The write owner must stop the API path and hand the operator the exact GitHub App settings UI checklist below. Do not fake success.** UI “Active” and naming the Funnel URL in docs are not live GitHub delivery. Live delivery exists only when App settings → **Advanced → Recent deliveries** shows a signed `ping` (HTTP 200 `ignored-event`) or `pull_request` (HTTP 200 `accepted`) to `https://claw.taild9f611.ts.net/webhooks/github`.

Optional smallest product change (same tree as a failing characterization, then the docs): operator docs **name** that Funnel URL as the **App webhook URL**, while still saying **not done** / App hook pending UI / no Recent Deliveries. That is documentation, not configuration.

---

## 1. Why the API path is closed

GitHub REST (`docs.github.com/en/rest/apps/webhooks`):

```text
GET    /app/hook/config          # JWT required
PATCH  /app/hook/config          # JWT required
GET    /app/hook/deliveries      # JWT required
GET    /app/hook/deliveries/{id} # JWT required
POST   /app/hook/deliveries/{id}/attempts  # JWT required
```

`PATCH` body is only `url`, `content_type`, `secret`, `insecure_ssl`. It does **not** set Active and does **not** subscribe events.

JWT mint is `generate_app_jwt` in `github_app.py`: RS256, `iss` = App ID, signed with PEM `read_bytes()`. That is the forbidden path.

| Credential | `PATCH /app/hook/config` | This slice |
| --- | --- | --- |
| App JWT from `github-app-private-key.pem` | Yes (documented) | **Forbidden.** No PEM read, no JWT mint. |
| Current `gh` user/OAuth token | **No.** 401 JWT decode (sibling explorer, this route). | Do not retry. Do not request a `github-api` grant to work around PEM. |
| Installation token (worker) | **No.** Repo-scoped `checks`/`contents`/`pull_requests`. | Worker-only; API must not hold it. |
| Fine-grained / classic PAT | **No** for `/app/hook/*`. | Must **not** be used to `POST /repos/{owner}/{repo}/hooks`. |

Tracked `trust-ci/` has **no** `/app/hook/*` client. `github.py` PATCHes only `/repos/{repo}/check-runs/{id}`. `GitHubAppAuth` POSTs only `/app/installations/{id}/access_tokens`. Do not add a hook-config client.

Even a later human-minted JWT outside this environment is **not** this write owner’s job. This route has no grant to call GitHub App admin APIs.

---

## 2. Live facts (this host, not GitHub-applied)

| Plane | Fact |
| --- | --- |
| App | slug `adaptive-trust-ci`, public `https://github.com/apps/adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193` |
| Intended webhook URL | `https://claw.taild9f611.ts.net/webhooks/github` (no trailing slash) |
| Funnel | **Up.** `/webhooks/github` → `http://10.200.200.1:18080/webhooks/github` (docker-proxy to `127.0.0.1:18080`). Do **not** reset. Do **not** rewrite the target to “fix” `10.200.200.1`. |
| Unsigned public ping | Slice `813a02`: HTTP/2 **401** FastAPI JSON `missing or malformed webhook signature` (`evidence/unsigned-ping-401.txt`). Edge is Trust CI HMAC, not nginx 405. |
| TLS | Tailscale Funnel cert for `claw.taild9f611.ts.net` (dns-01). SSL verification **Enabled** is expected to verify (unlike the voided ChatGPT hostname). |
| Repo hooks | `GET repos/Dimkox/adaptive-grok-build-pro/hooks` → `[]`. Keep empty. |
| App hook | **Unverified.** User token cannot `GET /app/hook/config`. No Recent Deliveries observed from this agent. |
| `TRUST_CI_PUBLIC_BASE_URL` | Leave `http://127.0.0.1:18080` (Check Run `details_url`, not inbound webhook). |
| FastAPI | HMAC first on `POST /webhooks/github`. **Do not change.** |
| M0.2 | Incomplete. Plan checkbox stays `[ ]`. Loopback HMAC Check Runs are not this slice. |

Path (already live at the edge, not at GitHub):

```text
GitHub App  --(not yet)--►  POST https://claw.taild9f611.ts.net/webhooks/github
                            Tailscale Funnel TLS
                         ►  http://10.200.200.1:18080/webhooks/github
                         ►  FastAPI HMAC (127.0.0.1:18080)
```

Do not Funnel `/`. Do not Funnel `/approvals` this slice. Do not add a trailing slash.

---

## 3. Exact GitHub App settings UI checklist (write owner stops here)

The agent cannot save these fields. The **App owner** (or App manager) does, in a browser session. Direct edit URL (personal-account owner):

`https://github.com/settings/apps/adaptive-trust-ci`

Org-owned equivalent (only if the App is org-owned):

`https://github.com/organizations/<org>/settings/apps/adaptive-trust-ci`

Public app page (not the form): `https://github.com/apps/adaptive-trust-ci`.

### Navigate (GitHub docs: Modifying a GitHub App registration)

1. Profile picture → **Settings** (personal) or **Your organizations** → org **Settings**.
2. Left sidebar → **Developer settings** → **GitHub Apps**.
3. To the right of **adaptive-trust-ci** → **Edit**.

### General → Webhook (save this page)

| UI field | Required value | Notes |
| --- | --- | --- |
| **Active** | **Checked** | App-registration field. Not in `PATCH /app/hook/config`. If inactive, **Recent deliveries** section is absent. |
| **Webhook URL** | `https://claw.taild9f611.ts.net/webhooks/github` | Exact. HTTPS. No trailing slash. Not `http://127.0.0.1:18080`. Not `trust-ci.ii-tonya.ru`. Not a repository Settings → Webhooks URL. |
| **Webhook secret** | same bytes as host API `TRUST_CI_WEBHOOK_SECRET` | Operator pastes from gitignored `trust-ci/env/api.env` **themselves**. Agent must not `cat`/`echo`/`grep`/print/commit it. |
| **SSL verification** | **Enabled** | API equivalent `insecure_ssl="0"`. Do **not** disable to paper over TLS. Funnel already served a public 401 over HTTPS. |
| Content type | `application/json` if shown | GitHub Apps serialize JSON. Repo-hook “Content type” dropdown is the wrong form. |

Click **Save changes**. Saving an Active URL triggers GitHub `ping`.

### Permissions & events (separate save)

4. Sidebar → **Permissions & events**.
5. Do **not** change repository permissions this slice (already Checks read/write, Contents read, Pull requests read). Adding permissions emails installers.
6. Under **Subscribe to events**, check **Pull request** only.
7. Click **Save changes**.

`PATCH /app/hook/config` cannot subscribe events. Without **Pull request**, signed pings may 200 `ignored-event` while real PR jobs never enqueue.

Do **not** subscribe `push`, `check_run`, or all events.

### Recent deliveries (proof GitHub actually POSTed)

8. Sidebar → **Advanced**.
9. Under **Recent deliveries** (past 3 days). If webhooks are not Active, this section is missing — that is not success.
10. Click a delivery GUID.

| Event | FastAPI (after HMAC) | GitHub delivery |
| --- | --- | --- |
| `ping` (sent on URL save) | HTTP **200** `{"accepted":false,"reason":"ignored-event"}` | **Green / 200** |
| `pull_request` opened/synchronize/reopened/ready_for_review (drafts enqueue) | HTTP **200** `accepted: true`, `job_id` | **Green / 200** |
| Missing/wrong secret | HTTP **401** `missing or malformed webhook signature` / `invalid webhook signature` | Failed delivery |
| TLS/SSL | n/a | SSL error — do not set SSL Disabled |

**Success for this operator action** is a Recent Deliveries row for `ping` with status **200**, URL the Funnel path above. **Not** success: form saved, docs updated, loopback HMAC Check Run, unsigned Funnel 401 (already proven).

**Do not** open `https://github.com/Dimkox/adaptive-grok-build-pro/settings/hooks` and Add webhook.

---

## 4. Optional smallest product change (docs characterization only)

If the write owner lands anything in git, it is **naming**, not applying, the App webhook URL. Characterization first, then docs, same tree.

Keep M0.2 incomplete. Keep `local HMAC` in the plan. Keep (`not done` **or** `no public HTTPS`). Keep `ii-tonya` negative scan. Leave `TRUST_CI_PUBLIC_BASE_URL` cell and gitignored env on loopback.

### Exact files (optional)

| File | Change | Do not |
| --- | --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | Assert operator docs that name the App webhook URL contain `https://claw.taild9f611.ts.net/webhooks/github`. Keep ChatGPT-host negative scan. **No** HTTP client to Funnel. | Probe GitHub or Funnel from unittest |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Keep `[ ]`. Reword repo webhook → **GitHub App** webhook `POST https://claw.taild9f611.ts.net/webhooks/github` — **not done** (App hook pending operator UI; Funnel path exists; no Recent Deliveries). Preserve `local HMAC`. | `[x]`; claim M0.2 complete |
| `engineering/runbooks/trust-ci-activation-report.md` | Prose/row: App webhook URL named Funnel path; **not** a GitHub-registered delivery. **Leave** `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`. | Flip public-base cell |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Rollout step 2: App webhook (not repo), later until Recent Deliveries. Keep M0.2 incomplete. TLS for this path is Funnel. | Treat UI save as live authority |
| `decisions.md` | ≤3 sentences: App webhook is UI-only without PEM; Funnel URL is the only named origin; not live until Recent Deliveries; loopback `details_url` stays. | Second hostname; JWT as success path |
| `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, `QUICKSTART.md` | Optional: “GitHub App webhook” not “repository webhook”; example may stay `ci.example.com` **or** the Funnel URL. | Require a repo hook; invent a host |
| This change package stubs | JWT-stop + UI checklist; no secrets. | Claim App configured |

### Do not change

- `trust-ci/src/**` (`api.py`, `webhooks.py`, `settings.py`, `github.py`, `github_app.py`, `worker.py`, `runner.py`)
- `trust-ci/compose.yaml`, untracked host-socket overlay
- gitignored `trust-ci/env/*`, PEM, trust-store
- Funnel (`reset`, `443 on`, path `off`, target rewrite)
- Repo webhooks, `branch-protect`, `.github/workflows/**`
- VERSION / CHANGELOG / README K16 graph (not a release)
- Sibling `engineering/changes/**` history

---

## 5. Frozen intake contract (unchanged)

```text
POST /webhooks/github
Content-Type: application/json
X-GitHub-Event: pull_request | ping | (other → ignored-event)
X-Hub-Signature-256: sha256=<hex>
```

HMAC over **raw** body + `TRUST_CI_WEBHOOK_SECRET`. Missing/malformed → **401**. Signed non-PR → **200** `ignored-event`. Draft `opened` enqueues. Idempotent on `(repository, pr, head_sha, policy_digest)`.

---

## 6. Forbidden vs allowed

**Forbidden (write owner and this agent)**

- Read PEM / `.env` / `api.env` / print `TRUST_CI_WEBHOOK_SECRET`.
- Mint JWT; `GET`/`PATCH /app/hook/config`; `GET /app/hook/deliveries*`.
- `POST /repos/Dimkox/adaptive-grok-build-pro/hooks` (or org hooks).
- `tailscale funnel reset`; Funnel `--bg 443 on`; Funnel path `off` except true rollback of a **this-slice** Funnel mutation (this slice must not mutate Funnel).
- FastAPI / compose / env edits.
- `insecure_ssl=1` / SSL verification Disabled.
- Claim App webhook live, M0.2 complete, protect `main`, merge, tag, deploy.

**Allowed**

- Stop and publish the UI checklist (this report).
- Optional docs + `test_m0_invariants` characterization as in §4.
- Operator (human browser): save the App form; later confirm Recent Deliveries.

---

## 7. Rollback / residual

No GitHub mutation from this agent, so nothing to roll back on GitHub. If the operator saved the form and must undo: same UI, set Webhook URL empty / Active off, Save — **operator only**. Do not Funnel reset.

Residual: App hook Active/URL/secret/events **unverified** (JWT forbidden). Funnel unsigned 401 is **edge** proof, not GitHub delivery. Write owner success for this route is an honest **JWT-stop** plus optional docs naming — never a fake “App configured” receipt.

## Return

**UI-only.** API `PATCH /app/hook/config` is not possible under no-PEM / no-JWT / user-token 401.

**Exact files if any (optional characterization only):** `trust-ci/tests/test_m0_invariants.py`, `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `engineering/runbooks/trust-ci-activation-report.md`, `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`, `decisions.md`, optionally `trust-ci/README.md` / `engineering/runbooks/trust-ci-rollout.md` / `QUICKSTART.md`. **No** `trust-ci/src/**`.
