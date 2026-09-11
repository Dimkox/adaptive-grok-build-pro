# docs_researcher — retract ChatGPT webhook URL `https://trust-ci.ii-tonya.ru/webhooks/github`

Route `b66b867ba5ab`. User (verbatim): that URL is not to be used; do not touch it; ChatGPT error. No replacement public URL invented. Secrets unread.

## Verdict

**Do not configure GitHub App (or repo) webhook to `https://trust-ci.ii-tonya.ru/webhooks/github`.** That hostname is **not** live operator truth for the webhook or public TLS edge. Canonical plan/spec still use placeholder `https://<ci>/webhooks/github`. Activation-report public base remains loopback. Retract operator-facing hostname claims in `decisions.md` (ACME vhost name) if that file is treated as current TLS-edge instruction; leave change-package evidence as history.

## Quotes required by the task

Activation-report current cell (`engineering/runbooks/trust-ci-activation-report.md`):

| Field | Value |
| --- | --- |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |

M0.2 webhook checkbox (`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` line 32):

```
- [ ] Register repo webhook `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS)
```

Spec rollout (`docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` line 73) also uses the **placeholder** `POST https://<ci>/webhooks/github`, not `trust-ci.ii-tonya.ru`.

README.md: **no** `trust-ci.ii-tonya.ru` and **no** `/webhooks/github` public URL.

## Live operator truth (must retract if it still names that host as webhook / TLS edge)

| File | Instructs that URL as GitHub App webhook? | Instructs hostname as public TLS edge? | Action |
| --- | --- | --- | --- |
| `decisions.md` § 2026-08-24 Apache TLS edge | **No** (does not mention `/webhooks/github`) | **Yes** — ACME vhost for `trust-ci.ii-tonya.ru`; leave `TRUST_CI_PUBLIC_BASE_URL` on loopback until HTTPS exists | **Retract hostname as intended public edge** if this entry is still treated as current instruction. Do not replace with another public URL in this slice. Loopback-until-HTTPS remains consistent with activation report. |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | **No** — placeholder `<ci>` only; checkbox **not done** | **No** named `trust-ci.ii-tonya.ru` | **Leave**; already does not instruct the ChatGPT URL |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | **No** — `https://<ci>/webhooks/github` | TLS reverse proxy required, **no** `ii-tonya.ru` hostname | **Leave** |
| `engineering/runbooks/trust-ci-activation-report.md` | **No** | **No** — public base is `http://127.0.0.1:18080` | **Leave**; do **not** set cell to `https://trust-ci.ii-tonya.ru` |
| `README.md` | **No** | **No** | **Leave** |

## Historical evidence (leave as history)

Do not rewrite analyses/reviews. Optional: one retraction banner on **this** package brief only.

| Package / path | Role |
| --- | --- |
| `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7/` (`brief.md` and evidence) | **ChatGPT-shaped operator order:** App webhook Active, URL `https://trust-ci.ii-tonya.ru/webhooks/github`, SSL Enabled, event Pull request. **Historical false instruction.** Do not execute. |
| `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964/` | TLS-edge slice that named Apache + `trust-ci.ii-tonya.ru` + unsigned POST 401; **did not** register GitHub hook. Host/DNS evidence already shows A `157.22.187.237` is nginx, cert SAN mismatch, unsigned POST **405**. History of a blocked edge, not a live webhook. |
| `engineering/changes/20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86/` | This retraction change; brief currently echoes the user correction. |

## What this slice must not do

- Invent a replacement public HTTPS webhook URL.
- PATCH GitHub App hook config / read App PEM.
- Flip activation-report `TRUST_CI_PUBLIC_BASE_URL` to `https://trust-ci.ii-tonya.ru`.
- Check the M0.2 webhook box.
- Touch host Apache/DNS/certbot because of this URL.

Webhook remains **unregistered**. Public HTTPS remains **absent**. Endpoint “on the existing app” is a later slice, not this retraction.
