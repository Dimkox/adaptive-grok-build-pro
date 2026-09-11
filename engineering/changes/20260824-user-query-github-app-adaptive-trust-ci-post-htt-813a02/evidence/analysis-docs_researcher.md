# docs_researcher — Funnel public webhook path (route 813a02b06dfc)

Read-only. No invented second hostname. «Приложуха» = GitHub App `https://github.com/apps/adaptive-trust-ci` (slug `adaptive-trust-ci`, App ID `4694114`). Do not name a voided ChatGPT domain as a live target.

## Quoted: activation-report `TRUST_CI_PUBLIC_BASE_URL`

From `engineering/runbooks/trust-ci-activation-report.md` (table cell as committed today):

| Field | Value |
| --- | --- |
| `TRUST_CI_PUBLIC_BASE_URL` | `http://127.0.0.1:18080` |

Surrounding operator-safe facts (same file): first App-owned Check Run was a **loopback HMAC POST (not a GitHub-registered webhook)**. “Local HMAC / public webhook still not a registered GitHub hook.” Dedicated host `claw`. App slug `adaptive-trust-ci`.

## Quoted: plan M0.2 webhook checkbox

From `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`:

```
- [ ] Register repo webhook `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS)
```

The box is **unchecked**. Wording still says **repo** webhook and **no public HTTPS**. M0.2 is not complete. Spec (`docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`) still says “M0.2 is still incomplete (no public HTTPS webhook)” and rollout step 2 “Register repository webhook”.

`trust-ci/tests/test_m0_invariants.py` requires the plan to contain `local HMAC` and (`no public HTTPS` **or** `not done`).

## User-named public HTTPS path (only hostname)

Operator named **one** public origin (Tailscale Funnel, not Apache):

`https://claw.taild9f611.ts.net/webhooks/github`

GitHub App webhook URL and Funnel `--set-path` + target both keep `/webhooks/github` so FastAPI sees that path. Compose bind stays `127.0.0.1:18080`. Unsigned public POST is expected **HTTP 401** `missing or malformed webhook signature` — edge + HMAC, **not** App registration.

`CommonSettings`: `TRUST_CI_PUBLIC_BASE_URL` is origin only (HTTPS outside localhost); Check Run `details_url` is `{base}/jobs/{id}`. After unsigned 401 succeeds, the activation-report cell is:

`https://claw.taild9f611.ts.net`

Do not invent a second hostname. Do not put the webhook path in the `TRUST_CI_PUBLIC_BASE_URL` cell.

## Operator docs to update AFTER unsigned 401 succeeds

Plan note (010964, adapted to this hostname): **public HTTPS path exists** but **GitHub App hook is still unregistered**. Do **not** tick M0.2 complete.

| Doc | After proven unsigned 401 | Do not |
| --- | --- | --- |
| `engineering/runbooks/trust-ci-activation-report.md` | Set `TRUST_CI_PUBLIC_BASE_URL` to `https://claw.taild9f611.ts.net`. Note Funnel path `/webhooks/github` reaches FastAPI HMAC; **App hook still unregistered**. | Claim GitHub-registered webhook; list a second host |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Keep `[ ]`. Reword **Register repo webhook** → **GitHub App** webhook (`приложуха`). Drop stale “no public HTTPS” **only if** the line still says **not done** (hook unregistered) so invariants stay green. Optional: “public HTTPS path exists; App hook still unregistered.” | `[x]`; drop both `not done` and `no public HTTPS` |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | Host TLS may cite Funnel; rollout step 2 stays **later** until GitHub App webhook delivers signed `pull_request`. Keep M0.2 incomplete. | Treat unsigned 401 as live authority |
| `decisions.md` | After proof: named public HTTPS path `https://claw.taild9f611.ts.net` reached FastAPI HMAC; `TRUST_CI_PUBLIC_BASE_URL` may leave loopback. «Приложуха» remains the GitHub App, not Funnel. | Invent another URL; treat Funnel as the App |
| Gitignored `trust-ci/env/common.env` | Operator may `sed` only `TRUST_CI_PUBLIC_BASE_URL=` to the same HTTPS origin, then recreate **api worker** (not postgres). Not a tracked doc. | Commit env; dump secrets |

Not this paperwork: `branch-protect`, M0.2 `[x]`, GitHub Actions, PEM/webhook secret, `tailscale funnel reset`. Registration of the App webhook URL on `https://github.com/apps/adaptive-trust-ci` is a **later** named slice after 401.

## Verdict

Activation report still documents loopback `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. Plan M0.2 webhook remains `[ ]` **not done (no public HTTPS)**. After Funnel unsigned POST returns 401, update that cell to `https://claw.taild9f611.ts.net` and note public HTTPS exists while the **GitHub App** hook stays unregistered; do not invent a second hostname or claim M0.2 complete.
