# repo_explorer — M0 in-tree vs live (route 3722694830f7)

Inspected: `trust-ci/` (compose, Dockerfiles, src, tests, env/*.example, config/*.example, holdout.example/validate.py, sql/, systemd/), `VERSION`=2.0.12, `DARK_FACTORY_ROADMAP.md` M0 items, `engineering/runbooks/trust-ci-rollout.md`. Did not open `.env`, `*.pem`, keys, or `trust-ci/runtime` secret bodies. No push/merge/deploy.

## Parent observations — confirm

| Observation | Result |
|---|---|
| `origin/main` = `48cb9737fac7f26fb70b425957a3ed64d4c1eb55` | **confirmed** (`git rev-parse origin/main`) |
| local = `milestone/m1-typed-intent` @ `5a63d1c915e4f86260b60ce98bbad56b5dd9e0f4` | **confirmed** |
| `main.protected=false`; protection API 404 | **accepted** (parent GitHub probe) |
| repo webhooks length 0 | **accepted** |
| check-runs on `48cb973`: total 0 | **accepted** |
| PR #4 merged; only GitGuardian, not `adaptive-trust-ci/verified@*` | **accepted** |
| no `.github/workflows` | **confirmed** (`NO_GHA`) |
| docker: no trust-ci api/worker/postgres running; `127.0.0.1:8080` = SearXNG | **confirmed** (`searxng-instance` maps 127.0.0.1:8080; no trust-ci container names) |
| `trust-ci/runtime/github-app-private-key.pem` present | **confirmed** (filename only; not opened) |
| App install ID unverified (403/401) | **accepted**; not re-probed |

## Host vs tree (additional)

- `trust-ci/runtime/`: `.gitkeep` + `github-app-private-key.pem` only. **No** `policy.json`, `trust-store.json`, `control/`, `holdout/`.
- `trust-ci/env/`: **examples only** (`*.env.example`). No `api.env` / `worker.env` / `postgres.env`.
- Local Docker **images** exist (`adaptive-trust-ci-{api,worker,runner,test}:2.1.0` and ghcr mirrors; `:latest` for api/worker). **No** running api/worker/postgres for Trust CI.
- Port 8080 occupied by SearXNG, not Trust CI `/health/ready`.
- Host postgres containers (`postgres-db`, `backup-postgres`, `domestos-pg`) are unrelated app stack, not Trust CI compose.

## M0 work item → in-tree / live / missing

| M0 work item | In-tree | Live | Missing |
|---|---|---|---|
| Trust CI product source (API, worker, GitHub App client, webhooks, policy, holdout, signing, store, migrations) | yes (`trust-ci/src/adaptive_trust_ci/`, tests, compose, SQL, systemd units) | no running stack | deploy |
| App installed on `Dimkox/adaptive-grok-build-pro` | docs/runbook only | unverified (401/403) | install ID + confirmation |
| App ID + installation ID in operator-only config | not in git (correct) | pem file on disk only | operator env + IDs |
| App RSA key mounted worker-only | pem present in `runtime/` (do not commit) | not mounted in a worker container | worker compose runtime |
| API-only webhook secret | env examples | webhooks=0 | secret + registration |
| Build API/worker/runner/holdout | Dockerfiles + compose.build; local 2.1.0 images | not deployed | pin + run |
| Pin images + holdout by digest | compose requires `${…:?digest}`; `holdout.example/` | no `runtime/policy.json` | live pins |
| SBOMs / signatures / supply-chain manifest | scripts + `test_supply_chain.py` | not observed live | generate/sign for deploy |
| Deploy PG + migrate + API + worker + runner + holdout + metrics + backup + HTTPS | compose.yaml, systemd, backup scripts | none of these services running | isolated CI host deploy |
| Webhook `POST /webhooks/github` | code + tests | length 0 | GitHub webhook |
| Check Run `adaptive-trust-ci/verified@<policy-sha12>` on exact SHA | naming in AGENTS/runbook/tests | 0 checks on `48cb973`; PR #4 ≠ this check | first live job |
| Check owned by Trust CI App | implementation | not proven | live check |
| Signed attestation + public-key verify | signing + tests | no job | live attest |
| Protected-path `needs_approval` + Ed25519 human approval | tests | not live | drill |
| Reject expired/wrong-scope/wrong-SHA/policy/nonce | tests | not live | drill |
| Kill switch | runbook + code | not live | drill |
| Branch protection after live check | `branch-protect` CLI in runbook | `main` unprotected (404) | apply after proof |
| Protection binds epoch check + App ID | runbook | not applied | |
| Direct push / force / delete / merge-without-check fail | intended | not enforced | |
| Remove bootstrap-exception language | still in roadmap (M0 unchecked) | n/a | after live authority |
| No GitHub Actions | **true** | **true** | — |

## Exit criteria vs now

`main protected=false`; required check absent; exact-SHA disposable PR not proven; attestation not independently verified on GitHub; approval/kill/backup-restore drills not live; **no GitHub Actions = true**.

M0 is **source + local tests + leftover images/key file**. It is **not** live merge authority.
