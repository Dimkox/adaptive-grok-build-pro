# docs_researcher — live Trust Authority (M0) requirements

Sources: `DARK_FACTORY_ROADMAP.md` M0, `engineering/runbooks/trust-ci-rollout.md`, `trust-ci/README.md`, `AGENTS.md`, `decisions.md`, `mistakes.md`. No secrets. No APIs invented.

## M0 exit criteria (verbatim, `DARK_FACTORY_ROADMAP.md`)

```text
main protected = true
required check = current adaptive-trust-ci/verified@<policy-sha12>
required check app_id = adaptive-trust-ci App ID
exact-SHA disposable PR = success
signed attestation = independently verified
protected-path approval flow = proven
backup + restore + restart drill = pass
kill switch = pass
no GitHub Actions = true
```

Roadmap also: apply branch protection **only after** the live check succeeded; bind exact policy-epoch check + GitHub App ID; prove no direct push/force-push/delete/merge without that check; then remove/supersede bootstrap-exception language.

## Deploy sequence (runbook + `trust-ci/README.md`; no secret values)

1. Isolated CI host; copy example env/policy/trust-store; mount holdout outside checkout; generate CI/human keys off-server; GitHub App Checks/Contents/PRs; worker-only App RSA.
2. Pin images by digest; `holdout-digest`; write sha256 into env + `runtime/policy.json`.
3. `docker compose up -d postgres migrate api worker`; `/health/ready`.
4. HTTPS webhook `POST /webhooks/github` (API-only HMAC). API has no GitHub credentials and cannot publish success.
5. **Prove before protect** (do not continue if ambiguous): disposable unprotected-docs PR → PG job for exact head SHA → worker (not API) Check Run `adaptive-trust-ci/verified@<policy-sha12>` with `external_id`=job id, App-owned → runner: pinned digest, holdout, `--network none`, no secrets/socket → offline attestation verify → SHA change invalidates old check → policy/holdout change retitles check → `trust-ci/**` needs Ed25519 human approval then same durable Check Run → source mutation fails integrity.
6. Only then protect `main` with a **temporary human admin token** (never grant admin to the long-lived App).

README order: deploy API/PG/worker → webhook → disposable PR → observe App-owned check + attestation → **then** branch protection. Protecting first can lock the repo.

## Branch-protect command shape (placeholders only)

```bash
TRUST_CI_GITHUB_ADMIN_TOKEN=<temporary-admin-token> \
TRUST_CI_GITHUB_APP_ID='<app-id>' \
adaptive-trust-ci branch-protect \
  --policy "$PWD/runtime/policy.json" \
  --repository Dimkox/adaptive-grok-build-pro \
  --branch main \
  --required-reviews 0
```

Writes `required_status_checks.checks` with **exact policy-epoch name + `app_id`**. Same text from another actor does not count. Also: PR required, strict up-to-date, conversation resolution, linear history, enforce admins, no force-push/delete.

## MUST NOT

- GitHub Actions / `.github/workflows/` / Dependabot / other CI SaaS (`AGENTS.md`, roadmap #1, decisions 2026-08-16, runbook).
- Forge `adaptive-trust-ci/verified@*` or treat local receipts, delegated grants, prompts, JSON, or commit statuses as the gate (runbook rollback; `AGENTS.md`).
- Agent-held human approval private keys; generate/read/submit/simulate them (`AGENTS.md`). Human approvals: `adaptive-trust-ci approval-create` off-agent; API verifies server-mounted pubkeys.
- PR changes to deployed policy, holdout, images, PG, CI/App keys, human trust store, or branch protection.
- Direct push to protected `main`; merge without App-owned check once live.

## Current bootstrap exceptions (revoke when live)

- **decisions.md 2026-08-23 — M0 exception for M1 start:** M0 not met on this host; M1 may proceed; does **not** create the check, protect `main`, or authorize merge. Revoke when a live App-owned check exists on an exact PR SHA.
- **decisions.md 2026-08-23 — PR #2:** user-ordered rebase-merge while App check absent; `main` unprotected; **do not forge** the check or protect `main` in that slice.
- **PR #4:** named merge exception of the same class (change `20260824-user-query-да-user-query-37bf04`; rebase at `5a63d1c`); not a new `decisions.md` heading. Revoke with M0 live authority.

`mistakes.md` has **no** Trust CI bootstrap entries; grant-fingerprint and prompt-file mistakes only.

M0 Git evidence: operator-safe report (App/install IDs, check/policy/image/holdout digests, no secrets), attestation output, redacted branch-protection response, rollback/key-rotation notes.
