# Requirements — retract ChatGPT webhook URL

## Acceptance criteria

- [x] Given the five operator docs (plan, spec, activation report, root README, `decisions.md`), when `test_operator_docs_do_not_present_chatgpt_webhook_as_live` runs, then none contain `https://trust-ci.ii-tonya.ru/webhooks/github` or hostname `trust-ci.ii-tonya.ru`.
- [x] Given `decisions.md`, when an agent reads the Apache TLS entry, then it does not name that hostname as the pending TLS/webhook target; `TRUST_CI_PUBLIC_BASE_URL` stays loopback until a **named** public HTTPS path exists.
- [x] Given `mistakes.md`, when a later slice starts, then it records: ChatGPT-invented hostname was treated as operator truth; do not configure or probe that webhook URL.
- [x] Given FastAPI and compose, when this slice lands, then `POST /webhooks/github` HMAC and `127.0.0.1:18080` are unchanged.
- [x] Given GitHub, when this slice lands, then no App webhook was set to the ChatGPT URL and no repository webhook was created.
- [x] Given host Apache leftovers from `010964`, when this slice lands, then they were not edited, certbot was not run, and DNS was not changed.
- [x] M0.2 plan checkbox remains **not done**. Activation-report public base remains `http://127.0.0.1:18080`.

## Failure and edge cases

- A naive URL-only `assertNotIn` on the five files would pass today; the test must also forbid the hostname so `decisions.md` is red before retraction.
- Historical change-package evidence may still name the URL; that is history, not operator truth. Do not rewrite `evidence/**`.
- `mistakes.md` may name the URL; it is not one of the five scanned operator docs.

## Non-functional requirements

- Security: no PEM/JWT/secret reads; no GitHub hook API; no `insecure_ssl`.
- Reliability: loopback HMAC remains the only proven intake.
- Observability: do not claim public webhook live.
