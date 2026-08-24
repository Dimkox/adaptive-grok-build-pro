# M0 — Live Trust Authority (implementation plan)

Base: `origin/main` `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`. Branch: `milestone/m0-live-trust-authority`. No GitHub Actions. No M1/M2–M9 on this branch.

TDD: add characterization tests before docs land; keep them green after each slice. Do not assert “main is unprotected” (that would fight M0.3).

## M0.0 — Design freeze (this slice)

- [x] Inspect live GitHub/host (no secrets).
- [x] Analysis + `scope_and_design_approval`.
- [ ] Spec `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- [ ] Plan (this file)
- [ ] Operator-safe activation-report template `engineering/runbooks/trust-ci-activation-report.md` (fields `UNKNOWN` until live)
- [ ] Invariant tests: no `.github/workflows/**`; API has no `GitHubClient`/`GitHubAppAuth`; worker has `GitHubAppAuth`; compose publishes `127.0.0.1:8080:8080`; holdout forbids Actions; spec/plan exist and contain no PEM material
- [ ] `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr`
- [ ] Draft PR from this branch; do not mark ready

**STOP:** no `compose.yaml up`, no webhook, no `branch-protect`, no PEM read.

## M0.1 — Dedicated-host listener

Requires `migration_or_external_write_approval` and a **named** dedicated CI host (not this laptop). User approved activation intent; host name is still required before this slice.

- [ ] Operator copies example env/policy/trust-store on that host; pins `name@sha256:` images and holdout digest
- [ ] `docker compose up -d postgres migrate api worker` (and runner-loader as in compose)
- [ ] `curl -fsS https://<ci-host>/health/ready` (or loopback behind TLS proxy)
- [ ] Confirm API has webhook secret + trust store and **no** App key; worker has App ID + installation ID + PEM + signing key and **no** webhook secret
- [ ] Webhook still absent; `main` still unprotected

## M0.2 — Live authority proof

- [ ] Register repo webhook `POST https://<ci>/webhooks/github`
- [ ] Disposable docs PR; job for exact head SHA; worker Check Run `adaptive-trust-ci/verified@<policy-sha12>` with `external_id=job_id`, App-owned
- [ ] Offline attestation verify
- [ ] SHA change invalidates old check; policy/holdout retitles epoch
- [ ] `trust-ci/**` → `needs_approval` → human Ed25519 requeue of the **same** Check Run
- [ ] Source-mutation fail-closed; kill switch; backup/restore/restart
- [ ] **Do not protect `main`**

## M0.3 — Bind `main`

Only after M0.2 is unambiguous.

- [ ] Temporary human admin token: `adaptive-trust-ci branch-protect` with epoch name **and** App ID
- [ ] Prove same text from another actor fails; direct push / force-push / delete / merge-without-check fail
- [ ] Disable leftover Actions workflow `340420982`
- [ ] Supersede bootstrap-exception language (M1 start, PR #2, PR #4)
- [ ] Fill activation report with IDs and digests; no secrets
- [ ] Mark PR ready; merge only through the live App-owned check

## Grants (after each last local write)

| Action | When |
| --- | --- |
| `git-push-branch` on `milestone/m0-live-trust-authority` | M0.0 draft PR |
| `external-write` `gh pr create` | M0.0 draft PR |
| Host compose / webhook / `branch-protect` / disable workflow 340420982 | M0.1–M0.3 only |
