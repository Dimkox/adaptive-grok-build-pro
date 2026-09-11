# task_analyst — PATCH GitHub App hook via worker JWT (route c36377792135)

Change: `engineering/changes/20260824-user-query-че-бля-делай-нахуй-user-query-c36377`  
Write owner: **`general_implementer`**. This agent does not PATCH, mint JWT, read PEM/`.env`/secret into chat, Funnel-reset, protect `main`, push, merge, or deploy.

User rejected the previous **UI-only** stop (`2cd446` / `decisions.md` “operator Saves”). Source-of-truth #1 this turn: **do the App hook PATCH**.

## Ruling

**In-scope outcome is the GitHub App webhook config mutation**, not a UI card.

`PATCH https://api.github.com/app/hook/config` with a **GitHub App JWT** minted **inside** `adaptive-trust-ci-worker-1` by existing `generate_app_jwt` (PEM already at `/run/secrets/github-app-private-key.pem`). Do **not** use the worker **installation token** (`GitHubAppAuth.installation_token`) and do **not** use the user `gh` token (live 401 “JWT could not be decoded”). Do **not** print PEM, JWT, `TRUST_CI_WEBHOOK_SECRET`, or `Authorization`. Do **not** `POST /repos/.../hooks`.

This outranks the 2026-08-24 “PATCH needs operator UI” decision. It does **not** complete M0.2, protect `main`, or reset Funnel.

## Observable outcome

GitHub App `adaptive-trust-ci` (App ID `4694114`, Installation `156003193`) hook config is:

| Field | Value |
| --- | --- |
| `url` | `https://claw.taild9f611.ts.net/webhooks/github` (HTTPS, **no** trailing slash) |
| `content_type` | `json` |
| `secret` | exact bytes of API env key `TRUST_CI_WEBHOOK_SECRET` (gitignored `trust-ci/env/api.env`; **unpublished**) |
| `insecure_ssl` | `"0"` (SSL verification on) |

Proof: JWT-authenticated `GET /app/hook/config` returns HTTP 200 with that `url` and `insecure_ssl="0"`. Printed JSON **redacts** `secret`. Repo `GET /repos/Dimkox/adaptive-grok-build-pro/hooks` stays `[]`.

`PATCH` does **not** set Active and does **not** subscribe **Pull request**. This slice still succeeds if URL+SSL+secret land. A GitHub `ping` / Recent Delivery is extra evidence, **not** M0.2 exit.

## In scope

1. One-shot **inside the worker** (PEM already mounted). Host `/tmp` script → `docker exec -i adaptive-trust-ci-worker-1`; secret on **stdin** (or equivalent non-argv pipe) from `api.env`; never `cat`/`echo`/`grep` the value.
2. `generate_app_jwt(app_id, pem_bytes)` → `Authorization: Bearer <jwt>` → `PATCH /app/hook/config` body `{url, content_type: "json", secret, insecure_ssl: "0"}` → redacted `GET`.
3. Local grant **after** last pre-PATCH tree freeze:

```text
python3 scripts/grok_approve.py external-write \
  --action external-write \
  --resource github-api \
  --source explicit-user-consent \
  --reason "user rejected UI-only; PATCH /app/hook/config Funnel URL via worker App JWT" \
  --ttl 15
```

4. Operator docs: activation-report inbound cell may say worker-JWT PATCH (Funnel URL). Plan M0.2 webhook line stays **`[ ]` / not done**. Optional `decisions.md` supersede of the UI-only sentence (protected-path grant; ≤3 sentences). Characterization: Funnel URL still named; no PEM markers; `ii-tonya` still absent from the five operator docs.

## Out of scope

| Item | Why |
| --- | --- |
| Claim M0.2 complete | Remaining: GitHub-origin delivery job, attestation, policy retitle, Ed25519 requeue, source-mutation |
| Protect `main` / `branch-protect` | M0.3 |
| `tailscale funnel reset` / Funnel rewrite | Edge already proven (`813a02` unsigned 401) |
| Repository webhook | User + `decisions.md`: config lives on the App |
| PEM / JWT / secret in chat, git, this package | User + `AGENTS.md` |
| Installation token for `/app/hook/*` | Wrong credential; 401/403 |
| Product `/app/hook` client, FastAPI, compose, `TRUST_CI_PUBLIC_BASE_URL` | One-shot; `details_url` stays loopback |
| `insecure_ssl=1` / ChatGPT host `trust-ci.ii-tonya.ru` | Forbidden |
| UI-only stop / “hand the operator a Save card” | User rejected |

## Acceptance criteria

- [ ] **Given** worker PEM mount and App ID, **when** the one-shot runs, **then** it mints an App JWT in-process and `PATCH`es `/app/hook/config`; it does not `cat` the PEM, print `eyJ`, or use `installation_token()`.
- [ ] **Given** `GET /app/hook/config` with that JWT, **then** `url` is exactly `https://claw.taild9f611.ts.net/webhooks/github` and `insecure_ssl` is `"0"`.
- [ ] **Given** the PATCH body, **then** `secret` equals host `TRUST_CI_WEBHOOK_SECRET` and that value never appears in command output, git, or this package.
- [ ] **Given** `GET /repos/Dimkox/adaptive-grok-build-pro/hooks`, **then** `[]`.
- [ ] **Given** plan / activation report, **then** M0.2 webhook remains **not done**; `main` unprotected; Funnel not reset; `TRUST_CI_PUBLIC_BASE_URL` remains `http://127.0.0.1:18080`.

## Constraints

- **Credential:** App JWT only (`iss` = App ID, RS256, `iat−60s`/`exp+9m` as in `github_app.py`). Worker has PEM; API must not.
- **Secret source:** API env only. Worker `env_file` has no `TRUST_CI_WEBHOOK_SECRET`. Do not dump `api.env`.
- **Output:** HTTP status + `url` + `content_type` + `insecure_ssl` only. Unlink `/tmp` script.
- **Worker FS:** read-only image, `/tmp` tmpfs `noexec` — interpret `python3 /tmp/….py`, do not exec the file.
- **Compat:** HMAC adapter and Funnel path unchanged.
- **Trust:** local receipts ≠ merge authority. A ping 200 is not a Check Run.

## Failure / edges

| Case | Handling |
| --- | --- |
| Installation token used | Fail; redo with App JWT |
| User `gh api /app` | Known 401; do not retry as the PATCH |
| Trailing slash / `http://` URL | Fail SSL/HMAC path; URL must be exact |
| Secret mismatch | Later GitHub POST → FastAPI 401; re-PATCH from `api.env`; do not print |
| Active off / no Pull request event | URL still in-scope-success; do not claim deliveries/jobs; events are not a `PATCH /app/hook/config` field |
| `docker exec` prints JWT | Fail; redact and rotate if leaked |
| Grant after tree mutation | Invalid; mint on the frozen tree, PATCH, then docs |

## Write-owner notes

`delivery_expected: true` = **the PATCH plus honest docs/tests**, not a silent GitHub write and not a new Trust CI client.

1. Do not implement FastAPI/compose. Do not add `/app/hook/*` to `github.py` this slice.
2. One-shot + redacted GET receipt under this package (`evidence/hook-config.md`: status/url/ssl only).
3. Keep `test_m0_invariants` phrases `local HMAC` / `not done` / Funnel URL / no PEM / no `ii-tonya`.
4. Unlink the helper. No second GitHub mutation (no deliveries retry storm, no repo hook, no branch-protect).
