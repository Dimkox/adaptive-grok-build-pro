# Architecture — SHA-change invalidation

Authority: `evidence/analysis-architect.md`, `evidence/analysis-code_reviewer.md`.

Tracked compose stays DinD. Live worker uses untracked host-socket overlay. HMAC is loopback characterization of `/webhooks/github`, not GitHub hook registration.

`JobRequest.idempotency_key` includes `head_sha`. New SHA → new `job_id`; other active jobs for the same PR become `cancelled`/`superseded-head` in Postgres only (no GitHub PATCH of the old Check Run). `ensure_check_run` lists checks **on that SHA** and reuses only when `external_id == job_id`.

HMAC inside the **api container** so `TRUST_CI_WEBHOOK_SECRET` never appears in agent output: event `pull_request`, action `synchronize`, PR 5, `draft: true`, base `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`, head = GitHub `head.sha` after push. Headers `X-Hub-Signature-256` + `X-GitHub-Event`. Print HTTP / `job_id` / `created` / `status` only.

New job likely `needs_approval` because `decisions.md` remains in the PR diff. Expected.

## Grants

```text
python3 scripts/grok_approve.py production --action git-push-branch --resource milestone/m0-live-trust-authority --source explicit-user-consent --reason "user далее after named SHA-change slice" --ttl 30
```

Mint **after** the commit being pushed. Resource is the branch name, not `*`.
