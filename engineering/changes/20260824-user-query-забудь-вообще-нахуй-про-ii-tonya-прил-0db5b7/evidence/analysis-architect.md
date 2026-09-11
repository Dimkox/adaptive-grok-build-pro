# Architect ruling — «приложуха» is GitHub App adaptive-trust-ci, not a public website

Route `0db5b77a9bf3`. Change `engineering/changes/20260824-user-query-забудь-вообще-нахуй-про-ii-tonya-прил-0db5b7`. Write owner: `general_implementer`. This agent did not read `.env`, PEM, webhook secrets, or GitHub App keys. Did not PATCH `/app/hook/config`, register a repository webhook, probe any public hostname, edit host Apache/DNS/certbot, or recreate compose.

Sources: user correction (verbatim); sibling `analysis-docs_researcher.md`, `analysis-repo_explorer.md`; `trust-ci/tests/test_m0_invariants.py`; `decisions.md`; `mistakes.md`; plan/spec/activation report/README; prior retraction slice `b66b86`.

## Ruling (one paragraph)

**Docs-and-characterization only.** Expand `test_operator_docs_do_not_present_chatgpt_webhook_as_live` so the five operator docs (plan, spec, activation report, root README, `decisions.md`) contain **no** substring `ii-tonya` (stronger than last slice’s `trust-ci.` subdomain only). Test-file constants may keep the old URL/host as scan needles. Add a **failing** assertion that `decisions.md` names `https://github.com/apps/adaptive-trust-ci`. Prepend a ≤3-sentence `decisions.md` entry: «приложуха» is that GitHub App; webhook config lives on that App; the ChatGPT-invented public hostname is out of this work. Keep the prior ChatGPT-hostname `mistakes.md` entry, but rewrite «nginx for the existing app» so it no longer teaches that a public website is the app; add a new mistakes entry whose root cause is overloaded Russian «приложение». Leave FastAPI, compose, gitignored env, host Apache, GitHub App hook config, plan/spec/activation/README body, and historical change-package evidence alone. Do not invent a replacement public webhook URL. Do not name that public domain as a live target in `decisions.md`. Do not claim M0.2 complete. Do not protect `main`.

---

## 1. Defect and root cause

User (verbatim): `забудь вообще нахуй про ii-tonya, приложуха - это приложение github https://github.com/apps/adaptive-trust-ci`.

Last slice (`b66b86`) already voided the ChatGPT webhook hostname in the five operator docs and forbade `trust-ci.` + that host. That is **not enough**: agents still collapse «приложуха» / «приложение» onto a public website.

| Plane | Fact |
| --- | --- |
| Live API | Unchanged. `POST http://127.0.0.1:18080/webhooks/github` HMAC. Compose publish `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. |
| Documented public base | Activation report: `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`. |
| GitHub App identity (activation report) | Slug `adaptive-trust-ci`, App ID `4694114`, Installation ID `156003193`. Literal page `https://github.com/apps/adaptive-trust-ci` is **absent**. |
| Five operator docs | **No** `ii-tonya` today (explorer). Negative scan of last slice’s host still green. |
| `decisions.md` | Does **not** name `https://github.com/apps/adaptive-trust-ci`. First 2026-08-24 entries void “a ChatGPT-invented public webhook hostname” without saying what «the app» is. |
| `mistakes.md` | Symptom still quotes the ChatGPT URL (allowed; not in the five-doc scan). Root cause still says **«That name is nginx for the existing app»** — the live defect. |
| M0.2 webhook | Plan: `POST https://<ci>/webhooks/github` — **not done**. Still says “repo webhook”; do **not** reword this slice. |
| FastAPI | Unchanged. HMAC adapter already proven on loopback. |

Root cause (not the symptom): overloaded Russian «приложение» means both a GitHub App and a public website. Agents bound «приложуха» to a ChatGPT public hostname instead of `https://github.com/apps/adaptive-trust-ci`.

A naive keep-as-is of last slice’s `assertNotIn(CHATGPT_WEBHOOK_HOST)` would **stay green** and would **not** lock apex/`www` forms. Expanding the needle to substring `ii-tonya` is the lock. A **new** `assertIn("https://github.com/apps/adaptive-trust-ci", decisions)` is the failing characterization for the identity entry.

---

## 2. Frozen contract

No HTTP, event, or env contract change.

| Item | Frozen value |
| --- | --- |
| Intake | `POST /webhooks/github`, HMAC `X-Hub-Signature-256` over raw body |
| Proven delivery path | Loopback HMAC `http://127.0.0.1:18080/webhooks/github` only |
| Public GitHub delivery | **Absent.** Do not PATCH App hook. Do not create a repository webhook. |
| GitHub App | Existing registration `adaptive-trust-ci` (`https://github.com/apps/adaptive-trust-ci`). Webhook **config surface** is that App. This slice does not edit it. |
| `TRUST_CI_PUBLIC_BASE_URL` | Stays gitignored loopback `http://127.0.0.1:18080`. Do not invent a public URL. |
| Tracked placeholders | Spec/plan: `https://<ci>/webhooks/github`. Leave them. They are not a live URL. |
| OpenAPI | Still none (`openapi_url=None`) |

Do not rewrite `test_webhooks_github.py` / `test_api.py`.

---

## 3. Exact files to change

### Required (product tree; write owner)

| File | Change |
| --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | **First.** Expand the five-doc negative scan to substring `ii-tonya`. Add a failing assertion that `decisions.md` contains `https://github.com/apps/adaptive-trust-ci`. Add a failing assertion that `mistakes.md` does not contain `nginx for the existing app`. Keep URL/host constants as needles. **Do not** scan `mistakes.md` or `engineering/changes/**` for `ii-tonya`. |
| `decisions.md` | **New** ≤3-sentence 2026-08-24 entry at the top of the dated list. Name the GitHub App page. Say webhook config lives on that App. Say the ChatGPT public hostname is out of this work. **Zero** `ii-tonya`. Do not rewrite the prior void/Apache leftover entries except if a stray `ii-tonya` appeared (it has not). |
| `mistakes.md` | Keep the ChatGPT-hostname entry (symptom may still quote the ChatGPT URL). Rewrite the «nginx for the existing app» sentence. **Add** a new entry: «приложуха» was misread as a public website; root cause = overloaded Russian «приложение». |

### This change package (write owner fills from this ruling; not the invariant scan)

`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `change-spec.yaml`, `rollback.md`, `release.md`, `tasks.md`.

When filling stubs, do **not** copy the user-query hostname into the five operator docs. Change-package files may name the needle as the thing being forgotten; they are not in the scan.

### Do not change

- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` (M0.2 checkbox stays **not done**; do not retitle repo→App this slice)
- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md` (slug/IDs already match the GitHub App; public base stays loopback)
- `README.md`, `trust-ci/README.md`, `AGENTS.md`, `trust-ci/env/common.env.example`
- `trust-ci/src/**` (FastAPI, webhooks, github_app, worker), `trust-ci/compose.yaml`, gitignored `trust-ci/env/*.env`
- Sibling `engineering/changes/**` evidence and already-retracted briefs (`b66b86`, `cec0c7`, `010964`)
- Host Apache / DNS / certbot / ufw / compose recreate
- VERSION / CHANGELOG / GitHub App hook / repo hooks / branch protection

`mistakes.md` **may** still contain `ii-tonya` (the named ChatGPT URL). The invariant **must not** scan `mistakes.md` or `engineering/changes/**` for that substring, or the log and this change-id would fail the test.

---

## 4. Characterization tests (add/expand first)

Keep existing module-level needles and add the stronger one. Reuse `SPEC`, `PLAN`, `REPORT`, `README`, `DECISIONS`, `ROOT`.

```python
CHATGPT_WEBHOOK_URL = "https://trust-ci.ii-tonya.ru/webhooks/github"
CHATGPT_WEBHOOK_HOST = "trust-ci.ii-tonya.ru"
CHATGPT_PUBLIC_SITE_NEEDLE = "ii-tonya"
GITHUB_APP_PAGE = "https://github.com/apps/adaptive-trust-ci"
MISTAKES = ROOT / "mistakes.md"


def test_operator_docs_do_not_present_chatgpt_webhook_as_live(self) -> None:
    operator_docs = (SPEC, PLAN, REPORT, README, DECISIONS)
    for path in operator_docs:
        self.assertTrue(path.is_file(), path.as_posix())
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(CHATGPT_WEBHOOK_URL, text, path.as_posix())
        self.assertNotIn(CHATGPT_WEBHOOK_HOST, text, path.as_posix())
        self.assertNotIn(CHATGPT_PUBLIC_SITE_NEEDLE, text, path.as_posix())


def test_decisions_name_the_app_as_github_app_page(self) -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    self.assertIn(GITHUB_APP_PAGE, text)
    self.assertNotIn(CHATGPT_PUBLIC_SITE_NEEDLE, text)


def test_mistakes_do_not_call_public_nginx_the_existing_app(self) -> None:
    text = MISTAKES.read_text(encoding="utf-8")
    self.assertNotIn("nginx for the existing app", text)
    self.assertIn(GITHUB_APP_PAGE, text)
```

**Current tree**

| Test | Expected before docs edit |
| --- | --- |
| expanded `test_operator_docs_do_not_present_chatgpt_webhook_as_live` | **green** (five docs already lack `ii-tonya`; this is the lock) |
| `test_decisions_name_the_app_as_github_app_page` | **red** (`decisions.md` lacks `https://github.com/apps/adaptive-trust-ci`) |
| `test_mistakes_do_not_call_public_nginx_the_existing_app` | **red** (`nginx for the existing app` still present; GitHub App page absent) |

Do not weaken with an allowlist. Do not scan change-package stubs (they currently echo the user query). Do not HTTP-probe any public hostname.

Prove red before the docs edits:

```bash
python3 -m unittest \
  trust-ci.tests.test_m0_invariants.M0InvariantTests.test_operator_docs_do_not_present_chatgpt_webhook_as_live \
  trust-ci.tests.test_m0_invariants.M0InvariantTests.test_decisions_name_the_app_as_github_app_page \
  trust-ci.tests.test_m0_invariants.M0InvariantTests.test_mistakes_do_not_call_public_nginx_the_existing_app
```

---

## 5. Proposed text

### `decisions.md` — prepend (≤3 sentences, **no** `ii-tonya`)

Do not treat the ChatGPT hostname as a live target here. Refer to it only as a voided invented public hostname.

```markdown
## 2026-08-24 — «Приложуха» is GitHub App adaptive-trust-ci

Operator «приложуха» is GitHub App `adaptive-trust-ci` at `https://github.com/apps/adaptive-trust-ci`. Webhook configuration lives on that App registration, not on a public website and not as a substitute repository webhook. The ChatGPT-invented public hostname is out of this work; proven intake remains loopback HMAC `127.0.0.1:18080`.
```

Leave the existing void-hostname and Apache-leftover entries in place. They already omit the forbidden substring. Do not add a new “wait for HTTPS on \<that host\>” instruction. Do not invent a replacement public webhook URL.

### `mistakes.md` — keep prior ChatGPT entry; fix the bad sentence; add the new root cause

**Rewrite only the root-cause paragraph** of `2026-08-24 — Treated a ChatGPT hostname as the live webhook URL`. Symptom may keep the ChatGPT URL.

Replace:

```text
**Root cause:** A ChatGPT-invented hostname was copied as operator truth. That name is nginx for the existing app, not Trust CI on claw; do not configure, probe, or complete TLS for it.
```

with:

```text
**Root cause:** A ChatGPT-invented hostname was copied as operator truth. That hostname is unrelated public nginx, not the GitHub App and not Trust CI on claw; do not configure, probe, or complete TLS for it.
```

**Prepend a new entry** (may name the GitHub App page; may name the ChatGPT URL as the logged mistake; `mistakes.md` is not in the five-doc `ii-tonya` scan):

```markdown
## 2026-08-24 — Misread «приложуха» as a public website

**Symptom:** Agents treated «приложуха» as a public website (nginx/vhost) instead of GitHub App `https://github.com/apps/adaptive-trust-ci`.
**Root cause:** Overloaded Russian «приложение» means both a GitHub App and a public website, so the two were collapsed into one live target.
```

---

## 6. Acceptance criteria (for this package)

1. **Given** the five operator docs, **when** the expanded `test_operator_docs_do_not_present_chatgpt_webhook_as_live` runs, **then** none contain substring `ii-tonya` (nor the old URL/host needles).
2. **Given** `decisions.md` **before** the new entry, **when** `test_decisions_name_the_app_as_github_app_page` runs, **then** it fails; **after** the entry, it passes and the file still has no `ii-tonya`.
3. **Given** `mistakes.md` **before** the rewrite, **when** `test_mistakes_do_not_call_public_nginx_the_existing_app` runs, **then** it fails on `nginx for the existing app`; **after** the rewrite + new entry, that phrase is gone, the GitHub App page is present, and the prior ChatGPT-URL symptom remains.
4. **Given** this slice, **then** no FastAPI/compose/env/host Apache/GitHub hook/certbot/DNS change; no invented public webhook URL; no M0.2-complete claim; `main` unprotected; plan checkbox remains **not done**; activation-report public base remains `http://127.0.0.1:18080`.

---

## 7. Forbidden this slice

- `PATCH /app/hook/config` or any App JWT/PEM read.
- `POST /repos/{owner}/{repo}/hooks` or GitHub UI webhook create.
- Certbot, DNS A/AAAA, Apache vhost edit, `a2dissite`/`a2ensite`, compose recreate, ufw.
- Setting `TRUST_CI_PUBLIC_BASE_URL` to any new public URL.
- Probing any `ii-tonya` hostname (user: forget it).
- Putting `ii-tonya` into `decisions.md` (including “do not use \<that host\>” that would fail the expanded scan).
- Inventing a replacement public webhook URL (do not promote `ci.example.com` or `<ci>` into a live claim).
- Checking the M0.2 webhook box, rewording plan “repo webhook” → “App webhook”, or protecting `main`.
- Editing FastAPI / `api.py` / `webhooks.py`.
- Rewriting historical `engineering/changes/**` evidence.
- Claiming M0.2 complete.

---

## 8. Sequence for `general_implementer`

1. Expand/add the three tests in `trust-ci/tests/test_m0_invariants.py`. Confirm the two new tests are red and the expanded five-doc scan is green.
2. Prepend the `decisions.md` entry (no `ii-tonya`). Confirm `test_decisions_name_the_app_as_github_app_page` is green.
3. Fix `mistakes.md` (rewrite «nginx for the existing app»; add the overloaded-«приложение» entry). Confirm `test_mistakes_do_not_call_public_nginx_the_existing_app` is green.
4. Fill this change-package brief/AC/architecture/test-plan/rollback from this ruling.
5. `python3 -m unittest trust-ci.tests.test_m0_invariants`
6. `python3 scripts/grok_verify.py --mode pr`
7. Stop. Independent `code_reviewer` and `test_reviewer` only after verify. No push/merge/deploy.

---

## 9. Rollback

Git revert of `trust-ci/tests/test_m0_invariants.py`, `decisions.md`, `mistakes.md` (and this change-package fill). No host, data, GitHub, or compose rollback. Residual host Apache vhost from `010964` is **unchanged** by both apply and rollback.

---

## 10. Residual risk

Historical packages (`cec0c7`, `010964`, `b66b86`) still name the ChatGPT hostname as retracted evidence. Future agents can rediscover it there or from leftover host Apache. Product-side stop is the stronger five-doc `ii-tonya` lock, the GitHub App page in `decisions.md`, and the corrected `mistakes.md` model. Uninstalling host leftovers and registering a real App webhook remain later, explicitly ordered slices — not this one.

No merge authority. Local receipts are not the App-owned check.
