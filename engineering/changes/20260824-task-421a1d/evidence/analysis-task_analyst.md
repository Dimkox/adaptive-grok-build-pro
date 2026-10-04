# task_analyst — App ID `<redacted-app-id>` / Installation ID <redacted-installation-id> (421a1ddd7770)
Loaded `/adaptive-delivery`. Change `…-421a1d` is `draft`; `human_gates` empty; write owner `general_implementer`. User integers are operator-safe (not PEM).
## Outcome
Claw worker authenticates as GitHub App `<redacted-app-id>` / installation `<redacted-installation-id>`. IDs live in gitignored worker env and the operator-safe activation report. Worker+DinD+runner-loader start. Webhook only on a real public HTTPS URL.
## In scope
Set `TRUST_CI_GITHUB_APP_ID=<redacted-app-id>` and `TRUST_CI_GITHUB_INSTALLATION_ID=<redacted-installation-id>` in gitignored `trust-ci/env/worker.env` (`trust-ci/env/*.env`; never chat-dump PEM/JWT). `docker compose up` services `worker`, `docker-engine` (DinD), `runner-loader`. Fill App ID + Installation ID on `engineering/runbooks/trust-ci-activation-report.md`.
## Out / forbidden
Read `.env`/PEM/keys; put App IDs on the API; `branch-protect`; merge or ready PR #5; GitHub Actions; forge Check Runs / fake GitHub webhook delivery; host 8080; M0.3.
## Acceptance
- worker.env remains untracked; IDs set; no PEM in git or chat.
- Compose shows `worker` + `docker-engine` + `runner-loader` up, or the exact start failure is recorded.
- Activation report: App ID `<redacted-app-id>`, Installation ID `<redacted-installation-id>`. Current `TRUST_CI_PUBLIC_BASE_URL` is `http://<loopback-trust-ci>` (not public HTTPS) → record webhook **blocked**; register `POST https://<public>/webhooks/github` only if that URL exists.
- `main` stays unprotected; PR #5 is not merged.
This agent does not implement, compose-up, push, or merge.
