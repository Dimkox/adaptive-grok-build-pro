# docs_researcher — public TLS edge vs registered webhook (M0.2)

Route `01096425a38d`. Change `20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964`. Read-only sources; no secrets.

## 1. Public HTTPS is not a registered GitHub webhook

Plan checkbox **Register repo webhook** stays **UNCHECKED** until an actual GitHub hook exists.

`docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.2:

- `[ ] Register repo webhook POST https://<ci>/webhooks/github` — currently **not done** (parenthetical still says “no public HTTPS”).
- Disposable-PR Check Run line is **partial:** local HMAC only; **Not M0.2 complete.**
- Later M0.2 items (offline attestation, policy/holdout retitle, Ed25519 requeue, source-mutation) remain open.
- **Do not protect `main`.**

Rollout in `trust-ci/README.md` (GitHub configuration) is ordered: deploy API/Postgres/worker → **install the webhook** → disposable PR → observe App-owned Check Run → attestation → **then** branch protection.

Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` same order: step 2 is **Register repository webhook** `POST https://<ci>/webhooks/github`. Freeze snapshot: `GET .../hooks` empty. Live gap: **M0.2 is still incomplete (no public HTTPS webhook).**

Activation report `engineering/runbooks/trust-ci-activation-report.md`: first Check Run was a **loopback HMAC POST (not a GitHub-registered webhook)**. “Local HMAC / public webhook still not a registered GitHub hook.”

Apache TLS to `/webhooks/github` and `/approvals` is a reverse-proxy prerequisite (`trust-ci/README.md` Terminate TLS; spec Host: TLS reverse proxy). It does **not** create the GitHub hook. **Public HTTPS ≠ registered webhook.** Do not check the M0.2 webhook box after DNS/Certbot/Apache only.

## 2. Activation report: public URL HTTPS; Check Run ids numeric; M0.2 incomplete

Current report cell:

| Field | Current (must change after TLS) |
| --- | --- |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |

After the edge exists, this **must** become `https://trust-ci.ii-tonya.ru` (no trailing slash required; settings rstrip `/`). Loopback HTTP is only for `localhost`/`127.0.0.1` (`trust-ci/src/adaptive_trust_ci/settings.py` CommonSettings). Spec Host: **`TRUST_CI_PUBLIC_BASE_URL` must still be HTTPS.**

Keep numeric Check Run ids already in the report (`97390635614`, SHA-change `97406973020`). Do not replace them with names or UNKNOWN.

Do **not** claim M0.2 complete: public TLS + env URL still leave webhook unregistered, `main` unprotected, attestation N/A (`needs_approval`), policy/holdout retitle open.

Untracked host env (`env/common.env`) is the operator bind for `TRUST_CI_PUBLIC_BASE_URL`; **do not commit** `env/common.env` or Let’s Encrypt keys (`trust-ci/README.md` Bootstrap: copy examples; do not commit resulting files).

## 3. `test_m0_invariants` — keep “not done” on the webhook line

`trust-ci/tests/test_m0_invariants.py` `test_activation_report_operator_safe`:

- plan must contain `"local HMAC"`
- plan must contain `"no public HTTPS"` **OR** `"not done"`

If TLS docs drop “no public HTTPS”, the **Register repo webhook** line must still say **not done** (hook not registered). Deleting both phrases fails the test. Do not mark M0.2 webhook `[x]` to satisfy wording.

## 4. Spec: public URL must be HTTPS — align the report

- Spec Host: TLS reverse proxy to `/webhooks/github` and `/approvals`; published API stays `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` (not all-interfaces, not host 8080).
- `CommonSettings.load`: `TRUST_CI_PUBLIC_BASE_URL` must start with `https://` or `http://localhost` / `http://127.0.0.1`; else `SettingsError('TRUST_CI_PUBLIC_BASE_URL must be HTTPS outside localhost')`.
- README webhook example Payload URL is `https://…/webhooks/github`.
- GitHub: HTTPS, cert verify, webhook secret, `X-Hub-Signature-256`; respond < 30s. README: terminate TLS in reverse proxy.

Align the activation-report `TRUST_CI_PUBLIC_BASE_URL` cell to `https://trust-ci.ii-tonya.ru`. Do not leave `http://127.0.0.1:18080` as the documented public base after the edge is live.

## 5. Do not commit secrets or cert material

Do not commit:

- `trust-ci/env/common.env` (or other `env/*.env` / `.env`)
- Let’s Encrypt `privkey.pem` / `fullchain.pem` or any copy under the repo
- webhook secret, App PEM, JWT, admin token, human approval private keys

README: `chmod 600 env/*.env`; webhook Secret is `TRUST_CI_WEBHOOK_SECRET` (placeholder only). Report: never paste PEM, JWT, webhook secret, admin token, or human approval private keys.

## Cited paths

- `trust-ci/README.md` — TLS reverse proxy; webhook URL/secret/events; rollout order
- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` — HTTPS public URL; webhook register step; M0.2 incomplete
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` — M0.2 webhook **not done**; local HMAC partial
- `engineering/runbooks/trust-ci-activation-report.md` — loopback public URL today; numeric Check Runs; not a GitHub hook
- `trust-ci/src/adaptive_trust_ci/settings.py` — HTTPS-outside-localhost validation
- `trust-ci/tests/test_m0_invariants.py` — `"no public HTTPS" in plan or "not done" in plan`

## Ruling for implementers

TLS edge + `https://trust-ci.ii-tonya.ru` in the activation report is this slice. Leave M0.2 webhook checkbox **unchecked** with **not done**. Keep Check Run ids. Do not declare M0.2 complete. Do not commit `env/common.env` or Let’s Encrypt keys.
