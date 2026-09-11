# Architect ruling — retract ChatGPT webhook URL as live operator target

Route `b66b867ba5ab`. Change `engineering/changes/20260824-user-query-https-trust-ci-ii-tonya-ru-webhooks-g-b66b86`. Write owner: `integration_implementer`. This agent did not read `.env`, PEM, webhook secrets, or GitHub App keys. Did not PATCH `/app/hook/config`, register a repository webhook, probe `https://trust-ci.ii-tonya.ru/webhooks/github`, edit host Apache/DNS/certbot, or recreate compose.

Sources: user correction (verbatim); sibling `analysis-docs_researcher.md`, `analysis-repo_explorer.md`, `analysis-integration_architect.md`; `trust-ci/tests/test_m0_invariants.py`; `decisions.md`; `mistakes.md`; plan/spec/activation report/README; sibling briefs `cec0c7` and `010964`.

## Ruling (one paragraph)

**Docs-and-characterization only.** Add a failing invariant in `trust-ci/tests/test_m0_invariants.py` that tracked operator docs (plan, spec, activation report, root README, `decisions.md`) do not contain `https://trust-ci.ii-tonya.ru/webhooks/github` or hostname `trust-ci.ii-tonya.ru`. Retract the 2026-08-24 Apache TLS `decisions.md` entry so it no longer names that hostname as the pending TLS target. Log the root cause in `mistakes.md`. Leave FastAPI, compose, gitignored env, host Apache, GitHub App hook config, and plan/spec/activation/README body alone: they already use placeholder `https://<ci>/webhooks/github` or loopback `http://127.0.0.1:18080`. Do not invent a replacement public webhook URL. Do not claim M0.2 complete. Do not protect `main`. Historical change-package evidence stays; optional one-line retraction on sibling briefs `cec0c7` and `010964` only.

---

## 1. Defect and root cause

User (verbatim): `https://trust-ci.ii-tonya.ru/webhooks/github нет , не трогаем, это ошибка chatgpt`.

| Plane | Fact |
| --- | --- |
| Live API | `POST http://127.0.0.1:18080/webhooks/github` HMAC. Compose publish `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`. |
| Documented public base | Activation report: `TRUST_CI_PUBLIC_BASE_URL` = `http://127.0.0.1:18080`. |
| M0.2 webhook | Plan: `POST https://<ci>/webhooks/github` — **not done** (no public HTTPS). |
| Spec | Placeholder `POST https://<ci>/webhooks/github`. No `ii-tonya.ru`. |
| Product README / `trust-ci/README.md` | No ChatGPT host. Product example remains `https://ci.example.com/webhooks/github` (placeholder, not a live URL). |
| `decisions.md` | **Current leak.** Heading `Apache TLS edge waits on DNS A, not on Apache ports` still presents `trust-ci.ii-tonya.ru` as the ACME/pending-HTTPS hostname. |
| Sibling `cec0c7` brief | Still orders App webhook URL = that ChatGPT URL. Evidence: never applied (JWT forbidden; reviews NO-GO). |
| Sibling `010964` | Installed host Apache HTTP vhost for that ServerName; stopped before certbot. User now: **не трогаем** — leave Apache as-is; do not uninstall, do not complete TLS. |
| FastAPI contract | Unchanged. Integration architect freeze stands. |

Root cause (not the symptom): agents treated a ChatGPT-invented hostname as operator truth. AGENTS.md source-of-truth order puts user correction above sibling briefs and prior `decisions.md` entries.

A naive `assertNotIn("https://trust-ci.ii-tonya.ru/webhooks/github")` on the five operator files would **pass today** (exact URL is absent there). The live defect in those files is the **hostname as pending TLS target** in `decisions.md`. The characterization must therefore forbid both the exact URL and the hostname in those five files so the new test is red before the retraction.

---

## 2. Frozen contract (api-event-change)

No HTTP, event, or env contract change.

| Item | Frozen value |
| --- | --- |
| Intake | `POST /webhooks/github`, HMAC `X-Hub-Signature-256` over raw body |
| Proven delivery path | Loopback HMAC `http://127.0.0.1:18080/webhooks/github` only |
| Public GitHub delivery | **Absent.** Do not register App or repo webhook this slice |
| `TRUST_CI_PUBLIC_BASE_URL` | Stays gitignored loopback `http://127.0.0.1:18080`. Do not set to the ChatGPT host. |
| Tracked placeholders | Spec/plan: `https://<ci>/webhooks/github`. `trust-ci/README.md` / `common.env.example`: `https://ci.example.com`. These are **not** a new live URL. |
| OpenAPI | Still none (`openapi_url=None`) |

Existing `test_webhooks_github.py` / `test_api.py` already freeze HMAC. Do not rewrite them for this retraction.

---

## 3. Exact files to change

### Required (product tree; write owner)

| File | Change |
| --- | --- |
| `trust-ci/tests/test_m0_invariants.py` | **First.** Add `test_operator_docs_do_not_present_chatgpt_webhook_as_live`. |
| `decisions.md` | Replace the 2026-08-24 Apache TLS entry. Do not leave the hostname as pending TLS/webhook target. Keep ≤3 sentences. |
| `mistakes.md` | New 2026-08-24 entry. Name the URL. Root cause: treating ChatGPT-invented hostname as operator truth. |

### Optional (user-allowed; recommended because they still look like live orders)

| File | Change |
| --- | --- |
| `engineering/changes/20260824-configure-github-app-webhook-pull-request-https-cec0c7/brief.md` | One-line retraction banner at top. Do not rewrite evidence. |
| `engineering/changes/20260824-m0-2-public-tls-edge-apache-trust-ci-ii-tonya-ru-010964/brief.md` | One-line retraction banner at top. Do not rewrite evidence. |

### This change package (write owner fills from this ruling; not the invariant scan)

`brief.md`, `requirements.md`, `architecture.md`, `test-plan.md`, `change-spec.yaml`, `rollback.md`, `release.md`, `tasks.md` — replace user-query stubs with the scope below.

### Do not change

- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md`
- `README.md`, `trust-ci/README.md`, `trust-ci/env/common.env.example`
- `trust-ci/src/**`, `trust-ci/compose.yaml`, gitignored `trust-ci/env/*.env`
- Sibling `evidence/**` (including `010964` vhost script and probes)
- Host Apache / DNS / certbot / ufw / compose recreate
- VERSION / CHANGELOG / GitHub App / repo hooks / branch protection

`mistakes.md` **must** name `https://trust-ci.ii-tonya.ru/webhooks/github`. The invariant **must not** scan `mistakes.md` or `engineering/changes/**`, or the log and historical evidence would fail the test.

---

## 4. Failing characterization test (add first)

Append to `M0InvariantTests` in `trust-ci/tests/test_m0_invariants.py`. Reuse existing `SPEC`, `PLAN`, `REPORT`, `ROOT`.

```python
def test_operator_docs_do_not_present_chatgpt_webhook_as_live(self) -> None:
    chatgpt_url = "https://trust-ci.ii-tonya.ru/webhooks/github"
    chatgpt_host = "trust-ci.ii-tonya.ru"
    paths = (
        SPEC,
        PLAN,
        REPORT,
        ROOT / "README.md",
        ROOT / "decisions.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        self.assertNotIn(chatgpt_url, text, path.as_posix())
        self.assertNotIn(chatgpt_host, text, path.as_posix())
```

**Current tree:** red on `decisions.md` (hostname in the Apache TLS entry). Plan/spec/report/README already lack both strings.

**After retraction:** green if `decisions.md` no longer contains the hostname or the exact URL. Do not quote the hostname in the replacement `decisions.md` entry (put the named URL only in `mistakes.md` and in this test constant).

Prove red before the docs edit:

```bash
python3 -m unittest trust-ci.tests.test_m0_invariants.M0InvariantTests.test_operator_docs_do_not_present_chatgpt_webhook_as_live
```

Do not weaken the test with a retraction allowlist. If a future agent re-teaches the hostname in operator docs, CI must fail.

---

## 5. Proposed text

### `decisions.md` — replace the Apache TLS heading and body

Remove:

```text
## 2026-08-24 — Apache TLS edge waits on DNS A, not on Apache ports
```

and the three sentences that name `trust-ci.ii-tonya.ru` as the ACME vhost / pending HTTPS.

Insert (≤3 sentences, **no** hostname so the invariant stays green):

```markdown
## 2026-08-24 — Invented public webhook hostname is not operator truth (retracted)

A ChatGPT-invented public HTTPS webhook URL was never operator-approved and is not the live GitHub delivery target. Do not use it as the GitHub App webhook, pending TLS hostname, or `TRUST_CI_PUBLIC_BASE_URL`. Host Apache stays as-is this slice; the API remains `http://127.0.0.1:18080`; public GitHub webhook registration and M0.2 remain incomplete.
```

Do not add a new “wait for HTTPS on \<that host\>” instruction. Loopback public base is already recorded in the activation report.

### `mistakes.md` — prepend after the intro (name the URL)

```markdown
## 2026-08-24 — Treated a ChatGPT-invented hostname as operator truth

**Symptom:** Sibling briefs and `decisions.md` treated `https://trust-ci.ii-tonya.ru/webhooks/github` as the live GitHub App webhook and pending Apache TLS target, and claw received an HTTP ACME vhost for that name.
**Root cause:** Treating a ChatGPT-invented hostname as operator truth instead of requiring an explicit operator-owned public URL.
```

### Optional sibling brief one-liners

`cec0c7/brief.md` (first line after the title):

```markdown
> **Retracted 2026-08-24:** the Webhook URL in the user order below is a ChatGPT invention, not a live GitHub App webhook. Do not PATCH the App or complete TLS for that hostname.
```

`010964/brief.md` (first line after the title):

```markdown
> **Retracted 2026-08-24:** the hostname in this package is a ChatGPT invention, not operator truth. Leave host Apache as-is; do not treat that URL as the live webhook.
```

(`010964` one-liner should also avoid putting `trust-ci.ii-tonya.ru` if a later invariant ever widens; “the hostname in this package” is enough. The user allowed naming it. Either is fine because briefs are not in the scan.)

---

## 6. Acceptance criteria (for this package)

1. **Given** the five operator docs, **when** `test_operator_docs_do_not_present_chatgpt_webhook_as_live` runs on the current tree **before** the `decisions.md` edit, **then** it fails on `decisions.md`.
2. **Given** the retracted `decisions.md` and the new `mistakes.md` entry, **when** the same test runs, **then** it passes; plan still says webhook **not done**; activation-report `TRUST_CI_PUBLIC_BASE_URL` is still `http://127.0.0.1:18080`.
3. **Given** this slice, **then** no FastAPI/compose/env/host Apache/GitHub hook/certbot/DNS change; no M0.2-complete claim; `main` unprotected.

---

## 7. Forbidden this slice

- `PATCH /app/hook/config` or any App JWT/PEM read.
- `POST /repos/{owner}/{repo}/hooks` or GitHub UI webhook create.
- Certbot, DNS A/AAAA, Apache vhost edit, `a2dissite`/`a2ensite`, compose recreate, ufw.
- Setting `TRUST_CI_PUBLIC_BASE_URL` to the ChatGPT host (or any new public URL).
- Re-probing `https://trust-ci.ii-tonya.ru/webhooks/github` (user: не трогаем).
- Inventing a replacement public webhook URL (do not promote `ci.example.com` or `<ci>` from placeholders into a live claim).
- Checking the M0.2 webhook box or protecting `main`.
- Uninstalling the leftover Apache vhost (out of scope; leftover, not this repair).

---

## 8. Sequence for `integration_implementer`

1. Add the test. Confirm red.
2. Retract `decisions.md`. Confirm the test is green.
3. Add `mistakes.md`.
4. Optional sibling brief banners.
5. Fill this change-package brief/AC/architecture/test-plan/rollback from this ruling.
6. `python3 -m unittest trust-ci.tests.test_m0_invariants`
7. `python3 scripts/grok_verify.py --mode pr`
8. Stop. Independent `code_reviewer` and `test_reviewer` only after verify. No push/merge/deploy.

---

## 9. Rollback

Git revert of `test_m0_invariants.py`, `decisions.md`, `mistakes.md` (and optional brief banners). No host, data, or GitHub rollback. No compose. Residual host Apache vhost from `010964` is **unchanged** by both apply and rollback.

---

## 10. Residual risk

Claw still has `/etc/apache2/sites-enabled/trust-ci.conf` for the ChatGPT ServerName (explorer). Future agents can rediscover it from host state or from historical `010964`/`cec0c7` evidence. Product-side stop is the invariant + retracted `decisions.md` + `mistakes.md`. Uninstalling that vhost is a later, explicitly ordered host slice — not this one.

No merge authority. Local receipts are not the App-owned check.
