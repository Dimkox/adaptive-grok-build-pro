# architect — BINDING M0 live Trust Authority design

Change: `20260824-user-query-read-agents-md-decisions-md-mistakes-372269`  
Route: `3722694830f7` · intent=`review` · write_agent=`null` · gates=`scope_and_design_approval` + `migration_or_external_write_approval`  
Authority: user M0-only order, `DARK_FACTORY_ROADMAP.md` M0, `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, live GitHub/host probes.  
Read-only except this report. Did not read `.env`, `*.pem`, or credential bodies. Did not push, merge, deploy, compose-up, webhook, or branch-protect.

## Ruling

**M0 is source-complete and live-absent. Stop this route at design. Do not implement M1 again. Do not mix M2–M9. Do not compose-up, webhook, branch-protect, or read the App PEM until named grants and both human gates pass.**

`origin/main` is `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` (M1 typed spec already merged via named bootstrap exception). Product identity stays **2.0.12**. Trust CI service identity stays **2.1.0**. Local workspace is still `milestone/m1-typed-intent` @ `5a63d1c` with dirty change-package paperwork — the M0 branch must be created from `origin/main` `48cb973`, not from this working tree.

Live gap (probed 2026-08-24, no secrets):

| Probe | Result |
| --- | --- |
| `GET .../branches/main/protection` | HTTP 404 `Branch not protected` |
| `GET .../hooks` | `[]` |
| check-runs + combined status on `48cb973` | total 0, state `pending` with empty statuses |
| Open PRs | none; no `milestone/m0-live-trust-authority` |
| `.github/` on `main` | absent |
| GitHub Actions registry | leftover workflow `trusted-ci` **id 340420982 path `.github/workflows/trusted-ci.yml` state=active**, 0 runs on `main` (stale PR #1 registration; file not in tree) |
| Docker | no Trust CI containers; leftover `adaptive-trust-ci-{api,worker,runner}:2.1.0` images exist and are **not running** |
| `127.0.0.1:8080` | SearXNG (`searxng/2026.6.11-4dd0bf486`, `/health/ready` = 404) |
| App installation ID | not queryable with current `gh` user token (`GET .../installation` → 401 JWT decode) |
| `trust-ci/runtime/github-app-private-key.pem` | filename present, gitignored; **not opened** |
| `trust-ci/runtime/policy.json`, `trust-store.json`, `env/*.env` | absent (examples only) |

M1 bootstrap exceptions remain in force until a live App-owned check exists on an exact PR SHA. They do not authorize merge of this M0 work, forging `adaptive-trust-ci/verified@*`, or protecting `main` before that check is observed.

**This analysis turn is the design package for `scope_and_design_approval`. Parent must present it and stop.** After approval, first in-repo vertical is design-docs only. First live-activation vertical requires a dedicated CI host that is **not this laptop**.

---

## 1. First vertical after design approval (smallest coherent activation slice)

M0 is four independently reviewable slices. Do not collapse them. Do not start slice N+1 until slice N exit is recorded.

### Slice M0.0 — Design freeze (first vertical; in-repo only)

Smallest coherent slice after `scope_and_design_approval`. No runtime. No host. No secrets.

1. From a **clean** worktree of `origin/main` `48cb973`, create `milestone/m0-live-trust-authority`.
2. Add the two docs named in §3 (spec + plan). Optionally add an operator-safe activation-report **template** with empty evidence fields.
3. TDD: characterization tests that freeze M0 invariants already true in-tree (no `.github/workflows/**`, API source must not contain `GitHubAppAuth`/`GitHubClient`, worker source must contain `GitHubAppAuth`, compose publishes `127.0.0.1` not `0.0.0.0`, holdout forbids workflows). Do **not** add tests that assert `main` is unprotected or that check-runs are empty — those would fight the later live goal.
4. Do not bump `VERSION`. Do not edit K16. Do not touch `schemas/change-spec.schema.json` / `scripts/grok_spec.py` (M1, already on main). Do not create `factory/`. Do not add `.github/workflows/`.
5. Open a **draft** PR only after the grant in §5.

Exit of M0.0: spec+plan merged-or-at-least-pushed on the milestone branch; `grok_verify --mode pr` green on that tree; no runtime mutation.

### Slice M0.1 — Dedicated-host listener (first *live* activation vertical)

Smallest slice that changes runtime. Requires `migration_or_external_write_approval` + exact host grant. **Cannot run on this laptop.**

Host-owned, untracked: env files, `runtime/policy.json` with immutable image+holdout digests, trust-store (public keys only), CI Ed25519 key, App RSA mount, holdout directory. Then on **that host only**:

```text
docker compose up -d postgres migrate api docker-engine runner-loader worker
curl -fsS https://<ci-host>/health/ready     # or 127.0.0.1:<api> behind TLS proxy
```

Exit of M0.1: `/health/ready` 200 from the dedicated host; API has webhook secret + trust store and **no** App key; worker has App ID + installation ID + PEM + signing key and **no** webhook secret; policy digest known; **webhook still absent**; **main still unprotected**.

### Slice M0.2 — Live authority proof (webhook + disposable PR + App-owned check)

Rollout order is binding: deploy → webhook → disposable docs PR → observe App-owned policy-epoch Check Run on exact head SHA → offline attestation verify. Prove SHA change, policy-epoch rename, `trust-ci/**` `needs_approval` + human Ed25519 requeue of the **same** durable Check Run, source-mutation fail-closed, kill switch, backup/restore/restart. **Do not protect `main` in this slice.**

Exit of M0.2: Check Run `adaptive-trust-ci/verified@<policy-sha12>` on the disposable PR head, `app.slug` = Trust CI App, `external_id` = durable job id, attestation verifies with the published CI public key.

### Slice M0.3 — Bind `main` and revoke bootstrap language

Only after M0.2 is unambiguous. Temporary **human** admin token. `adaptive-trust-ci branch-protect` with exact epoch name **and** App ID. Prove: same text from another actor does not satisfy; direct push / force-push / delete / merge-without-check fail; admins cannot bypass. Disable leftover Actions workflow `340420982`. Supersede bootstrap-exception language in `decisions.md` / README current-state (exception **revoked because live check exists**, not because we forged one). Operator-safe activation report with IDs and digests, no secrets.

M0 program exit is the roadmap block: `main protected`, required check = current epoch from App ID, disposable PR success, attestation verified, protected-path approval proven, backup+restore+restart pass, kill switch pass, no GitHub Actions.

---

## 2. Dedicated CI host vs this laptop (8080 collision)

**This laptop is forbidden as the Trust CI host.** Remapping `8080`→another port here is not an acceptable design. The collision is a symptom; the host is disqualified on trust-boundary grounds.

Laptop facts:

- `127.0.0.1:8080` is SearXNG (`granian`, generator `searxng/2026.6.11+4dd0bf486`). Trust CI compose publishes `127.0.0.1:8080:8080`; bind would fail or steal SearXNG.
- Co-located workloads: n8n+Caddy (`80`/`443`/`5678`), `postgres-db`, `backup-postgres`, `domestos-pg:5433`, mongo×2, CouchDB `:5984`, nginx `:8083`, MySQL, glider proxies. README/runbook require a dedicated Linux CI host **without production workloads**.
- Worker path includes privileged rootless DinD (`docker-engine` in `compose.yaml`). Sharing this machine's Docker engine with unrelated stacks puts the Docker socket trust domain next to app data.
- Agent workspace contains `trust-ci/runtime/github-app-private-key.pem`. Production must mount a **host-owned** key, not an agent-readable laptop path.
- `TRUST_CI_PUBLIC_BASE_URL` must be HTTPS outside localhost. This laptop has no Trust CI TLS name.

Required dedicated host (non-secret):

| Requirement | Why |
| --- | --- |
| Separate Linux VM/host, Docker Engine + Compose v2 | Privileged worker + DinD isolation |
| No SearXNG/n8n/app DBs on that engine | Trust boundary |
| HTTPS reverse proxy terminating TLS to API `/webhooks/github` and `/approvals` | GitHub webhook + `TRUST_CI_PUBLIC_BASE_URL` |
| In-container API may keep `:8080`; publish only `127.0.0.1:<local>` on **that** host | Laptop `:8080` is irrelevant there |
| Outbound GitHub from API (webhook ack) and worker (checkout, Checks API) | Live proof |
| Runner containers: `network=none`, no socket, no secrets | Isolation |
| Host paths: policy, trust-store, holdout, CI signing key, App PEM; API never receives App PEM or signing key | Role split |
| PostgreSQL named volume + backup destination on that host | Durability |
| Installation ID + App ID in **worker.env only**, never committed | Auth |

In-container port 8080 is not a product defect. Do not retarget compose to this laptop. Optional later (not M0.0): make the **published** host port an env interpolation for dedicated-host flexibility; default remains `127.0.0.1:8080:8080`. That change is unnecessary if M0.1 uses a clean host.

Leftover local images `adaptive-trust-ci-{api,worker,runner}:2.1.0` matching `build/adaptive-trust-ci-pin.env` (gitignored scratch) are **not** a live deployment. Mutable tags `:latest` must never be deployed. M0.1 must pin `name@sha256:` in host `.env` **and** `runtime/policy.json` `sandbox.image`.

---

## 3. Design spec file: where it lives and what it contains

Roadmap §11 is binding for in-repo locations. Do not put secrets there. Do not invent a second authority file under `engineering/changes/` as the product spec (this change package is route evidence only).

| File | Role |
| --- | --- |
| `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md` | **Authoritative M0 design spec** (new). References, does not replace, `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md` (service already on main). |
| `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md` | Implementation plan, task-by-task, TDD first, slices M0.0–M0.3. |
| `engineering/runbooks/trust-ci-rollout.md` | Existing operational runbook; update only if a host-port/proxy fact is missing. Do not duplicate the spec. |
| `engineering/runbooks/trust-ci-activation-report.md` | Operator-safe evidence **template** in M0.0; filled after M0.2/M0.3 from the dedicated host. Empty fields stay `UNKNOWN` until live. |
| `trust-ci/config/policy.example.json`, `env/*.example`, `config/trust-store.example.json` | Contracts for host copies. Never commit filled `env/*.env`, `runtime/*.pem`, `runtime/policy.json`, `runtime/trust-store.json`. |

### Spec contents (required headings)

1. **Objective** — turn existing `trust-ci/` source into actual merge authority for `main`; GitHub Actions remain absent.
2. **Baseline** — repository `Dimkox/adaptive-grok-build-pro`; base SHA `48cb9737fac7f26fb70b425957a3ed64d4c1eb55`; product `2.0.12`; Trust CI `2.1.0`; M1 already on main; M0 still unmet.
3. **Live gap table** — copy the probe table above (no secrets).
4. **Trust boundary** — trusted: dedicated-host images, server policy, holdout digest, PostgreSQL, worker-only CI key, worker-only App RSA, API-only webhook secret, API-only human pubkey store, branch protection bound to App ID. Untrusted: PR tree, local receipts, delegated grants, agent output, this laptop.
5. **Role split** — API cannot publish a successful check; worker cannot read webhook secret or trust-store; runner gets none of token/key/socket/network; human approval private keys never on CI host or in agent workspace.
6. **Check contract** — name `adaptive-trust-ci/verified@<first-12-hex of policy sha256>`; `external_id` = durable job id; owner = Trust CI GitHub App; success backed by stored Ed25519 attestation.
7. **Rollout order** — deploy → webhook → disposable PR → observe App-owned check + attestation → **then** `branch-protect`. Protecting first can lock the repo.
8. **GitHub App** — permissions `Checks: read/write`, `Contents: read`, `Pull requests: read`; worker requests reduced installation token `checks:write,contents:read,pull_requests:read`. App ID + installation ID live only in worker env. Record IDs in the activation report, never next to PEM material in git.
9. **Host** — dedicated CI host required; this laptop forbidden; HTTPS URL; pin digests; holdout outside checkout.
10. **Human approvals** — `approval-create` on a human machine; scopes from actual diff; bind repository, PR, base SHA, head SHA, policy digest, actor, key_id, nonce, TTL; worker restarts the same Check Run.
11. **Kill switch, backup, rollback** — as runbook; policy/holdout rollback changes the epoch and requires a fresh observed check before re-protecting.
12. **Exit criteria** — verbatim roadmap M0 block plus: leftover Actions workflow `340420982` disabled/deleted; bootstrap-exception language superseded.
13. **Forbidden** — `.github/workflows/**`; Dependabot CI; forging the check; reading/committing PEM; using local receipts as merge authority; M1 re-implementation; M2–M9; `factory/`; root packaging markers; auto-merge; protecting `main` before the live check.

The implementation plan lists M0.0–M0.3 as checkboxed tasks with the TDD split in §4, exact grant names in §5, and STOP in §6.

---

## 4. TDD / integration drills — allowed now vs needs `migration_or_external_write_approval`

### Allowed before live GitHub writes (after design approval; still no prod compose-up on this laptop)

| Drill | Evidence | Notes |
| --- | --- | --- |
| Existing `PYTHONPATH=trust-ci/src python3 -m unittest discover -s trust-ci/tests` | Fake transport; JWT; reduced installation token; Check Run create/restart; app-bound protection payload; HMAC; nonce replay; holdout digest | No network to GitHub required |
| `python3 -m compileall -q trust-ci/src` and root `python3 scripts/grok_verify.py --mode pr` | Preflight only | Not merge authority |
| `docker compose -f trust-ci/compose.yaml config` (no `up`) | Published bind is `127.0.0.1:8080:8080`; images require digest interpolation | Config parse only |
| `make trust-ci-holdout-digest` on `trust-ci/holdout.example/` | Example digest only | Must not be treated as deployed holdout |
| New unit tests for M0.0 invariants listed in §1 | TDD red→green on docs+invariants | Do not assert live unprotected `main` |
| Offline `adaptive-trust-ci keygen` / `approval-verify` / `attestation-verify` against **fixture** keys in tmpdirs | Crypto | Never use `trust-ci/runtime/github-app-private-key.pem` |
| Read-only `gh api` GETs already used here | Live gap characterization | Not a write |

`make trust-ci-postgres-test` starts `compose.test.yaml` (isolated network, **no** published 8080, **no** DinD, **no** GitHub). It is a local integration drill, not a live GitHub write. It **is** still `docker compose up` on this overcrowded engine. **Defer it until design approval.** Do not treat a green postgres harness on this laptop as M0 host qualification. After approval it is allowed **without** `migration_or_external_write_approval` because it performs no GitHub/production write. Production `trust-ci/compose.yaml up` is not this command.

### Needs `migration_or_external_write_approval` + exact delegated local grant

| Drill / action | Grant shape (minimum) |
| --- | --- |
| `git push` of `milestone/m0-live-trust-authority` | `--action git-push-branch` + resource `origin milestone/m0-live-trust-authority` |
| `gh pr create --draft` | `--action external-write` + resource `gh pr create` (no `pull-request-merge`) |
| Query installation ID via App JWT | requires reading worker PEM → named grant; do not print PEM |
| `docker compose -f trust-ci/compose.yaml up` on dedicated host | production/external-write on that host; never on this laptop |
| Register repo webhook `POST https://<ci>/webhooks/github` | `external-write` + resource the hooks API / `gh api .../hooks` |
| Disposable PR that is the **proof vehicle** (docs-only) | `git-push-branch` + `external-write` (`gh pr create`) |
| Worker publishing Check Runs | happens only from dedicated host worker; App credentials stay on host |
| Human `approval-create` / `approval-submit` | human machine; agent must not hold the private key |
| Kill-switch / backup restore on the live host | host grant |
| Disable leftover workflow `340420982` | `external-write` + resource `actions/workflows/340420982` |
| `adaptive-trust-ci branch-protect` | last; temporary human admin token; `external-write`; **after** M0.2 proof |

A mocked GitHub test does not replace M0.2. A live Check Run on an exact SHA is the first authority evidence. Branch protection is not a drill to “try early”.

---

## 5. May parent create the branch + draft PR with design-only docs while `write_agent` is null?

**No, not in this analysis turn. After `scope_and_design_approval`, local branch + docs require a write owner; push + draft PR additionally require `migration_or_external_write_approval` and an exact grant.**

Facts:

- Route `write_agent=null`, intent=`review`. Adaptive-delivery: present design and **stop before implementation**; dispatch only the route write owner.
- User order to create `milestone/m0-live-trust-authority`, write spec/plan, and open a draft PR early is **scope** (source of truth #1). It is not a local grant and it does not cancel the named gates.
- Creating the two docs is a product change. With `write_agent=null`, parent must **re-route** so a single write owner (expected: `general_implementer`) lands M0.0. Parent must not impersonate a write agent and must not use a domain implementer the route did not select.
- Local `git switch -c milestone/m0-live-trust-authority origin/main` is not an external write, but it must start from `48cb973`, not from dirty `milestone/m1-typed-intent` @ `5a63d1c`.
- `git push` and `gh pr create` **are** external GitHub writes. User “open a draft PR early” does not mint `scripts/grok_approve.py`. Required after design approval: exact grant `git-push-branch` + `external-write` bound to this repo, this route/change, then-current HEAD/fingerprint, named resources, TTL. Grant cannot merge, tag, release, webhook, or branch-protect.
- Draft PRs **must** enqueue Trust CI jobs once the webhook exists (`decisions.md` 2026-08-23). That matters in M0.2, not M0.0 (no webhook yet).

Sequence after the user accepts this design:

```text
scope_and_design_approval (this report)
  → re-route with write_agent for M0.0 docs
  → local branch from origin/main 48cb973
  → spec + plan + invariant tests
  → grok_verify --mode pr
  → request exact grant
  → push branch + draft PR (still draft; no merge)
  → STOP runtime until dedicated-host grant (M0.1)
```

---

## 6. Explicit STOP

Until the user accepts this design **and** issues the named grants for the next slice, agents and parent must not:

1. `docker compose -f trust-ci/compose.yaml up` (any host, any port remap on this laptop).
2. Register or modify a GitHub webhook.
3. Run `adaptive-trust-ci branch-protect` or otherwise protect `main`.
4. Read, print, copy, or commit `trust-ci/runtime/github-app-private-key.pem` or any `.env` / private key / trust-store private material.
5. Generate, submit, or simulate a human approval private key.
6. Forge `adaptive-trust-ci/verified@*` or a commit status of that name.
7. Add `.github/workflows/**`, Dependabot workflows, or another CI SaaS.
8. Implement or extend M1 typed-spec files; start M2–M9; create `factory/`; bump VERSION/tag/release.
9. Push, merge, or deploy without an exact delegated local grant naming that action and resource.
10. Treat leftover local `adaptive-trust-ci*:2.1.0` images, the gitignored PEM filename, or the M1 bootstrap exception as live Trust Authority.

`scope_and_design_approval` is **open**. `migration_or_external_write_approval` is **open**. This report is the design to approve. It is not that approval.

---

## Conflicts and bounded rulings

| Conflict | Ruling |
| --- | --- |
| Roadmap baseline SHA `73e4ae7` vs current `main` `48cb973` | Current `main` wins. M1 is already on `main`. Do not reset. |
| Roadmap “M1 missing” vs tree | Stale. Do not re-implement M1. |
| `repo_explorer` “no GitHub Actions = true” live vs Actions API `trusted-ci` **active** | Tree has no workflows (correct). GitHub registry still has active workflow **340420982**. M0.3 must disable it. Until then live “no GitHub Actions” is **false in the registry**, true in git. |
| User “create branch + draft PR now” vs `write_agent=null` + design gate | Gate wins for this turn. After approval, re-route a write owner for docs; grants for push/PR. |
| 8080 collision vs “just change the port” | Rejected. Dedicated host required. |
| Existing control-plane spec (2026-08-23) vs new M0 spec | Keep 2026-08-23 as the service design (already built). Add 2026-08-24 as **activation** spec. Do not rebuild Trust CI in this milestone. |

---

## Non-goals (this milestone and this route)

- M1 schema/CLI/tests (already on `48cb973`).
- M2 architecture model, M3 governance, M4–M9 factory/shadow/autonomy/canary.
- GitHub Actions of any kind.
- Auto-merge, production deploy of the product zip, VERSION 2.0.13.
- Using this change package’s filled `change-spec.yaml` as live merge authority (it is not).
- Colocating Trust CI with SearXNG on `:8080`.
