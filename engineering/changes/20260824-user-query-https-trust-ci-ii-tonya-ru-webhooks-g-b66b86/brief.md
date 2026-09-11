# Retract ChatGPT Trust CI webhook URL

Change ID: `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`
Route: `b66b867ba5ab`
Write owner: `integration_implementer`

## Problem

User (verbatim): `https://trust-ci.ii-tonya.ru/webhooks/github нет , не трогаем, это ошибка chatgpt`.

That hostname was treated as the live GitHub App webhook / Apache TLS-edge target in sibling packages `cec0c7` and `010964`, and as the pending ACME hostname in `decisions.md`. It is not operator truth.

## Outcome

Operators and future agents stop using that ChatGPT URL. Tracked operator docs (plan, spec, activation report, README, `decisions.md`) do not present that URL or hostname as the live webhook / public TLS target. FastAPI, compose, host Apache, GitHub App hook config, and `TRUST_CI_PUBLIC_BASE_URL` stay frozen. Loopback HMAC on `127.0.0.1:18080` remains the only proven delivery path. M0.2 webhook stays **not done**.

## Scope

### In scope

- Characterization test in `trust-ci/tests/test_m0_invariants.py` forbidding the ChatGPT URL and hostname in the five operator docs.
- Retract the 2026-08-24 Apache TLS `decisions.md` entry so it no longer names that hostname.
- Log the root cause in `mistakes.md`.
- Optional one-line retraction banners on sibling briefs `cec0c7` and `010964` only (evidence stays).

### Out of scope

- FastAPI / HMAC / compose / gitignored env edits.
- GitHub App `PATCH /app/hook/config`, App JWT/PEM, repository webhook.
- Certbot, DNS, Apache vhost install/uninstall/edit (`не трогаем`).
- Inventing a replacement public webhook URL.
- Claiming M0.2 complete; protecting `main`; merge/push/deploy.

## Constraints

- Backward compatibility: no API contract change.
- Data/privacy: do not read PEM, webhook secret, or env dumps.
- Operational: API stays `127.0.0.1:18080`. Do not probe the ChatGPT URL.
