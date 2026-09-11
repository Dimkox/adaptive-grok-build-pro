# task_analyst — GitHub App is the application; forget `ii-tonya`

Route `0db5b77a9bf3`. Change `20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`.
Write owner: `general_implementer`. This agent does not implement, probe, PATCH, read PEM/secrets, or deploy.

User (verbatim): `забудь вообще нахуй про ii-tonya, приложуха - это приложение github https://github.com/apps/adaptive-trust-ci`.

## Verdict

**Operator-memory + characterization only.** The observable result is that later agents treat «приложуха» as the GitHub App at `https://github.com/apps/adaptive-trust-ci` (slug `adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`), and never as a public website / nginx / Apache leftover on any `*.ii-tonya.ru` hostname. Forget that public domain entirely. Do **not** change FastAPI, do **not** mint App JWT or `PATCH /app/hook/config`, do **not** create a repository webhook, do **not** touch TLS/certbot/Apache, and do **not** invent a public webhook URL.

Sibling `b66b86` already retracted the ChatGPT URL from the five operator live-target docs. This slice is the **identity correction** that retraction left unfinished: “the existing app” is still written as nginx on that domain.

---

## Prior misread (must not repeat)

| Phrase | Wrong reading (prior agents) | Operator truth (this user) |
| --- | --- | --- |
| «приложуха» | nginx site / public A `157.22.187.237` / vhost on `ii-tonya.ru` | GitHub App **`https://github.com/apps/adaptive-trust-ci`** |
| «эндпойнт на самой приложухе» | HTTP(S) endpoint on that public domain (later TLS-edge / webhook URL work) | GitHub App registration / App webhook **on that App**, not a public website |
| `https://trust-ci.ii-tonya.ru/webhooks/github` | live App webhook / Apache TLS target | ChatGPT error; already voided by `b66b86`; **do not probe or complete** |

Concrete leftover of the misread in tracked memory:

- `mistakes.md` root cause still says: “That name is **nginx for the existing app**, not Trust CI on claw.”
- `b66b86` `analysis-docs_researcher.md` closed with: “Endpoint **on the existing app** is a later slice, not this retraction.”
- `decisions.md` voids the ChatGPT hostname without naming `https://github.com/apps/adaptive-trust-ci` as the application, and still implies an eventual unnamed public HTTPS edge.

The user now: **forget `ii-tonya` entirely.** The application is the GitHub App page, not a website on that domain.

---

## Observable outcome

A later agent (or operator) who reads only tracked memory and characterization tests, without this chat:

1. **Names the application** as GitHub App `https://github.com/apps/adaptive-trust-ci` (slug `adaptive-trust-ci`, App ID `4694114`, Installation `156003193`).
2. **Does not** treat any `ii-tonya` hostname, nginx vhost, Apache leftover, or public A record as the application, the webhook target, or a pending TLS edge to complete.
3. **Does not** invent a replacement public webhook URL. Proven intake stays loopback HMAC `POST http://127.0.0.1:18080/webhooks/github`. Activation-report `TRUST_CI_PUBLIC_BASE_URL` stays `http://127.0.0.1:18080`.
4. **Does not** claim M0.2 complete. Plan checkbox remains **not done** (`POST https://<ci>/webhooks/github`, placeholder, no public HTTPS).
5. Runtime, GitHub App hook config, host TLS, and historical change-package evidence are **unchanged**.

Success metric: identity is locked in `decisions.md` + `mistakes.md` and a characterization test would go red if “the app” is again written as a public website or if `ii-tonya` reappears as a live target in the five operator docs. Not a live webhook. Not a Check Run. Not a TLS cert.

---

## Current behavior (facts recovered; no probe)

From `analysis-repo_explorer.md` and `analysis-docs_researcher.md` on this change, plus `b66b86` retraction:

| Surface | Fact |
| --- | --- |
| Five operator live-target docs (plan, spec, activation report, README, `decisions.md`) | **No** `ii-tonya` substring. `test_operator_docs_do_not_present_chatgpt_webhook_as_live` already forbids URL + host there. |
| `mistakes.md` | **Names** `https://trust-ci.ii-tonya.ru/webhooks/github` as the logged mistake (intentional; not in the five-file scan). Root cause still = “nginx for the existing app”. |
| `trust-ci/tests/test_m0_invariants.py` | Constants `CHATGPT_WEBHOOK_URL` / `CHATGPT_WEBHOOK_HOST` used only as `assertNotIn` on the five files. Not a live target. |
| Activation report | Slug `adaptive-trust-ci`, App ID `4694114`, Installation `156003193`, public base loopback. Literal URL `https://github.com/apps/adaptive-trust-ci` **absent**. First Check Run was loopback HMAC, **not** a GitHub-registered webhook. |
| M0.2 plan line | `Register repo webhook POST https://<ci>/webhooks/github` — **not done**. Says **repo**, not App. Does not name `ii-tonya`. |
| FastAPI / compose | Frozen. Publish `127.0.0.1:18080`. HMAC `POST /webhooks/github` unchanged. |
| Historical packages `cec0c7`, `010964`, `b66b86` | Still quote `ii-tonya` as retracted evidence. Leave them. |

There is **no live-doc leak** of `ii-tonya` as webhook/TLS target. The remaining defect is **category error in operator memory**, not a missing public site.

---

## In scope

1. **`mistakes.md`** — rewrite the 2026-08-24 root cause so “app” / «приложуха» is the GitHub App `https://github.com/apps/adaptive-trust-ci`, not “nginx for the existing app”. Symptom may keep the ChatGPT URL (the log must name what was wrongly used). Keep ≤3 sentences.
2. **`decisions.md`** — add (or replace the voided-hostname entry with) a short ruling: operator application = GitHub App `https://github.com/apps/adaptive-trust-ci`; forget `ii-tonya`; do not treat any public website as the app; do not invent a public webhook URL; leave `TRUST_CI_PUBLIC_BASE_URL` on loopback. Keep ≤3 sentences per entry. Do not name a new hostname.
3. **Characterization** in `trust-ci/tests/test_m0_invariants.py` — smallest test that would have been red on the current tree:
   - existing five-doc `assertNotIn` ChatGPT URL/host stays;
   - `decisions.md` contains `https://github.com/apps/adaptive-trust-ci`;
   - `mistakes.md` does **not** contain `nginx for the existing app` (it may still contain the ChatGPT URL).
4. **This change package** — fill brief / requirements / architecture / test-plan / change-spec from this outcome. Optional one-line note that sibling `b66b86` retracted the URL; this slice retracts the nginx-as-app identity.
5. **Optional, not required:** reword M0.2 checkbox “repo webhook” → “GitHub App webhook” while leaving **not done** and placeholder `<ci>`. Do not fill a public URL. Keep phrases `local HMAC` / `not done` / `no public HTTPS` that `test_activation_report_operator_safe` already expects.

Protected-path note: `decisions.md` and `mistakes.md` are protected. The write owner needs an exact local grant naming those files (and the test file if also protected) in one fingerprint-bound batch. Do not read `.env` or PEM to “help” the grant.

---

## Out of scope (explicit non-goals)

- FastAPI, HMAC adapter, `trust-ci/src/**`, compose, gitignored `trust-ci/env/*.env`.
- GitHub App JWT, PEM, `PATCH /app/hook/config`, App settings form save, Recent Deliveries.
- Repository webhook create/list/delete (`GET/POST .../hooks`).
- TLS, certbot, Apache vhost install/uninstall/edit, DNS, probes of any `ii-tonya` hostname (including apex).
- Inventing a replacement public webhook URL or flipping `TRUST_CI_PUBLIC_BASE_URL` off loopback.
- Claiming M0.2 complete; protecting `main`; merge, push, tag, deploy.
- Rewriting historical `engineering/changes/**` evidence (`cec0c7`, `010964`, `b66b86` evidence stays).
- Activation-report App ID / slug / installation cells (already correct). Optional App-page URL there is **not** required this slice.
- README / spec body / `AGENTS.md` for this naming bug (they already speak of the GitHub App as Check owner, not a public website as the app).
- Reading webhook secret, App RSA, CI signing key, human approval private keys.

---

## Acceptance criteria

**P0 — identity locked**

1. **Given** `mistakes.md`, **when** a later agent reads the 2026-08-24 ChatGPT-hostname entry, **then** the root cause does not call that hostname “nginx for the existing app”; it records that the application is GitHub App `https://github.com/apps/adaptive-trust-ci` and that the hostname was a ChatGPT error, not the app.
2. **Given** `decisions.md`, **when** a later agent reads 2026-08-24 entries, **then** it sees `https://github.com/apps/adaptive-trust-ci` as the operator application and does not treat a public website as the app or as a pending `ii-tonya` edge to finish.
3. **Given** the five operator live-target docs, **when** `test_operator_docs_do_not_present_chatgpt_webhook_as_live` runs, **then** none contain `https://trust-ci.ii-tonya.ru/webhooks/github` or hostname `trust-ci.ii-tonya.ru`.
4. **Given** the new characterization, **when** it runs on the landed tree, **then** `decisions.md` contains `https://github.com/apps/adaptive-trust-ci` and `mistakes.md` does not contain `nginx for the existing app`.

**P0 — runtime frozen**

5. **Given** FastAPI and compose, **when** this slice lands, **then** `POST /webhooks/github` HMAC and `127.0.0.1:18080` are unchanged.
6. **Given** GitHub, **when** this slice lands, **then** no App hook was PATCHed and no repository webhook was created.
7. **Given** host TLS leftovers, **when** this slice lands, **then** Apache/DNS/certbot were not touched and no `ii-tonya` host was probed.
8. **Given** M0.2, **when** this slice lands, **then** the plan checkbox remains **not done** and activation-report public base remains `http://127.0.0.1:18080`.

**P1 — history**

9. Historical change-package evidence still names the ChatGPT URL. That is history, not operator truth. Do not rewrite `evidence/**` in sibling packages.

---

## Constraints

- Backward compatibility: no API/event/env contract change.
- Data/privacy: do not read PEM, webhook secret, env dumps, or App JWT.
- Operational: API stays loopback. Do not probe `ii-tonya`. Do not complete certbot.
- `decisions.md` / `mistakes.md` entries remain ≤3 sentences.
- `mistakes.md` may still quote the ChatGPT URL; the five-doc invariant must stay green.
- Source-of-truth order: this user correction outranks sibling briefs `cec0c7` / `010964` and the leftover “nginx for the existing app” sentence.

---

## Failure and edge cases

- Adding `https://github.com/apps/adaptive-trust-ci` to all five operator docs is **over-scope**. Activation report already has slug + IDs. Lock the identity in `decisions.md` (and optionally one activation-report sentence). Do not spray the App URL everywhere.
- Forbidding `ii-tonya` in `mistakes.md` would fail the log’s job (it must name the bad URL). Keep the URL there; change only the root-cause identity.
- Forbidding `ii-tonya` in `engineering/changes/**` would rewrite history. Out of scope.
- Rewording M0.2 “repo” → “App” without leaving **not done** / `no public HTTPS` can break `test_activation_report_operator_safe`. If touched, keep those phrases.
- A test that only `assertIn` the GitHub App URL in `decisions.md` without also forbidding “nginx for the existing app” in `mistakes.md` would miss the actual misread.

---

## Risk

Low. Docs + one characterization test. No trust-boundary mutation. Human gates: none on the route. Protected-path grant required for `decisions.md` / `mistakes.md`. Residual risk: a later agent still invents a public webhook URL; characterization + this ruling must say “none named.”

## Rollback

Revert the `decisions.md` / `mistakes.md` / invariant commit. No data, no runtime, no GitHub config to undo.

## Suggested change-spec seeds

- OBJ-001: Operator memory names the application as GitHub App `https://github.com/apps/adaptive-trust-ci` and forgets `ii-tonya` as any live target.
- Success metric: characterization green; five-doc ChatGPT-host invariant still green; FastAPI/GitHub/TLS untouched.
- FORBID: App JWT / hook PATCH; repo webhook; TLS/certbot/Apache; public webhook URL invention; `ii-tonya` probe; M0.2 claimed done.
