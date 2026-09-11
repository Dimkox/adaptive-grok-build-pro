# Architect ruling — route c36377792135
User rejected the UI-only stop. Write owner: `general_implementer`. This agent did not read `.env`/`api.env`/PEM and did not print `TRUST_CI_WEBHOOK_SECRET`, JWT, or PEM.
**Ruling:** `docker exec` worker App-JWT `PATCH https://api.github.com/app/hook/config` is allowed iff PEM/secret/JWT never appear in agent stdout, chat, or this package.
Mint JWT only inside compose service `worker` via `generate_app_jwt` reading the already-mounted `/run/secrets/github-app-private-key.pem`; never `cat` the PEM on the host; never use an installation token or the host `gh` user token (401 JWT decode).
Inject `TRUST_CI_WEBHOOK_SECRET` only from compose service `api` env through a stdin pipe into that worker process; never `printenv`/`cat api.env`; never persist the secret on `runtime/control`.
PATCH JSON: `url=https://claw.taild9f611.ts.net/webhooks/github` (no trailing slash), `content_type=json`, `secret=<injected>`, `insecure_ssl="0"`; `Authorization: Bearer` App JWT (`iss`=App ID `4694114`).
Print only HTTP status and GitHub-redacted config (`url`, `content_type`, `insecure_ssl`; `secret` must stay `********`), including a same-JWT `GET /app/hook/config` confirmation.
Do not `POST /repos/Dimkox/adaptive-grok-build-pro/hooks`; keep repo hooks `[]`.
Do not `tailscale funnel reset`; Funnel `/webhooks/github` stays; do not rewrite the `10.200.200.1` target.
Do not set `insecure_ssl=1`, edit FastAPI, or move `TRUST_CI_PUBLIC_BASE_URL` off `http://127.0.0.1:18080`.
PATCH does not subscribe events; if signed `ping` 200 `ignored-event` appears but PR jobs do not, the operator still ticks App UI Pull request.
Live success is GitHub Recent Deliveries POSTing to the Funnel URL; UI Active, loopback HMAC, and unsigned Funnel 401 are not this slice; M0.2 stays incomplete until that delivery.
This is an ops action: do not add a product `/app/hook` client; optional docs only after a real delivery.
If PreToolUse denies docker-exec or `github-api`, record the deny and stop; do not fall back to UI-only or a repository webhook.
User-approved operational scope (#1 source of truth) overrides `decisions.md` UI-only path for this container-JWT PATCH only; credentials still must never enter agent stdout.
