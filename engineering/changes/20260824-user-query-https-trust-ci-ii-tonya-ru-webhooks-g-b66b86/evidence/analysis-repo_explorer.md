# repo_explorer — where `trust-ci.ii-tonya.ru` is an operator target

Route `b66b867ba5ab`. User correction (verbatim): public URL `https://trust-ci.ii-tonya.ru/webhooks/github` is **not** to be touched; it was a ChatGPT error.

This explorer did **not** GET/POST that public URL, did **not** call GitHub App webhook APIs, and did **not** read PEM/env secrets.

## Verdict

The hostname is **not** a tracked product operator target. Tracked `trust-ci/` uses placeholder `https://ci.example.com/webhooks/github` and FastAPI path `POST /webhooks/github` only. The concrete URL appears as a **ChatGPT-era operator target in historical change packages** (`010964` TLS edge, `cec0c7` App webhook) and as **claw Apache leftovers**. Current user order: **do not configure, probe, or register** that public webhook.

## 1. Tracked product files

| Path | `trust-ci.ii-tonya.ru`? | Notes |
| --- | --- | --- |
| `trust-ci/**` (src, tests, compose, README) | **No** | Intake is `POST /webhooks/github`. README payload example: `https://ci.example.com/webhooks/github`. |
| `docs/` | **No** | Spec/plan use `https://<ci>/webhooks/github`. |
| `engineering/runbooks/` (incl. activation report) | **No** | Rollout says HTTPS webhook at `/webhooks/github`, no this hostname. |
| `README.md`, `AGENTS.md`, `mistakes.md`, `QUICKSTART.md` | **No** | |
| `decisions.md` | **Yes, historical fact only** | Line ~7: Apache HTTP ACME vhost for `trust-ci.ii-tonya.ru` installed; DNS A still `157.22.187.237` ≠ NAT; leave `TRUST_CI_PUBLIC_BASE_URL` on **loopback** until HTTPS exists. Not an instruction to register the GitHub App URL. |

Product contract: HMAC adapter on loopback `127.0.0.1:18080`. Public HTTPS origin is **not** encoded in tracked compose or settings defaults.

## 2. Historical change packages (ChatGPT/operator intent, not merge authority)

### `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964/`

Intended Apache TLS: GitHub App → `https://trust-ci.ii-tonya.ru/webhooks/github` → Apache :443 → `http://127.0.0.1:18080/webhooks/github`, plus `/approvals`. **Did not register a GitHub webhook this slice.** Stopped before certbot because DNS A `157.22.187.237` is **nginx on the apex**, not claw Apache.

Previously recorded probes (do not re-run): verify-on HTTPS **SSL hostname mismatch** (cert SAN `ii-tonya.ru` / `www.ii-tonya.ru` only); unsigned public POST **405 nginx**; loopback ready **200**; local Host vhost **403**.

### `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7/`

User query (then) asked to set GitHub App webhook URL to **exactly** `https://trust-ci.ii-tonya.ru/webhooks/github`. Analyses treated that as operator UI, **not** App JWT/`PATCH /app/hook/config`. Reviews: **NO-GO** to save that URL as live until cert SAN + unsigned FastAPI **401**. Agents never claimed App hook was applied.

### This package `20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86/`

Brief/route copy the **correction**: do not touch that URL. Not a product source.

Other packages mention `/webhooks/github` as loopback HMAC characterization (`127.0.0.1:18080`) without this hostname as a live target.

## 3. Host leftovers (claw Apache) — paths only; not modified

Present on this host (from `ls`, no PEM/env reads):

- `/etc/apache2/sites-available/trust-ci.conf`
- `/etc/apache2/sites-enabled/trust-ci.conf` (symlink enabled)
- `/var/www/trust-ci-acme` (ACME webroot)
- Script copy in evidence: `…/010964/evidence/host-http-vhost.sh` writes `ServerName trust-ci.ii-tonya.ru`, DocumentRoot `/var/www/trust-ci-acme`, logs `${APACHE_LOG_DIR}/trust-ci-*.log`

Absent (this check): `/etc/letsencrypt/live/trust-ci.ii-tonya.ru` — **no** LE live dir (HTTP-01 never completed).

Gitignored `trust-ci/env` / `.grok-stack`: **no** matches for this hostname in a filename search; recorded env remains loopback `http://127.0.0.1:18080` (from sibling evidence; env files not opened).

## Implication for this route

Treat `https://trust-ci.ii-tonya.ru/webhooks/github` as **invalid ChatGPT operator target**. Do not ProxyPass, certbot, GitHub App form, or public probe against it. Keep intake on loopback HMAC. Host Apache HTTP vhost is leftover from `010964`, not a reason to publish that URL.
