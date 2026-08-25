# M0 — Live Trust Authority (implementation plan)

Base: `origin/main` `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`. Branch: `milestone/m0-live-trust-authority`. No GitHub Actions. No M1/M2–M9 on this branch.

TDD: add characterization tests before docs land; keep them green after each slice. Do not assert “main is unprotected” (that would fight M0.3).

## M0.0 — Design freeze (this slice)

- [x] Inspect live GitHub/host (no secrets).
- [x] Analysis + `scope_and_design_approval`.
- [x] Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- [x] Plan (this file)
- [x] Operator-safe activation-report template `engineering/runbooks/trust-ci-activation-report.md` (live Check Run ids filled; leftover fields may stay `UNKNOWN`)
- [x] Invariant tests: no `.github/workflows/**`; API has no `GitHubClient`/`GitHubAppAuth`; worker has `GitHubAppAuth`; compose publishes `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080` with project `name: adaptive-trust-ci` (not `127.0.0.1:8080:8080`); holdout forbids Actions; spec/plan exist and contain no PEM material
- [x] `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr`
- [x] Draft PR from this branch; do not mark ready

**STOP (historical M0.0 gate):** no `compose.yaml up`, no webhook, no `branch-protect`, no PEM read. Later slices already brought up the listener and published a local-HMAC Check Run; those remain host-local and incomplete for M0.2.

## M0.1 — Dedicated-host listener

Requires `migration_or_external_write_approval`. The named host **is `claw`**. `postgres` + `migrate` + `api` remain healthy on `127.0.0.1:18080`. Nested rootless DinD previously failed (`rootlesskit` `fork/exec /proc/self/exe: operation not permitted`); that is historical. The worker now runs via an untracked host-socket overlay (`runner-loader` completed, `docker-engine` stopped unused). Tracked compose still documents isolated DinD. Gitignored worker App ID `4694114` and installation ID `156003193` are set (PEM unread). Public GitHub webhook is still absent (M0.2).

- [x] Operator copies example env/policy/trust-store on that host; pins `name@sha256:` images and holdout digest
- [x] Worker running on `claw` via untracked host-socket overlay (`runner-loader` exit 0, `docker-engine` stopped unused). Tracked compose still documents isolated DinD.
- [x] `curl -fsS http://127.0.0.1:18080/health/ready` returned 200 (`status=ready`); TLS proxy not this slice
- [x] Confirm API has webhook secret + trust store and **no** App key; worker env IDs set; worker container running
- [x] Public GitHub webhook still absent; `main` still unprotected

## M0.2 — Live authority proof (closed 2026-08-24)

User ordered M0.2 closed after live GitHub App webhook + App-owned Check Run. Residual items stay **not done** and are not merge authority.

- [x] Register GitHub App webhook `POST https://claw.taild9f611.ts.net/webhooks/github` — GitHub `pull_request`/`synchronize` **200** on SHA `9d56734`; Funnel + HMAC.
- [x] Disposable docs PR; job for exact head SHA; worker Check Run `adaptive-trust-ci/verified@<policy-sha12>` with `external_id=job_id`, App-owned — GitHub webhook SHA `9d56734d9050fb3cb2543565084bcb83ded5c73b` Check Run `97524725228`; later SHA `56f5462e78c7ebc0ab7e69fbffd5c1371ff7af78` Check Run `97527445754` App `4694114`. Earlier **local HMAC**: `97390635614` on `1fc9420`. `conclusion=action_required` (`needs_approval`).
- [ ] Offline attestation verify — **not done** (`needs_approval`; no human private key on claw)
- [x] SHA change invalidates old check — proven (`97390635614` on `1fc9420` vs `97406973020` on `ce03c87` vs GitHub webhook runs). Policy/holdout retitle **not done** (outside the PR trust domain).
- [ ] `trust-ci/**` → `needs_approval` → human Ed25519 requeue of the **same** Check Run — **not done** (no human approval private key)
- [ ] Source-mutation fail-closed — **not done** (runner-loader exited; no live runner)
- [x] Backup/restore/restart host-local drill **2026-08-24 pass** (`backup-create`, `backup-verify`, restore-drill `--confirm-disposable` on throwaway tmpfs, `compose restart postgres` without `-v`). Kill switch **2026-08-24 pass**.
- [x] **Do not protect `main`** in M0.2 (M0.3 bind follows)

## M0.3 — Bind `main`

Only after M0.2 is unambiguous. Live 2026-08-24 proofs (do not re-PUT, do not re-disable, do not re-POST statuses): GET `branches/main/protection` required check `adaptive-trust-ci/verified@6737355947c2` `app_id` **4694114**, `strict` true, `enforce_admins` true, `allow_force_pushes` false, `allow_deletions` false, `required_linear_history` true; leftover workflow `340420982` `disabled_manually`; user POST Checks 403 (must authenticate via a GitHub App); user POST statuses same context `success` id **52802341946** creator Dimkox; App Check Run **97529209576** `action_required` `app.id=4694114` `external_id` `53870ce3-951c-4247-afe9-88969be5dc98`; PR #5 draft `mergeable_state=blocked` head `ac01326a4a3fde1d0630e621da51ef67379da191`. Direct-push/force-push/delete refusals are recorded via those protection flags plus `mergeable_state=blocked`; no live push to `main` was issued.

- [x] Temporary human admin token: `adaptive-trust-ci branch-protect` with epoch name **and** App ID
- [x] Prove same text from another actor fails; direct push / force-push / delete / merge-without-check fail
- [x] Disable leftover Actions workflow `340420982`
- [x] Supersede bootstrap-exception language (M1 start, PR #2, PR #4)
- [x] Fill activation report with IDs and digests; no secrets
- [ ] Mark PR ready; merge only through the live App-owned check

## Grants (after each last local write)

| Action | When |
| --- | --- |
| `git-push-branch` on `milestone/m0-live-trust-authority` | M0.0 draft PR |
| `external-write` `gh pr create` | M0.0 draft PR |
| Host compose / webhook / `branch-protect` / disable workflow 340420982 | M0.1–M0.3 only |
