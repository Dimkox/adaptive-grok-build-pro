# Architect ruling — continue M0.2 after the first App-owned Check Run

Route `85a17ed2e935`. Change `engineering/changes/20260824-m0-consolidate-git-and-continue-live-authority-p-85a17e`. Write owner: `general_implementer`. This agent does not compose-up, POST the webhook, push, merge, read PEM/`.env`, edit deployed policy/holdout/images/Postgres/keys, or deploy.

Prior slice (`3e6166`) already produced Check Run `97390635614` on SHA `1fc942065a124ce75659bd082519d8ebc37774e8` via untracked host-socket overlay + loopback HMAC. That is **not** M0.2 complete and **not** merge authority. Git HEAD is still that SHA; operator notes are dirty and unpushed.

## Ruling (one paragraph)

**Smallest coherent next implementation is SHA-change invalidation on PR #5, using the already-running overlay.** Commit the already-dirty operator-safe M0 notes (`engineering/runbooks/trust-ci-activation-report.md`, `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`, `decisions.md`) plus this change package on `milestone/m0-live-trust-authority`, push, then HMAC-POST `/webhooks/github` for the **new** head SHA. Prove Check Run `97390635614` remains bound to `1fc9420` and a **new** App-owned Check Run appears on the new SHA with a new `job_id`/`external_id`. Tracked `trust-ci/compose.yaml` stays unchanged. Policy/holdout retitle is **forbidden** from this PR/agent. Human Ed25519 requeue, public webhook, kill-switch drill, backup/restore, and `branch-protect` stay blocked or later. Do not claim M0.2 exit.

## Conflicts resolved

| Source | Claim | Ruling |
| --- | --- | --- |
| User this turn | Re-read git, unify, continue | **Wins** as SHA-change + git consolidate on the live overlay. Continue does **not** mean finish every M0.2 checkbox. |
| M0 spec/plan remaining M0.2 list | webhook + attestation + SHA + policy retitle + human requeue + mutation + kill switch + backup | Split. Only SHA-change (plus honest attestation 404 on `needs_approval`) is in this slice. |
| Prior architect `3e6166` | Overlay, no tracked compose, no public webhook, no branch-protect | **Stands.** Overlay residual remains accepted, not promoted. |
| `docs_researcher` (prior) | Spec still wants HTTPS webhook before first Check Run | True of **docs**. First Check Run already happened via loopback. Do not invent Cloudflare/ngrok. |
| `AGENTS.md` trust boundary | Repo cannot modify deployed policy/holdout/images/Postgres/keys; agent cannot create human approval keys | **Binding.** Policy retitle and human private-key operations are blocked. |

## Live facts (no secrets)

| Item | Value |
| --- | --- |
| Branch | `milestone/m0-live-trust-authority` @ `1fc942065a124ce75659bd082519d8ebc37774e8` (matches origin) |
| Dirty (must consolidate) | `decisions.md`, M0 plan, activation report; leftover unrelated `state.json`; untracked change packages |
| PR | #5 draft; base `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` |
| Check Run | `97390635614`, name `adaptive-trust-ci/verified@6737355947c2`, App `4694114` |
| Job | `1b63d10b-90c1-498a-97b8-7b5e0ea76aec`, `needs_approval`, conclusion `action_required` |
| `TRUST_CI_PUBLIC_BASE_URL` (activation report) | `http://127.0.0.1:18080` — **not HTTPS** |
| Public webhook | absent |
| `main` protected | false |
| Overlay | untracked `/home/pall/adaptive-trust-ci-host/compose.host-socket.yaml`; tracked compose still DinD |
| Host `:8080` | SearXNG |

Do not `git add` `trust-ci/env/*.env`, `trust-ci/runtime/**`, overlay under `trust-ci/`, PEM, or leftover unrelated change packages (`20260817-…`, `20260824-user-query-да-user-query-37bf04`, stale `9d97f8` `state.json`).

---

## 1. Four planes still separate? Overlay residual risk

**Yes. Planes remain. Overlay residual is unchanged and still accepted only as a claw-only exception.**

| Plane | Socket | Secrets | Network | Overlay effect |
| --- | --- | --- | --- | --- |
| **API** | no | webhook HMAC + trust-store **public** keys | `trust-ci`; published `127.0.0.1:18080` | Overlay does not mount sock or App RSA on `api` |
| **Worker** | **yes** (host `/var/run/docker.sock`) | App RSA path, CI Ed25519, App/install IDs | `trust-ci` + host-gateway proxy | Overlay mounts sock + bind-replaces workspace/holdout |
| **Runner** | **no** | none | `none` | Unchanged argv in `sandbox.py` (`--network none --pull never`, no sock, no token) |
| **Human keys** | n/a | **not on claw** | n/a | Bootstrap unlinked the approval private after inserting the public key |

Residual (do not “fix” this slice):

- Worker uid `10001` + writable host docker.sock is **host-root equivalent** on the same engine as SearXNG/n8n/Caddy. App PEM and CI signing key sit in that container.
- Host `socat TCP-LISTEN:1080,bind=172.17.0.1` → glider `127.0.0.1:1080` is operator residue. Do not rebind `proxy-gateway` or use `network_mode: host`.
- Loader relies on the host image store when ghcr pull is unauthorized.
- `GitWorkspace._git_env` still strips proxy (checkout residual). P0 checkout already reached `needs_approval`, so do not patch it pre-emptively.
- Restricted Docker API proxy from the hardening plan is **unbuilt**. Do not invent it.

Invariants the implementer must not break: no sock on `api`/`postgres`; no sock in runner argv; tracked `trust-ci/compose.yaml` still forbids `/var/run/docker.sock` in tests/smoke; overlay stays outside the git tree (evidence copy under the prior change package is documentation only).

---

## 2. SHA-change invalidation — this is the right next proof

**Yes.** GitHub Check Runs are bound to `head_sha`. Durable jobs are idempotent on `(repository, pr_number, head_sha, pipeline, policy_digest)`. A new commit on PR #5 is the smallest live proof that does not cross the trust boundary.

### What the code already does

On `synchronize` HMAC POST with a **new** SHA (`store.enqueue` / `PostgresStore.enqueue`):

1. Active jobs for the same repo/PR with a **different** `head_sha` become `cancelled` / `failure_code=superseded-head`.
2. A **new** `job_id` is created for the new SHA.
3. `GitHubClient.ensure_check_run` lists check-runs **on that SHA** and reuses only a run whose `external_id` equals the new `job_id`. Check Run `97390635614` cannot be found on the new SHA, so the worker **creates** a new Check Run.

The old GitHub Check Run is **not** unpublished. That is correct: it must remain visible on `1fc9420` and **absent** from the new SHA’s check-run list. Worker does not PATCH superseded jobs to GitHub `cancelled`; do not invent that PATCH.

### Exact next sequence

1. Last local writes: operator-safe docs already dirty + this change package. `decisions.md` is `protected_paths` **and** `control_plane_paths` **and** Trust CI `governance` glob — structured Edit/Write + exact protected-path grant; no shell `sed`.
2. `python3 scripts/grok_verify.py --mode pr` after product-tree edits.
3. Exact `git-push-branch` grant for `milestone/m0-live-trust-authority`. Push. Re-fetch `gh api repos/Dimkox/adaptive-grok-build-pro/pulls/5` for the **new** `head.sha` immediately before POST.
4. `/tmp` HMAC POST (same contract as prior slice): `POST http://127.0.0.1:18080/webhooks/github`, event `pull_request`, action `synchronize`, PR #5, new SHA, base still `48cb973…`. Print only HTTP status / `job_id` / `created` / `status`. Never print secret or signature.
5. Proof (operator-safe):

```text
gh api repos/Dimkox/adaptive-grok-build-pro/commits/1fc942065a124ce75659bd082519d8ebc37774e8/check-runs
gh api repos/Dimkox/adaptive-grok-build-pro/commits/<NEW-HEAD-SHA>/check-runs
curl -fsS http://127.0.0.1:18080/health/ready
```

### Pass / fail

| Must hold | Must not happen |
| --- | --- |
| Old SHA still lists Check Run `97390635614`, App `4694114`, `external_id=1b63d10b-…` | Treating `97390635614` as satisfying the new SHA |
| New SHA lists a **different** Check Run id, same name `adaptive-trust-ci/verified@6737355947c2`, App `4694114`, `external_id` = **new** `job_id` | PATCH old check to `success`; user-token check-run create; GitHub Actions |
| New webhook `created: true` (or honest `created: false` only if that exact new SHA was already posted) | Replay of the **old** SHA (returns same cancelled/old job; not a new proof) |
| New job likely `needs_approval` / `action_required` because `decisions.md` remains in the diff | Forging human approval to chase `success` |

Replay of the old SHA after supersede: `ON CONFLICT (idempotency_key) DO NOTHING` returns the existing row (`created: false`); it does **not** resurrect a cancelled job. Do not use that as the new proof.

This proof is **not** M0.2 complete. It is the next bounded live characterization of exact-SHA authority.

---

## 3. Offline attestation — verify without secrets in chat

CLI (from `trust-ci/README.md` and `cli.py`):

```bash
adaptive-trust-ci attestation-verify \
  --attestation <envelope.json> \
  --public-key runtime/trust-ci-signing-key.pub.pem
```

**Public key location (documented, not opened here):** `trust-ci/runtime/trust-ci-signing-key.pub.pem`, produced by `adaptive-trust-ci keygen --private runtime/trust-ci-signing-key.pem --public runtime/trust-ci-signing-key.pub.pem`. README: “Publish the public key with release documentation for offline attestation verification.” The **private** sibling `.pem` is worker-only — never read, cat, or paste. Do not confuse this with GitHub App RSA or human approval keys.

Fetch path (rollout §6): `GET /attestations/<job_id>` with the API read bearer. **Do not print the token.** Envelope bytes may be written to a tmp file for `attestation-verify`.

### Expected failure on the current (and likely next) job

`JobRunner.process` returns at `needs_approval` **before** `sign_attestation`. `GET /attestations/{job_id}` returns **404** `attestation not found` while status is `needs_approval` / Check Run `action_required`. Job `1b63d10b-…` is in that state. A new SHA that still touches `decisions.md` will be the same.

**Honest result this slice:** record `Attestation verified offline = UNKNOWN` (or “404 expected: no envelope until a job finishes holdout+commands”). Do **not** mint a fake envelope. Do **not** treat 404 as a broken CLI. A green `attestation-verify` is **blocked** until either (a) a diff outside `approval_rules` reaches `passed`/`failed`, or (b) a human Ed25519 requeue of the same job actually runs commands — both out of this slice.

`/jobs/{job_id}` may still show `required_scopes` / `missing_scopes` without an attestation. That is enough observability.

---

## 4. Policy / holdout retitle — FORBIDDEN from PR/agent (blocked)

Deployed `runtime/policy.json` and the holdout bundle live **outside** the pull-request trust domain (`AGENTS.md`, spec trust boundary, `trust-ci/README.md`). API/worker load policy from the **server mount**, not from the PR tree. Editing `trust-ci/config/policy.example.json` or any repo file **does not** change `policy.digest` or the required check name `adaptive-trust-ci/verified@6737355947c2`.

Changing deployed policy or holdout bytes:

- changes the policy digest and **retitles** the required check;
- invalidates old jobs and approvals;
- is a host-owned operator action on images/policy/holdout — **not** a PR, **not** an agent write.

**Record as blocked.** Do not `docker cp` policy, do not edit host `runtime/policy.json`, do not rebuild/retarget images, do not alter holdout digest `b78d17006e270cec373aa130d7b0d11de357ffa236297b41075234e6ad7d5db8`. Spec M0.2 item “policy/holdout retitles epoch” waits for an explicit operator session **after** SHA-change is proven.

If the worker sees `job.policy_digest != deployed digest`, it fails closed with `policy-digest-mismatch` and still publishes an App-owned check. That path is **not** the retitle drill.

---

## 5. Human Ed25519 requeue — agent must not generate/read/submit the private key

`needs_approval` for PR #5 is **already proven** (`governance` glob includes `decisions.md` and `trust-ci/**`). Requeue of the **same** Check Run is `POST /approvals` → `requeue_for_approval` (status `needs_approval` → `queued`, same `job_id`) → worker `ensure_check_run` PATCHes the existing run by `external_id`.

**Agent forbidden:** `keygen` for a human approval key; read/copy/submit any approval private key; `approval-create` / `approval-submit`; simulate signatures; insert keys into `runtime/trust-store.json`.

**Operator-safe prep allowed (no private material):**

- Record from `/jobs/{job_id}` (redact tails/token): repository, PR, `base_sha`, `head_sha`, `policy_digest`, `required_scopes` / `missing_scopes`, `check_run_id`.
- Print the **command template** from `trust-ci/README.md` with placeholders only:

```text
adaptive-trust-ci approval-create \
  --private-key <HUMAN-MACHINE-ONLY> \
  --policy <downloaded-server-policy.json> \
  --actor <trust-store-actor> \
  --repository Dimkox/adaptive-grok-build-pro \
  --pr-number 5 \
  --base-sha <40-hex> \
  --head-sha <40-hex> \
  --scope governance \
  --reason '<human review of exact diff>' \
  --ttl 900 \
  --output approval.json

adaptive-trust-ci approval-submit --approval approval.json --url http://127.0.0.1:18080
```

(`approval-submit --url` may be loopback HTTP; public HTTPS is not required for a human on `claw`. Still do not run it from the agent.)

**Blocked until a human who still holds a matching private key acts off-host.** `decisions.md` records that bootstrap generated a pair, inserted **only** the public key into the server trust-store, then **unlinked** the private file on `claw`. The live public key therefore has **no** private on this host. The agent must not regenerate that pair. Installing a new human public `key_id` into deployed `runtime/trust-store.json` is a **host-owned trust-store write** (outside the PR domain) and is **not** this slice.

---

## 6. Public webhook — still blocked without HTTPS

Activation report: `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080`. Plan: “Public GitHub webhook still absent (no public HTTPS).” Spec: public URL **must** be HTTPS; GitHub will not deliver to loopback.

Repo grep of product/host docs for `ngrok` / `cloudflare` / `cloudflared` / `tailscale`: **no matches**. Do **not** invent a tunnel or steal n8n/Caddy `:443`. `trust-ci/env/common.env.example` uses `https://ci.example.com` as a **placeholder**, not a live name.

`GET /repos/Dimkox/adaptive-grok-build-pro/hooks` stays empty. Loopback HMAC remains a characterization of `/webhooks/github`, not webhook registration. Do not `gh api` create a hook at `http://127.0.0.1:18080`.

---

## 7. Kill switch / backup-restore — later, not this slice

They remain **M0.2 exit items** in the spec/plan, but they are **not** the next implementation. They do not prove SHA binding, they can 503 the live API or touch PostgreSQL, and SHA-change is still missing.

Documented commands / runbooks (do not execute now):

| Drill | Where named |
| --- | --- |
| Kill switch | `trust-ci/README.md` “Emergency stop”; `engineering/runbooks/trust-ci-rollout.md` “Emergency stop”; CLI `adaptive-trust-ci kill-switch on\|status\|off`; default file `/run/adaptive-trust-ci/STOP` |
| Backup | `trust-ci/README.md` “Backup and recovery”; rollout “Database backup”; CLI `backup-create`, `backup-verify`, `backup-prune`; systemd `trust-ci/systemd/adaptive-trust-ci-backup.service` |
| Restore drill | `QUICKSTART.md`; CLI `restore-drill --confirm-disposable`; script `trust-ci/scripts/restore-drill.sh` |

Kill switch while proving SHA-change would 503 the HMAC POST (`test_api.py`). Restore-drill requires an **explicitly disposable** database URL — never the live `trust-ci-postgres` volume. Source-mutation fail-closed is also later (holdout/runner fixture).

Activation report fields `Kill switch drill` and `Backup/restore/restart drill` stay `UNKNOWN`.

---

## 8. Smallest coherent next implementation

**In scope (write owner):**

1. Keep tracked `trust-ci/compose.yaml` **unchanged**. Do not start `docker-engine`. Do not rewrite tests/smoke/systemd.
2. Commit and push only M0-related operator-safe tree: dirty activation report, M0 plan, `decisions.md` (protected-path grant), this change package, optionally the prior `3e6166` evidence as workflow paper. Then HMAC-POST the **new** PR #5 SHA.
3. Record new Check Run id / `external_id` / SHA in the activation report **without secrets**. Keep `TRUST_CI_PUBLIC_BASE_URL=http://127.0.0.1:18080` and `main protected = false`.
4. Probe `GET /attestations/<job_id>`: expect 404 while `needs_approval`; document CLI + public-key path; do not claim offline verify pass.
5. If product files change: `python3 scripts/grok_verify.py --mode pr` and route reviews. Overlay-only / gitignored env: skip verify (no-op tree) — but this slice **does** touch the product tree.

**Out of scope / forbidden:**

- Edit `trust-ci/compose.yaml` or promote host-socket to the product default
- Policy/holdout/image/Postgres/key/trust-store writes on the host
- Human approval private key operations
- Public webhook, Cloudflare/ngrok, Caddy Trust CI site, `TRUST_CI_PUBLIC_BASE_URL` change
- `adaptive-trust-ci branch-protect`, protect `main`, disable Actions workflow `340420982`
- Kill-switch on/off, backup-create, restore-drill against live data
- Merge / ready PR #5 / push to `main` / forge `adaptive-trust-ci/verified@*`
- PEM / `.env` / JWT / webhook secret / read token print
- M1–M9, `factory/`, VERSION/tag/release
- `GitWorkspace._git_env` proxy patch unless the **new** job dies at checkout after P0-equivalent publication already holds

### Grants (mint after the last local write, exact, no wildcard)

```text
git-push-branch  resource: milestone/m0-live-trust-authority
protected-path-write  resource: decisions.md   (only if that file is edited)
```

Loopback HMAC POST is not an external GitHub write. Compose-up is already done; re-mint compose grants **only** if worker/loader must be restarted. No webhook-create, no branch-protect, no production mutation.

### Rollback

Same as prior slice: stop `worker`/`runner-loader`; leave postgres+api; keep overlay file unless aborting the exception; never `compose down -v`; never PATCH checks to success. A published Check Run cannot be unpublished. `main` is unprotected, so a new SHA cannot lock the repository.

### Acceptance (this slice only)

- Four planes unchanged; tracked compose still DinD; overlay untracked
- New head SHA ≠ `1fc9420`; Check Run `97390635614` still only on the old SHA
- New App-owned Check Run on the new SHA, name `@6737355947c2`, `app.id=4694114`, new `external_id`
- Attestation: 404 documented if `needs_approval`; no fake envelope
- Policy digest still `6737355947c21eb561073cb506ebc5698afd170088a34f8eaace50007c57d1a5`
- Hooks empty; `main` unprotected; no secrets in git/chat/activation report

**Stop** after that proof. M0.2 remainder and M0.3 wait.
