# Security review — GitHub App webhook (no repo hook)

**Agent:** `security_reviewer` (read-only except this report; in route `allowed_agents`)  
**Route:** `cec0c7622133`  
**Change:** `20260824-configure-github-app-webhook-pull-request-https-cec0c7`  
**HEAD:** `92ddbd9f69c5c560f257fd61fa9c902f43f67e50` (this slice is untracked paperwork only)  
**Skills:** `/adaptive-delivery`, `/security-sensitive-change`, `/api-event-change`  
**This review is not merge authority.** Local receipts cannot create `adaptive-trust-ci/verified@<policy-sha12>`.

Did not read `.env`, `trust-ci/env/api.env`, `trust-ci/env/*.env`, `*.pem`, webhook secret values, JWTs, or installation tokens. Did not mint a GitHub App JWT. Did not `GET`/`PATCH /app/hook/config`. Did not `POST /repos/.../hooks`. Did not push, merge, or deploy.

## Verdict: **pass**

`write_agent: none`. No product code was modified. Analysis correctly refused the App PEM/JWT path and did not substitute a repository webhook. Intended GitHub App SSL verification stays **Enabled** (`insecure_ssl=0`); nobody proposed or applied `insecure_ssl=1`.

| Confirmation | Result |
| --- | --- |
| PEM not read/printed | **PASS.** This reviewer did not open `trust-ci/runtime/github-app-private-key.pem` or any other PEM. Analysis reports (architect, explorer, integration, docs) state the same. Change package has no `-----BEGIN` blocks. `git ls-files '*.pem' '*.key'` is empty. Paths are gitignored (`*.pem`, `trust-ci/runtime/*`). |
| Webhook secret not read/printed | **PASS.** `trust-ci/env/api.env` was not opened. Evidence names the env **key** `TRUST_CI_WEBHOOK_SECRET` only. No JWT (`eyJ…`), `ghp_`/`github_pat_`, or `sha256=<64 hex>` bodies in this package. Example file still uses `REPLACE_WITH_LONG_RANDOM_SECRET`. |
| No repository webhook created | **PASS.** Independent `gh api repos/Dimkox/adaptive-grok-build-pro/hooks` this review: length **0**, empty list. jq projected only `id/name/active/events/url/insecure_ssl` — no `config.secret`. Architect/integration: do not `POST /repos/.../hooks`. |
| SSL verification remains enabled | **PASS.** Required mapping is UI Enabled / API `insecure_ssl="0"`. Architect forbidden list includes `insecure_ssl=1`. No `/app/hook/config` mutation ran, so GitHub SSL verification was not lowered. TLS-off probes of the public edge are **not** GitHub `insecure_ssl`. |

**Local security review: pass.** Do not treat App UI “Active” or loopback HMAC as live GitHub delivery. Do not merge on this receipt.

---

## Scope inspected

Change package (this slice): brief, requirements, architecture, analysis reports, code-review, test-review.

Surrounding implementation (read-only, **not** modified by this route): `trust-ci/src/adaptive_trust_ci/{api,webhooks,policy,settings}.py`, `trust-ci/compose.yaml`, `trust-ci/env/{api,worker}.env.example`, `.gitignore`, `trust-ci/holdout.example/validate.py`. Filename-only ignore check for `trust-ci/env/api.env` and runtime PEMs (bodies not opened).

Live GitHub: `GET repos/Dimkox/adaptive-grok-build-pro/hooks` (read-only).

---

## 1. Secrets and credential handling

**Assets in scope:** GitHub App RSA (`github-app-private-key.pem`), App JWT, `TRUST_CI_WEBHOOK_SECRET`, installation tokens, CI signing key.

**Findings:**

- `PATCH /app/hook/config` requires an App JWT signed with the App private key. `AGENTS.md` and this route forbid reading that PEM. Architect ruling: user token and installation token cannot call `/app/hook/*`. The operator UI is the only allowed config path.
- API holds the webhook secret (`ApiSettings.webhook_secret` ← `_required('TRUST_CI_WEBHOOK_SECRET')` from gitignored `api.env`). Worker env example has App ID / installation ID / PEM path and `TRUST_CI_ROLE=worker` — **no** webhook secret. Compose mounts App RSA + CI signing key on **worker only**; API mounts trust-store public material only. Holdout: `GitHubAppAuth` must not appear in API source.
- `.gitignore` covers `.env`, `*.pem`, `*.key`, `trust-ci/env/*.env`, `trust-ci/runtime/*`. Tracked env files are `*.example` placeholders only.
- Explorer grepped `TRUST_CI_PUBLIC_BASE_URL` in `common.env` (URL `http://127.0.0.1:18080`, not a secret) and explicitly did **not** open `TRUST_CI_WEBHOOK_SECRET`.

**Abuse case blocked:** an agent that `cat`s `api.env` or the PEM to fill the App form would leak credentials into chat/evidence. Requirements forbid that. Operator pastes the secret themselves.

---

## 2. Authorization (webhook intake)

Unchanged product contract (no FastAPI edit this slice):

1. HMAC-SHA256 over **raw body** vs `X-Hub-Signature-256` (`hmac.compare_digest`) — fail-closed **401** if missing, malformed, or wrong.
2. Then parse `X-GitHub-Event`. Non-`pull_request` (including signed `ping`) → HTTP **200** `ignored-event`.
3. Then `policy.allows_repository(repository.full_name)` — foreign repo **403**.
4. Kill switch → **503**. Duplicate identity reuses the job row.

GitHub App deliveries use the same HMAC header as repository hooks. Extra App fields (`installation`, extra headers) are ignored. Empty secret is rejected (`webhook secret is not configured`).

Unsigned public POST currently returning **405 nginx** (sibling/explorer) means the public name has **not** reached FastAPI. That is an edge gap, not an HMAC bypass. GitHub SSL-enabled deliveries will not POST until the cert SAN includes `trust-ci.ii-tonya.ru`.

---

## 3. Tenant isolation

`allows_repository` is exact membership in `allowed_repositories`. App-level webhook delivers every installation; HMAC authenticates GitHub, not a tenant. Isolation after HMAC is the policy allowlist. A second installation on a non-allowlisted repo is **403** (GitHub signs `repository.full_name`; the attacker cannot forge another repo’s name without the HMAC secret).

Not consuming `installation.id` this slice is defense-in-depth leftover, not a fail: GitHub-signed payloads already bind `full_name`. Do not add a repo hook “for isolation” — that would double-deliver.

API bind remains `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. Public GitHub cannot hit loopback; the public HTTPS origin is independent of `TRUST_CI_PUBLIC_BASE_URL`.

---

## 4. PII

GitHub `pull_request` payloads can contain logins and emails. The adapter keeps `repository.full_name`, PR number, and SHAs/refs only. This slice does not log raw bodies or paste payloads into evidence. Public identifiers (App slug `adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`, host `trust-ci.ii-tonya.ru`) are not secrets.

---

## 5. Irreversible / production actions

| Action | This slice |
| --- | --- |
| Create repository webhook | **Not done.** Hooks list empty. Forbidden as a JWT workaround. |
| `PATCH /app/hook/config` | **Not done.** JWT/PEM forbidden. Operator UI only. |
| Set `insecure_ssl=1` | **Forbidden and not applied.** Would disable GitHub’s TLS check to paper over the parent-domain cert (`CN=ii-tonya.ru`, SAN lacks `trust-ci.ii-tonya.ru`). |
| Protect `main` | Out of scope. Not done. |
| Read/print PEM or webhook secret | Not done (see table). |
| Push / merge / deploy | Not done. |

Creating a repo hook to the same URL would duplicate producers (idempotency prevents a second job, still wastes deliveries and splits secrets). Disabling SSL verification would let a MITM present any cert to GitHub. Both remain blocked.

---

## Residual (not a fail for this review)

- App hook Active / URL / `pull_request` / secret equality: **unverified** without operator UI or a forbidden App JWT.
- Public TLS: hostname mismatch; GitHub SSL-enabled deliveries will fail until the cert covers `trust-ci.ii-tonya.ru`.
- Unsigned public POST: **405** nginx, not FastAPI **401**. Edge is not Trust CI yet.
- M0.2 stays incomplete until GitHub actually delivers a signed `pull_request`. UI Active ≠ delivery. Loopback HMAC is not this slice.
- Named human gate `scope_and_design_approval`: operator owns the App settings form and cert/vhost. Agents do not.

---

Local receipt (parent, after this report):

```bash
python3 scripts/grok_review.py security_review --status pass --report engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7/evidence/security-review.md
```
