# docs_researcher — GitHub App vs public website naming

Route `0db5b77a9bf3`. Change `20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`. Read-only. Did not invent a replacement public webhook URL. Did not rewrite historical change-package evidence.

User (verbatim): forget ii-tonya; the application is the GitHub App `https://github.com/apps/adaptive-trust-ci`.

## How operator docs should name the GitHub App vs any public website

| Thing | Operator name | Do not call it |
| --- | --- | --- |
| The application (`приложуха`) | GitHub App **`adaptive-trust-ci`**, public page **`https://github.com/apps/adaptive-trust-ci`**, App ID **`4694114`**, installation **`156003193`**, slug **`adaptive-trust-ci`** | A public website, nginx vhost, Apache leftover, or any `*.ii-tonya.ru` hostname |
| Check owner | Trust CI GitHub App (`app.slug` = `adaptive-trust-ci`) | nginx, “the existing app” on a public A record |
| Webhook channel | **GitHub App webhook** on that App registration (one URL for all installations). Placeholder in plan/spec: `POST https://<ci>/webhooks/github`. Live intake recorded as loopback HMAC. | A “repository webhook” as if that were the design; a ChatGPT hostname as the App URL |
| Public website / TLS hostname | **None named.** `TRUST_CI_PUBLIC_BASE_URL` stays `http://127.0.0.1:18080` until a **named** public HTTPS path actually reaches FastAPI HMAC. Do not invent a replacement hostname in this slice. | `trust-ci.ii-tonya.ru`, apex `ii-tonya.ru`, or “nginx for the existing app” |

Historical change packages under `engineering/changes/**` that still quote `ii-tonya` are frozen evidence. Do not rewrite them.

## Quoted: activation-report App cells

From `engineering/runbooks/trust-ci-activation-report.md` (operator-safe table; no secrets):

```
| GitHub App slug | `adaptive-trust-ci` |
| App ID | 4694114 |
| Installation ID | 156003193 |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |
```

Surrounding report text (not a secret): first App-owned Check Run was published by a **loopback HMAC POST (not a GitHub-registered webhook)**. Required check name cell: `adaptive-trust-ci/verified@6737355947c2`. No public website URL is stored in those cells.

## Quoted: M0.2 webhook checkbox

From `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`:

```
- [ ] Register repo webhook `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS)
```

That line still says **repo** webhook and placeholder `<ci>`. It does **not** name `ii-tonya`. Status remains incomplete. Prior analysis already asked to reword to **App webhook** after GitHub actually delivers a signed `pull_request`; that reword is still outstanding and is naming (App vs repo), not a public website.

## Does `decisions.md` still imply a public website edge?

**Yes, as a future intake path; no, as a named site or as “the app.”**

Current tracked `decisions.md` (first two 2026-08-24 entries) does **not** contain `ii-tonya` or `github.com/apps/adaptive-trust-ci`. It still says:

- voided ChatGPT hostname: do not configure GitHub App or repository webhook to it; leave `TRUST_CI_PUBLIC_BASE_URL` on loopback **until a named public HTTPS path actually reaches FastAPI HMAC**;
- Apache HTTP leftover exists; public A is not this NAT host; leftover is **not** a live Trust CI edge; leave public base on loopback.

That language still implies an eventual **public HTTPS edge** (unspecified hostname). It does **not** equate that edge with the GitHub App. It does not identify `https://github.com/apps/adaptive-trust-ci` as the application.

## Does `mistakes.md` still say ChatGPT hostname is «nginx for the existing app»?

**Yes.** Tracked `mistakes.md` entry `2026-08-24 — Treated a ChatGPT hostname as the live webhook URL`:

**Symptom:** Operator packages and `decisions.md` pointed GitHub App webhook and Apache TLS at `https://trust-ci.ii-tonya.ru/webhooks/github`.

**Root cause:** A ChatGPT-invented hostname was copied as operator truth. **That name is nginx for the existing app**, not Trust CI on claw; do not configure, probe, or complete TLS for it.

That root-cause sentence is the misread this user is correcting: “the existing app” is written as a public nginx site. Operator truth is that the application is the GitHub App `https://github.com/apps/adaptive-trust-ci`, not a public website on that hostname. Symptom may keep the ChatGPT URL as the logged mistake (invariants expect `mistakes.md` to name that URL). Root cause must not keep “nginx for the existing app.”

## Tracked files that must change

| Path | Must change? | Why |
| --- | --- | --- |
| `mistakes.md` | **Yes** | Root cause still calls the ChatGPT hostname «nginx for the existing app». Correct so “app” = GitHub App `https://github.com/apps/adaptive-trust-ci`; hostname remains a void ChatGPT URL, not the application. Keep the URL in the log so `test_m0_invariants` still sees it in `mistakes.md` only. |
| `decisions.md` | **Yes** | Add a short ruling: operator “application” = GitHub App `https://github.com/apps/adaptive-trust-ci`; do not treat any public website as the app. Optionally tighten the leftover “named public HTTPS path” sentences so they do not read as a pending website-named edge. Do not insert a new public webhook URL. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | **Optional this slice** | M0.2 checkbox still says “Register **repo** webhook”; should eventually say **App** webhook, still **not done**. Not required to name `github.com/apps/...` on that line. Keep `local HMAC` / `not done` / `no public HTTPS` phrases for `test_m0_invariants`. |
| `engineering/runbooks/trust-ci-activation-report.md` | **No** | App slug / App ID / Installation ID already match the GitHub App. Public base is loopback. |
| `README.md`, M0 spec, `AGENTS.md` | **No for this naming bug** | They already speak of the GitHub App / Check Run owner, not a public website as the app. Spec still uses placeholder `https://<ci>/webhooks/github`. |
| Historical `engineering/changes/**` (cec0c7, 010964, b66b86, …) | **No** | Do not rewrite historical evidence. |

## Out of scope (do not do)

- Invent a replacement public webhook URL.
- Probe or configure `ii-tonya`.
- Claim M0.2 complete; protect `main`; PATCH `/app/hook/config`.
- Read `.env`, PEM, webhook secret.

## Verdict

**Must change:** `mistakes.md` (nginx / “existing app” root cause) and `decisions.md` (name the GitHub App as the application; drop implication that a public website is the app). **Do not change** activation-report App cells or historical change-package evidence. Plan M0.2 webhook checkbox stays **not done**; optional later reword from repo → App webhook without filling `<ci>`.
