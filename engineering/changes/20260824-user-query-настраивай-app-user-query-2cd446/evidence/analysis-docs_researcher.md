# docs_researcher — GitHub App webhook config (route 2cd446440734)

Read-only. No invented hostname. No `.env`/PEM/JWT. «Приложуха» = GitHub App `https://github.com/apps/adaptive-trust-ci` (slug `adaptive-trust-ci`, App ID `4694114`). Public payload URL the operator named (and Funnel slice `813a02` already recorded) is only:

`https://claw.taild9f611.ts.net/webhooks/github`

Do not write `trust-ci.ii-tonya.ru` or any other origin. `test_m0_invariants.test_operator_docs_do_not_present_chatgpt_webhook_as_live` forbids that host in spec/plan/report/README/`decisions.md`.

## Quoted: M0.2 webhook checkbox

From `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`:

```
- [ ] Register repo webhook `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS)
```

The box is **unchecked**. Wording still says **repo** webhook. `trust-ci/tests/test_m0_invariants.py` requires plan text to contain `local HMAC` and (`no public HTTPS` **or** `not done`).

## Quoted: activation-report public URL cell

From `engineering/runbooks/trust-ci-activation-report.md`:

| Field | Value |
| --- | --- |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |

Same file: first App-owned Check Run was **loopback HMAC POST (not a GitHub-registered webhook)**; “Local HMAC / public webhook still not a registered GitHub hook.”

## Keep `TRUST_CI_PUBLIC_BASE_URL` on loopback

This slice **does not** change that cell. `TRUST_CI_PUBLIC_BASE_URL` is the worker Check Run `details_url` origin (`settings.py`: HTTPS required outside localhost). Inbound GitHub delivery uses the App webhook URL / Funnel path, independent of that env.

`decisions.md` (ChatGPT-hostname void + Apache leftover): leave the setting on loopback until a named public HTTPS path actually reaches FastAPI HMAC **and** a later slice is explicitly about Check Run links. Funnel unsigned 401 (slice `813a02`) proved the edge; it did **not** authorize rewriting `details_url`. Sibling Funnel `docs_researcher` that proposed `https://claw.taild9f611.ts.net` in the report cell is **superseded** for this route: keep `http://127.0.0.1:18080` unless a later analysis names Check Run public links.

Do not `sed` gitignored `common.env` in this change.

## JWT-stop vs operator UI

`PATCH`/`GET /app/hook/config` requires a GitHub App JWT signed with the App RSA PEM (`cec0c7` architect). User tokens and installation tokens cannot call it. `AGENTS.md` forbids reading that PEM. There is **no** `github.py` client for `/app/hook/config`. Events (`pull_request`) are App-registration fields, not the hook-config PATCH body.

**If the agent cannot mint JWT (expected):** stop API config. Operator sets Active, URL `https://claw.taild9f611.ts.net/webhooks/github`, JSON, secret = host `TRUST_CI_WEBHOOK_SECRET` (never in git), SSL verification Enabled, subscribe **Pull request**, on `https://github.com/apps/adaptive-trust-ci` (settings: `https://github.com/settings/apps/adaptive-trust-ci`). Do **not** create a repository webhook as a substitute (`decisions.md`).

UI “Active” ≠ GitHub delivery. M0.2 checkbox stays **not done** until a signed GitHub `pull_request` (or documented ping) is observed on FastAPI.

## Operator docs after JWT-stop (UI pending; Funnel URL already named)

Checkbox stays `[ ]`. Optionally reword “repo” → **GitHub App** webhook and note **Funnel URL + App hook pending UI**. Keep `not done` so invariants stay green. Do **not** drop both `not done` and `no public HTTPS` unless the replacement still includes `not done`.

| File | After JWT-stop / UI pending | Do not |
| --- | --- | --- |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Keep `[ ]`. Optional: “Register **GitHub App** webhook `POST https://claw.taild9f611.ts.net/webhooks/github` — **not done** (App hook pending UI; Funnel path exists).” Preserve `local HMAC` elsewhere in the file. | `[x]`; claim M0.2 complete |
| `engineering/runbooks/trust-ci-activation-report.md` | **Leave** `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`. Optional prose: Funnel URL named; App hook not GitHub-delivered. | Change public-URL cell; invent a host |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Rollout step 2 still later until signed delivery. M0.2 incomplete. | Treat UI save as live authority |
| `decisions.md` | Optional 3 sentences: App webhook is UI-only without PEM; Funnel URL is the only named origin; loopback `details_url` stays. | Second hostname |
| `trust-ci/README.md` / `engineering/runbooks/trust-ci-rollout.md` | Optional: “GitHub App webhook” instead of “repository webhook”; example payload may stay `ci.example.com` **or** the Funnel URL — not a ChatGPT host. | Require a repo hook |
| This change package | Record JWT-stop + UI steps; no secrets. | `PATCH /app/hook/config` |

## Operator docs after successful config **and** observed GitHub delivery

Only then reword the checkbox to App webhook and describe delivery. Still **do not** mark all of M0.2 complete (attestation, policy retitle, human requeue, source-mutation, `branch-protect` remain open). Still **do not** change `TRUST_CI_PUBLIC_BASE_URL` in this slice.

| File | After observed GitHub delivery | Do not |
| --- | --- | --- |
| Plan M0.2 first checkbox | Reword to App webhook; may tick **that** line if delivery is proven; keep other M0.2 boxes and “Not M0.2 complete” on the Check Run line. Keep `local HMAC` in the file **or** update `test_m0_invariants` in the same tree if the phrase is retired. | Tick M0.2 as a whole; drop invariant phrases without updating the test |
| Activation report | Keep public-URL cell loopback. Prose: GitHub-registered App hook delivered to Funnel URL (not loopback HMAC as the only path). | Put Funnel origin in `TRUST_CI_PUBLIC_BASE_URL` this slice |
| Spec rollout #2 | App webhook, not repo webhook; signed `pull_request` observed. | Claim `main` protected |
| `decisions.md` | App hook configured via UI; delivery observed; PEM unread. | JWT mint as a success path |
| README / rollout | App registration, payload Funnel URL, HMAC env name only. | Repository webhook substitute |

## Files **not** changed for hook config

`trust-ci/src/**`, `trust-ci/compose.yaml`, gitignored env/PEM, branch protection, GitHub Actions.

## Verdict

JWT-stop: operator UI only. Quote stays `[ ] Register repo webhook … **not done** (no public HTTPS)` until delivery **or** an honest “Funnel URL + App hook pending UI” rewrite that still says **not done**. Quote public URL cell stays `http://127.0.0.1:18080`. Do not invent another hostname.
