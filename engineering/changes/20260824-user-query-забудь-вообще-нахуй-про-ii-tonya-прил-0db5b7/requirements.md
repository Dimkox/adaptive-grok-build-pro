# Requirements — GitHub App is the application

## Acceptance criteria

- [x] Given the five operator docs, when the M0 invariant runs, then none contain substring `ii-tonya`.
- [x] Given `decisions.md`, when an agent reads current entries, then it contains `https://github.com/apps/adaptive-trust-ci` and does not name a public website as the application.
- [x] Given `mistakes.md`, when an agent reads the ChatGPT-hostname entry, then it does not say `nginx for the existing app`.
- [x] Given FastAPI/compose/GitHub/host, when this slice lands, then they are unchanged: no App hook PATCH, no repo webhook, no TLS work, no invented public URL.
- [x] M0.2 plan checkbox remains **not done**. Activation-report public base remains `http://127.0.0.1:18080`.

## Failure and edge cases

- Test file constants may still hold forbidden host strings as scan needles.
- Historical `engineering/changes/**` may still quote that domain; leave them.
- `mistakes.md` may still name the ChatGPT URL as the logged mistake.

## Non-functional

- Security: no PEM/JWT/secret reads; no GitHub hook API.
- Observability: do not claim public webhook live.
