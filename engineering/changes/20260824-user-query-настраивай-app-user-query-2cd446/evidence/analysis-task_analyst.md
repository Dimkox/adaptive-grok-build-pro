# task_analyst — GitHub App webhook (route `2cd446440734`)

Change: `engineering/changes/20260824-user-query-настраивай-app-user-query-2cd446`  
Write owner: **`general_implementer`**. This agent does not implement, push, merge, read PEM/`.env`/webhook secret, mint JWT, `PATCH /app/hook/config`, or create a repository webhook.

User order: «настраивай app» = configure **GitHub App** `adaptive-trust-ci` webhook (not a website, not a repo hook).

## Ruling: in-scope outcome is **(a)**

**If API is impossible without PEM, the in-scope outcome is (a):** stop GitHub mutation with **exact UI fields** for the operator to Save, then write **operator-docs after they confirm**. It is **not (b)**.

«Настраивай» is a request to finish the live App hook. The agent cannot complete that mutation. GitHub REST documents `GET`/`PATCH /app/hook/config` as **JWT-only**. Sibling `analysis-repo_explorer.md` on this route: `gh api /app` and `gh api /app/hook/config` return **401** `A JSON web token could not be decoded`. `AGENTS.md` forbids reading the App PEM, so this agent must not mint a JWT. A user token, installation token, GitHub MCP session, and `gh` OAuth session **cannot** substitute.

The configuration action that fulfills «настраивай» is **the operator clicking Save** on the App registration page. Agent-completable work is the field card now, then docs/tests after that confirmation. Pretending PATCH succeeded, asking for the PEM, or creating a repo hook is failure.

## Observable outcome

GitHub App `adaptive-trust-ci` (`https://github.com/apps/adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`) receives **Pull request** events at:

`https://claw.taild9f611.ts.net/webhooks/github`

HMAC secret matches API env key `TRUST_CI_WEBHOOK_SECRET` (value never in git/chat/this package). SSL verification **Enabled**. No repository webhook. Funnel already proxies that path (this-route explorer; unsigned FastAPI **401** proven in sibling `813a02`).

Until the operator confirms Save, **no agent may claim the hook is live**. Until a **signed GitHub** `pull_request` (or `ping`) delivery is observed on FastAPI, M0.2 stays incomplete.

## Why API cannot be the delivery path

| Credential | `PATCH /app/hook/config`? | Agent may use? |
| --- | --- | --- |
| GitHub App JWT from App RSA PEM | **Yes** (docs: “You must use a JWT”) | **No** — PEM read and JWT mint forbidden |
| User / OAuth / `gh` token | **No** — 401 JWT decode (this route) | Cannot configure App hook |
| Installation token (`GitHubAppAuth` → `POST /app/installations/{id}/access_tokens`) | **No** — installation scope, not App hook | Worker-only; holdout forbids API holding the PEM |
| GitHub MCP | No App hook tool; repo-hook tools would be a substitute | **No** |

`PATCH` body is only `url`, `content_type`, `secret`, `insecure_ssl`. It does **not** set Active and does **not** subscribe events. Events live under App **Permissions & events**. Product code has **no** `/app/hook/*` client (`github.py` Check Runs only). Do not add one this slice.

GitHub MCP `create_or_update_file` / Tasks GitHub triggers are **not** App webhook config. Do not use them as a workaround.

## Exact UI fields (operator Save)

Open (personal-account App owner):

`https://github.com/settings/apps/adaptive-trust-ci`

If org-owned: `https://github.com/organizations/<org>/settings/apps/adaptive-trust-ci`  
(GitHub: Settings → Developer settings → GitHub Apps → **Edit** `adaptive-trust-ci`.)

### Webhook (same page, “Webhook”)

| UI field | Value | Notes |
| --- | --- | --- |
| **Active** | Checked | Enables deliveries. Not a `PATCH /app/hook/config` field. |
| **Webhook URL** | `https://claw.taild9f611.ts.net/webhooks/github` | HTTPS, **no trailing slash**, path kept so Funnel + FastAPI both see `/webhooks/github`. Do **not** use `trust-ci.ii-tonya.ru` or loopback. |
| **Webhook secret** | paste host `TRUST_CI_WEBHOOK_SECRET` | Operator reads gitignored `trust-ci/env/api.env` on `claw`. Agent never prints, cats, greps, or pastes the value. |
| **SSL verification** | **Enabled** | API equivalent `insecure_ssl="0"`. Do not disable to paper over TLS. Funnel TLS is already serving this hostname (unsigned 401 JSON from uvicorn). |
| Content type (if shown) | `application/json` / `json` | Apps send JSON; UI may omit this. |

Then **Save changes**.

### Permissions & events (sidebar)

| UI field | Value |
| --- | --- |
| **Subscribe to events** | **Pull request** only for this slice |
| Permissions | Do **not** add new permission scopes unless “Pull request” is greyed out (then Pull requests Read is the minimum; extra scopes are a later named change) |

Do **not** open repository Settings → Webhooks. Explorer listed `GET /repos/Dimkox/adaptive-grok-build-pro/hooks` = `[]`. Keep it empty.

After Save, GitHub sends a signed `ping`. Expected FastAPI: **200** with ignored-event (or equivalent success that is **not** unsigned 401). Unsigned operator curl staying 401 is still correct.

## In scope

1. **Stop** `GET`/`PATCH /app/hook/config`, JWT mint, PEM/`.env` reads, and repository webhook create.
2. Hand the operator the **exact UI card** above (this package). That is the agent’s completion of «настраивай» until Save.
3. After **operator confirmation that they Saved**, write-owner updates operator docs to name the Funnel URL as the **GitHub App** webhook (not a repo hook), still **not** M0.2-complete until signed GitHub delivery.
4. Characterization tests that: Funnel URL string appears once docs name it; M0.2 webhook line stays **not done** (or honest “App hook pending UI / not done”); `ii-tonya` stays absent from the invariant scan; docs do not instruct a repository webhook as the live path.
5. Optional same-tree reword of plan/README/rollout “repo webhook” → “GitHub App webhook” **without** ticking M0.2.

## Out of scope (not (b))

| Item | Why |
| --- | --- |
| Agent `PATCH /app/hook/config` | JWT required; PEM forbidden |
| Human pastes PEM/JWT into the agent so it can PATCH | Same prohibition; still an external GitHub write |
| Repository webhook (`POST /repos/…/hooks`) | User + `decisions.md`: config lives on the App |
| Print / commit `TRUST_CI_WEBHOOK_SECRET` | Secret is API-only; name the env key only |
| `insecure_ssl=1` / SSL verification Disabled | User required Enabled |
| FastAPI / compose / gitignored env / Funnel reset | Edge already proven; HMAC already first |
| Flip `TRUST_CI_PUBLIC_BASE_URL` off loopback | Check Run `details_url` origin; later named slice |
| Claim M0.2 complete, protect `main`, branch-protect, GitHub Actions | Remaining M0.2/M0.3 work |
| ChatGPT host `trust-ci.ii-tonya.ru` | Voided; invariant forbids presenting it as live |
| Adding a product `/app/hook/config` client | Operator UI is the allowed path |

Route `human_gates: []` does not authorize the mutation. App webhook Save is an **irreversible/security-sensitive external write**. Stop for the operator.

## Acceptance criteria

- [ ] **Given** this agent has no App JWT, **when** it considers GitHub mutation, **then** it does not `GET`/`PATCH /app/hook/config`, does not read PEM, does not mint JWT, and does not `POST /repos/…/hooks`.
- [ ] **Given** the operator opens App settings, **when** they Save, **then** fields are: Active; URL `https://claw.taild9f611.ts.net/webhooks/github`; secret = host `TRUST_CI_WEBHOOK_SECRET` (unprinted); SSL verification Enabled; Subscribe **Pull request**.
- [ ] **Given** no operator confirmation yet, **when** docs/tests land, **then** they do **not** claim the App hook is registered/live; M0.2 webhook stays **not done**.
- [ ] **Given** operator confirms Save, **when** write-owner updates operator docs, **then** they name the Funnel URL as the GitHub App webhook, keep `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`, and still do not mark M0.2 complete until a signed GitHub delivery is observed.
- [ ] **Given** `GET /repos/Dimkox/adaptive-grok-build-pro/hooks`, **then** the list remains empty (no substitute repo hook).

## Constraints

- Backward compatibility: no product intake change; HMAC + Funnel path unchanged.
- Data/privacy: never print webhook secret, PEM, JWT, installation tokens.
- Operational: Funnel stays up; never `tailscale funnel reset`. Compose bind stays `127.0.0.1:18080`.
- Trust: local receipts are not merge authority; this slice does not create the App-owned Check Run on a GitHub delivery.

## Failure and edge cases

| Case | Handling |
| --- | --- |
| Operator Save with trailing slash or `http://` | GitHub may 301/fail SSL; URL must be exact HTTPS without slash |
| Secret mismatch | Signed GitHub POST → FastAPI **401**; operator re-pastes from host env; agent does not retrieve it |
| SSL Disabled | Forbidden; Funnel already verified HTTPS |
| “Pull request” greyed out | Missing Pull requests permission — stop; do not silently add extra scopes |
| GitHub `ping` after Save | Signed → expect 2xx; unsigned curl 401 remains the HMAC probe |
| Claiming Active checkbox = M0.2 | Fail; need signed delivery + remaining M0.2 boxes |
| Write-owner docs before confirmation using “configured/live” | Fail; use “pending UI” only |

## Write-owner notes

`delivery_expected: true` means **docs/tests in git**, not a silent GitHub PATCH.

1. Record this UI card in the change brief/requirements (no secrets).
2. Before operator confirm: optional “repo → GitHub App webhook, **not done**, Funnel URL named” docs; keep `local HMAC` / `not done` phrases `test_m0_invariants.py` requires.
3. After operator confirm: same files may say the operator Saved those fields; still no M0.2-complete; still no public-base cell change.
4. Do not implement FastAPI, compose, or an App-JWT helper.

## Preconditions already true (do not re-prove as this slice’s success)

- Funnel `/webhooks/github` → `http://10.200.200.1:18080/webhooks/github` (this-route explorer).
- Unsigned `POST https://claw.taild9f611.ts.net/webhooks/github` → HTTP **401** `missing or malformed webhook signature` (`813a02` `unsigned-ping-401.txt`).
- Repo hooks `[]`.
- App installed (IDs above).

Those prove the **edge**, not the **App registration**.

## Alignment with siblings

- `analysis-repo_explorer.md` (this change): JWT required; 401; no repo hooks; Funnel up.
- `analysis-docs_researcher.md` (this change): JWT-stop → operator UI; keep public-base loopback; checkbox **not done** until delivery or honest pending-UI rewrite.
- Prior `cec0c7`: same JWT-stop, but URL was the voided `ii-tonya` host. This slice’s URL is Funnel only.
- `decisions.md`: webhook config lives on App `adaptive-trust-ci`, not a website and not a substitute repository webhook.

## Verdict

**In scope: (a)** — stop with exact UI fields; operator Saves; operator-docs after confirmation.  
**Out of scope: (b)** — any agent-side PATCH, PEM/JWT path, repo-hook substitute, or claiming the App is configured without that Save.
