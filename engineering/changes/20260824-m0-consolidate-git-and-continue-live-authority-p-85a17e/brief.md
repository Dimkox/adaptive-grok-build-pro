# M0 consolidate git and continue live authority proof

Change ID: `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e`
Route: `85a17ed2e935`
Created: 2026-08-24T10:11:49+00:00
Risk: low
Complexity: standard
Domains: generic
Write owner: `general_implementer`

## Problem

User: «давай перечитывай гит своди все воедино и продолжай».

HEAD `1fc9420` still says DinD blocked / worker not running. Dirty working tree, live `claw`, and GitHub already disagree: worker is up via an untracked host-socket overlay; draft PR #5 has App-owned Check Run `97390635614` (`action_required`) via loopback HMAC. M0.2 is not complete (no public HTTPS webhook).

## Outcome

Git on `milestone/m0-live-trust-authority` tells one operator-safe story that matches live claw + GitHub. One host-local M0.2 drill (kill-switch on/off) is proven and recorded. Attestation GET for the `needs_approval` job is recorded as 404, not a forged pass. Remote and `main` stay unchanged.

## Scope

### In scope

- Commit explicit paths: dirty M0 plan, activation report, `decisions.md`, change packages `…-3e6166/` and `…-85a17e/`
- Check off M0.0 false-negative plan boxes; annotate spec live-gap as freeze snapshot
- Kill-switch on → prove block → off → `/health/ready` 200
- Honest `GET /attestations/<job_id>` 404
- Characterization in `trust-ci/tests/test_m0_invariants.py`
- `python3 scripts/grok_verify.py --mode pr`

### Out of scope

- `git push` / `git-push-branch` / `gh pr edit` / merge / mark ready
- Public HTTPS webhook, Cloudflare/ngrok, `TRUST_CI_PUBLIC_BASE_URL` change
- SHA-change invalidation on GitHub (needs a pushed SHA)
- Policy/holdout retitle, human Ed25519 requeue, PEM read
- Backup/restore against live volume; `compose down -v`
- Tracked `trust-ci/compose.yaml` overlay; protect `main`; M1–M9; VERSION/tag/release
- Leftover packages `9d97f8`, `37bf04`, `33e0c2`

## Constraints

- Backward compatibility: tracked compose still documents isolated DinD
- Secrets: never print PEM, JWT, webhook secret, read bearer, installation token, human private keys
- Operational: leave postgres+api+worker up; restore kill-switch **off**; host `:8080` stays SearXNG
- Four planes stay separate; overlay stays untracked host exception

## Controller ruling (analysis conflict)

Architect wanted SHA-change + push as the next M0.2 proof. Task analyst: this user text does not name push (`AGENTS.md` requires an explicit named operation). **Ruling:** task_analyst wins on push. Unify git locally; continue with kill-switch + attestation 404. SHA-change is the next slice after an explicit push order.
