# task_analyst — consolidate git, continue M0.2 locally (route 85a17ed2e935)

**Verdict:** this turn is **git unification of already-proven live facts**, plus **one host-local M0.2 drill**. It is not M0.2 complete and not M0.3. Write owner: `general_implementer`. This agent does not implement, push, merge, read PEM, or deploy.

Skills: `/adaptive-delivery`, `feature-workflow`. Allowed agents only. Read-only.

User text (verbatim): «давай перечитывай гит своди все воедино и продолжай»

## 1. Outcome the user asked for in this turn

Make **git tell one story** that matches live `claw` + GitHub, then **continue the next M0.2 proof that does not need public HTTPS or a human approval private key**.

Today the stories disagree:

| Plane | State |
| --- | --- |
| `HEAD` / `origin/milestone/m0-live-trust-authority` | `1fc942065a124ce75659bd082519d8ebc37774e8` — last commit still says DinD blocked, worker not running |
| Working tree | dirty M0 plan, activation report, `decisions.md` already record overlay + Check Run |
| Draft PR **#5** body | stale: “Worker is not running.” `draft=true`, `mergeable_state=unstable`, base `origin/main` `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| GitHub Check Runs on that SHA | `adaptive-trust-ci/verified@6737355947c2` id `97390635614`, `conclusion=action_required`; plus GitGuardian success (not authority) |
| Leftover dirty/untracked packages | `9d97f8/state.json` (v2.0.12 paperwork), `37bf04` (PR #4 merge), `33e0c2` (2.0.10) — not this branch |

**Observable result of this slice:** after one explicit commit on `milestone/m0-live-trust-authority`, `git show HEAD` contains the operator-safe Check Run facts, M0.1 worker-running via overlay, and one additional M0.2 checkbox (kill switch) filled without secrets. GitHub may still show the old SHA until a later named push.

This is **not** “сводим всё в релиз, коммитим, пушим мерджим” (`9d97f8`). That earlier order named commit, push, and merge. This order names re-read + unify + continue.

## 2. Acceptance criteria (observable)

**P0 — git matches live M0.1 / M0.2-partial**

1. **Given** dirty M0 docs vs HEAD `1fc9420`, **when** the implementer stages an **explicit path list** (never `git add -A`) and commits on `milestone/m0-live-trust-authority`, **then** HEAD contains:
   - `decisions.md` host-socket overlay + Check Run `97390635614` / App `4694114` / `action_required`
   - `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` M0.1 worker-running via overlay; M0.2 Check Run marked **partial / local HMAC / not complete**; webhook still unchecked
   - `engineering/runbooks/trust-ci-activation-report.md` PR **5**, SHA `1fc942065a124ce75659bd082519d8ebc37774e8`, Check Run id `97390635614`, `external_id` `1b63d10b-90c1-498a-97b8-7b5e0ea76aec`
   - change packages `…-3e6166/` (overlay implementation evidence) and `…-85a17e/` (this slice)
2. **Given** leftover paperwork, **then** these stay **unstaged**: `engineering/changes/20260823-user-query-сводим-всё-в-релиз-…-9d97f8/state.json`, `…-37bf04/`, `…-33e0c2/`.
3. **Given** the commit, **then** `python3 -m unittest trust-ci.tests.test_m0_invariants` and `python3 scripts/grok_verify.py --mode pr` pass. Characterization: report Check Run id is not `UNKNOWN`; plan still says local HMAC is not a registered webhook; spec/plan/report contain no `BEGIN RSA PRIVATE KEY` / PEM material.
4. **Given** inspect of git / chat / report, **then** no PEM, JWT, webhook secret, installation token, or human approval private key appears.

**P1 — continue: kill-switch drill (same slice, before the commit)**

5. **Given** API ready on `127.0.0.1:18080` and compose project `adaptive-trust-ci` still up, **when** `adaptive-trust-ci kill-switch on`, **then** new webhook/approvals/claims are blocked (`503` / metrics `adaptive_trust_ci_kill_switch 1`). **When** `kill-switch off`, **then** `/health/ready` is 200 and kill-switch metric is 0. Do not leave `STOP` in place. Do not `compose down -v`.
6. Activation report field `Kill switch drill` becomes a dated pass (no secrets), not `UNKNOWN`.

**P2 — cheap honest probe (same activation-report edit)**

7. `GET http://127.0.0.1:18080/attestations/1b63d10b-90c1-498a-97b8-7b5e0ea76aec` (Bearer read token in env, never printed). Expected **404** because the job is `needs_approval` and did not sign. Record `Attestation verified offline` as `N/A (job needs_approval; GET 404)` — not a forged pass.

Non-criteria: `GET .../hooks` stays empty; `GET .../branches/main/protection` stays 404; PR #5 stays draft; remote SHA may remain `1fc9420`.

Skip-no-op does **not** apply: `decisions.md`, the M0 plan, and the activation report are product/operator docs that already diverged from HEAD. After those files are in the commit, run verify + `code_review` + `test_review`. Do not skip the wave.

## 3. In scope / out of scope for THIS slice (not all of M0)

### In scope

- Re-read git (already done here): branch, origin, PR #5, Check Run, dirty vs HEAD.
- Explicit commit of the three dirty M0 docs + `3e6166` evidence (including the overlay **copy** under `evidence/compose.host-socket.yaml`) + this `85a17e` package.
- Optional ≤3-sentence `decisions.md` note only if the kill-switch drill is new; `decisions.md` is `protected_paths` **and** `control_plane_paths` — further edits need a fresh `protected-path-write` grant for that exact path. Plan and activation report are **not** in `protected_paths`.
- Host-local kill-switch on/off. Honest attestation 404.
- Characterization extension of `trust-ci/tests/test_m0_invariants.py` (protected `trust-ci/**` — grant if the test file is edited).
- `python3 scripts/grok_verify.py --mode pr` and route reviews after the last local write.

### Out of scope this slice

- Public HTTPS, Cloudflare/Caddy, `TRUST_CI_PUBLIC_BASE_URL` change, GitHub webhook registration.
- `git push` / `git-push-branch` (see §6).
- `gh pr edit` / mark ready / merge PR #5.
- Human Ed25519 `approval-create` / requeue of Check Run `97390635614`.
- SHA-change invalidation on GitHub (needs a new pushed SHA).
- Policy/holdout retitle.
- Live source-mutation job (runner never reached; job stopped at `needs_approval`).
- Backup/restore/restart drill (threatens named volume if mis-run; next slice).
- Docs-only PR chasing `conclusion=success`.
- Tracked `trust-ci/compose.yaml` host-socket (tests/smoke forbid `/var/run/docker.sock`).
- M0.3, M1–M9, VERSION/tag/release, README graph, `factory/`.

## 4. Which M0.2 items can proceed without public HTTPS and without generating/reading human approval private keys

Plan M0.2 checklist vs this host:

| M0.2 item | This slice | Why |
| --- | --- | --- |
| Register `POST https://<ci>/webhooks/github` | **No** | No public HTTPS. Loopback HMAC is not a registered webhook. |
| Disposable PR + App-owned Check Run `external_id=job_id` | **Already partial** | PR #5 SHA `1fc9420`, Check Run `97390635614`, App `4694114`, job `1b63d10b-…`, via **local HMAC**. Not M0.2 complete. Do not re-POST unless SHA changes. |
| Offline attestation verify | **Probe only** | `needs_approval` jobs do not store an envelope. GET 404 is the honest result. `attestation-verify` uses the **CI public** key only if a file exists; do not read the worker signing private key. |
| SHA change invalidates old check; policy/holdout retitle | **No** | New SHA must exist on GitHub (push). Policy/holdout bytes are deployed trust boundary — do not edit them here. |
| `trust-ci/**` → `needs_approval` → human Ed25519 requeue of the **same** Check Run | **Half done** | `needs_approval` / `action_required` is already proven. Requeue **cannot** proceed: agents must not generate, read, or simulate the human approval private key. |
| Source-mutation fail-closed | **No live** | Unit/holdout already exist. Live fail-closed needs a job that reaches the runner. Blocked until a docs-only PR (push) or human requeue. |
| Kill switch | **Yes — this slice** | Local `STOP` file. No GitHub, no keys. Restore `off`. |
| Backup/restore/restart | **Yes later, not this slice** | Scripts exist (`trust-ci/scripts/restore-drill.sh`, postgres restart drill). Requires disposable restore URL and a compose grant. Easy to `down -v` the live volume. Queue after git is clean. |
| Do not protect `main` | Constraint | Keep unprotected. |

Public CI signing **public** key and GitHub Check Run metadata are readable. Human approval **private** keys and App PEM are not.

## 5. Whether committing dirty M0 docs is in-scope «своди все воедино»

**Yes.** That is the named unification.

Dirty **in**:

- `decisions.md` (new overlay + Check Run entry)
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` (M0.1 worker running; M0.2 partial)
- `engineering/runbooks/trust-ci-activation-report.md` (PR #5 / SHA / Check Run / job id)
- `engineering/changes/20260824-the-user-sent-a-message-while-you-were-working-u-3e6166/` (implementation + overlay copy)
- `engineering/changes/20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e/` (this package)

Dirty **out** (leftover paperwork, skip-no-op if they were the only delta):

- `engineering/changes/20260823-user-query-сводим-всё-в-релиз-коммитим-пушим-мер-9d97f8/state.json` (`reviewing` → `released` for v2.0.12 — wrong branch)
- untracked `…-37bf04/` (PR #4 merge)
- untracked `…-33e0c2/` (2.0.10 cleanup)

Do not commit gitignored `trust-ci/env/*.env`, `trust-ci/runtime/*`, host overlay `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml`, or PEM files. The evidence **copy** of the overlay under `3e6166/evidence/` is documentation, not the live compose file.

`build/stage_m02.py` stages the wrong change (`421a1d`). Do not run it. Explicit `git add -- <paths>`.

## 6. Whether `git-push-branch` on already-open draft PR #5 is delegated by this user message

**No — weak. Do not mint or use a push grant this slice.**

Quoted user text: «давай перечитывай гит своди все воедино и продолжай»

| Signal | Reading |
| --- | --- |
| Named operations | re-read git, unify, continue. No «пуш», no `git push`, no origin, no PR #5, no `git-push-branch`. |
| `AGENTS.md` | “A user may **explicitly** delegate named operational actions, including branch push.” “An agent may invoke `grok_approve.py` only when the user has explicitly delegated the **named** operation.” Wildcard forbidden. |
| Precedent `9d97f8` | «сводим всё в релиз, коммитим, пушим мерджим мое прямое указание» — that message **did** name push and merge. This one does not. |
| Standing 2026-08-17 “always push main and release” | Product **main** releases. Direct push to `main` is now prohibited. Does not authorize this feature branch. |
| M0 plan grant table | `git-push-branch` on this branch was for **M0.0 draft PR**. PR #5 already exists. Table is not a standing push token. |
| Current `approvals.json` | **Zero** `git-push-branch` grants. Live rows are `external-write` compose/socat for route `3e61666b8de2` / change `…-3e6166` / TTL ~10:14–10:20Z. Wrong route, change, fingerprint. **Do not reuse.** |

Local commit does not require `git-push-branch`. Pushing would move PR #5 off the SHA the Check Run is bound to (`1fc9420`); that is the M0.2 “SHA change invalidates old check” drill and needs an **explicit** later order plus a grant minted **after** the new HEAD.

`gh pr edit` (stale body: “Worker is not running”) is `external-write`. Also **not** delegated. Leave the GitHub PR text until a named push/edit grant exists.

## 7. Human gates

**Route `human_gates`: `[]`.** No `scope_and_design_approval` stop. Implementer may proceed after this analysis + architect ruling.

`AGENTS.md` named gates that still apply regardless of the empty route list:

| Gate | This slice |
| --- | --- |
| Direct push to protected/shared `main` | Forbidden. Branch only, and not even that without a named push grant. |
| Merge | Forbidden. PR #5 stays draft. Local receipts / grants never satisfy `adaptive-trust-ci/verified@<policy-sha12>`. |
| Webhook registration | External GitHub write; needs public HTTPS. Not this slice. |
| `branch-protect` | M0.3 only; **temporary human admin token**; App must not gain Administration. |
| Human security approval private keys | Never generate, read, request, submit, or simulate. No `approval-create`. |
| PEM / `.env` / CI signing private key / GitHub App key | Never read. Filename gitignored; unread. |
| GitHub Actions / `.github/workflows/**` | Forbidden. Do not disable leftover workflow `340420982` (M0.3). |
| Forge `adaptive-trust-ci/verified@*` | Forbidden. Do not PATCH Check Run `97390635614` to `success`. |

Protected-path: further `decisions.md` or `trust-ci/tests/test_m0_invariants.py` edits need an exact `protected-path-write` grant on this route/change/HEAD/fingerprint. First mutation consumes it (`mistakes.md` 2026-08-23). Batch or re-mint.

Kill-switch / `docker compose` on project `adaptive-trust-ci`: mint a **new** `external-write` grant for **this** `change_id` `20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e` and route `85a17ed2e935` only if the implementer actually runs compose/kill-switch. User «продолжай» plus standing compose-up on `claw` is enough to mint that **narrow** grant; it is **not** enough to mint `git-push-branch`. Resource must be exact (compose project or kill-switch CLI), not `*`.

## 8. Non-goals

- Protect `main`.
- Merge PR #5 or mark it ready.
- Forge or complete Check Run `97390635614` from another actor / user token / GitHub Actions.
- Add `.github/workflows/**`, Dependabot, or any Actions dependency.
- Start M1–M9 or `factory/`.
- Read or commit PEM, JWT, webhook secret, admin token, or human approval private keys.
- `git add -A`, force-push, tag, GitHub Release, VERSION bump.
- Publish Trust CI on host `:8080`. Steal n8n/Caddy/SearXNG/app-stack resources.
- `compose down -v`. Change deployed policy/holdout/images.
- Treat GitGuardian, local receipts, or delegated grants as merge authority.

## Recommended ONE vertical slice

**Name:** Git matches the live App-owned Check Run, then prove kill-switch on loopback.

**Why this one:** the user asked to re-read git and unify first. Continuing live M0.2 on a dirty tree is what split HEAD from reality. Kill switch is the only remaining M0.2 checkbox that is host-local, does not need HTTPS, and does not need human keys. Backup/SHA-change/docs-only-success are larger next slices.

**Sequence (single write owner, one commit):**

1. Read-only attestation GET → record 404 in the activation report.
2. Mint exact `external-write` for kill-switch/compose on **this** fingerprint if the hook requires it. Run on → prove block → off → `/health/ready` 200.
3. Update activation report (`Kill switch drill`, attestation field). Edit plan checkbox for kill switch only if the drill actually passed. Do not claim M0.2 complete.
4. If adding a `decisions.md` sentence or `test_m0_invariants` characterization: mint `protected-path-write` **after** the report edit or batch both against the then-current fingerprint.
5. `git add --` the in-scope paths. Commit on `milestone/m0-live-trust-authority`. Do not push.
6. `python3 scripts/grok_verify.py --mode pr`. Route `code_reviewer` + `test_reviewer`. Bind receipts after the last file write (`mistakes.md` 2026-08-14).

**Empty / error stops (do not improvise):**

| Signal | Action |
| --- | --- |
| Kill switch cannot be turned off | Stop. Restore `off` is P0. Do not commit a red API. |
| `/health/ready` not 200 after off | Stop. Do not `compose down -v`. |
| Hook denies `trust-ci` shell mutation | Structured Edit/Write or CLI via grant; no `sed`/redirect. |
| Temptation to push so PR #5 body/SHA match | Stop. Push is **not** delegated. |
| Temptation to requeue `needs_approval` | Stop. Human key off-host. |
| Attestation GET 200 with a blob | Verify offline with **public** key only; still do not push. |

**Rollback:** `git restore --staged` / `git reset` of an unpushed commit on this branch; `kill-switch off`; leave postgres+api+worker; do not PATCH the Check Run.

**Success metric:** `git log -1` on this branch describes Check Run `97390635614` honestly, kill-switch drill is recorded, verify is green, remote and `main` unchanged.

**Next slice (not this one):** named `git-push-branch` + optional `gh pr edit` so PR #5 SHA/body match; then SHA-invalidation Check Run; then backup/restore/restart; public HTTPS webhook still blocked; human requeue still human.
