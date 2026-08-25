# architect — BINDING ruling: M0 CI host is claw, not a laptop

Change: `20260824-user-query-какой-нахуй-ноут-ты-работаешь-на-xeon-c8e5e5`  
Route: `c8e5e567a15d` · write_agent=`general_implementer` · gates=`[]` · branch=`milestone/m0-live-trust-authority` · PR=#5 draft (`9f84dfd7b5458e5394314c5f6913aa5c6631c058`)  
Authority: user source-of-truth #1 (hostname **claw**, Xeon E5-2680 v4, ~16 GiB ECC); sibling `analysis-repo_explorer.md`, `analysis-task_analyst.md`; retract `analysis-docs_researcher.md` where it forbids claw as CI host.  
Read-only except this report. Did not read `.env`, PEM, or credential bodies. Did not push, merge, deploy, compose-up, webhook, or branch-protect.

## Ruling

**Retract “this laptop.” The M0 CI host is `claw`. Do not compose-up, webhook, or branch-protect in this slice. Do not start M1/M2.**

1. **Hostname is `claw`.** Chassis desktop (INTEL X99 W-D4H), `Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz`, MemTotal `16268340 kB` (~16 GiB), Ubuntu 24.04.4 LTS. User states ECC; this turn did not independently read SPD/EDAC. Never call this machine a laptop. SearXNG on `127.0.0.1:8080` and co-located n8n/app DBs **remain facts**; they do not rename the host.

2. **M0.1 on claw MUST NOT bind host 8080.** In-container API listen stays `8080` (healthcheck `http://127.0.0.1:8080/health/ready` inside `api`). Published mapping must be env-interpolated. Default **`127.0.0.1:18080:8080`**. `ss -ltn` on claw: `127.0.0.1:8080` is LISTEN; **`18080` is not**. Healthcheck must not be rewritten to the host port.

3. **Co-located stacks are residual risk the user accepted by naming claw.** Isolate Compose project **`adaptive-trust-ci`** (`name: adaptive-trust-ci` on `trust-ci/compose.yaml`). Do not steal existing containers (`searxng-instance`, `n8n-core`, `n8n-proxy`, `postgres-db`, `backup-postgres`, `domestos-pg`, `pulsengineering-dev-*`, …), their volumes, or their networks. Do not `external: true` any of those.

4. **This slice is docs + compose-file + invariant tests + a `decisions.md` line. It is not M0.1 runtime.** No `docker compose up`, no webhook, no `branch-protect`, no PEM read. Stay on `milestone/m0-live-trust-authority` / PR #5 (keep draft). Write owner = `general_implementer` only.

5. **Prior “laptop forbidden / do not remap 8080” ruling is withdrawn for naming and for the published port.** Co-location and privileged DinD next to app data stay residual; they no longer disqualify `claw` as the named host.

Exact `decisions.md` entry the implementer must append (three sentences, no more):

```markdown
## 2026-08-24 — M0 CI host is claw, not a laptop

The M0 Trust CI host is hostname `claw` (Xeon E5-2680 v4, ~16 GiB ECC, Ubuntu 24.04). Never call it a laptop; SearXNG already owns `127.0.0.1:8080` and co-located n8n/app databases remain residual risk the user accepted. Trust CI therefore publishes another loopback port (`127.0.0.1:18080` by default) with compose project `adaptive-trust-ci`.
```

---

## Conflicts (this ruling wins)

| Source | Claim | Disposition |
| --- | --- | --- |
| User query + parent correction | Host is **claw**, named M0 CI host | **SoT #1** |
| `analysis-docs_researcher.md` | Replace “this laptop” with “host claw is **forbidden**”; do not retarget Trust CI onto claw | **Overruled.** That keeps the misnomer’s conclusion. Retract laptop language **and** record claw as the named host. Keep SearXNG/n8n/DinD as **compose-up constraints**, not a host un-naming. |
| `372269` architect §2 | “This laptop is forbidden”; remapping 8080 is not acceptable; default may stay `127.0.0.1:8080:8080` | **Overruled** on naming and published-port default. Collision fact stands. |
| `analysis-task_analyst.md` | claw is the M0.1 hostname; no compose-up this turn | **Accepted.** |
| `analysis-task_analyst.md` | In scope **docs only**; `test_m0_invariants` stays unchanged | **Overruled in part.** Compose file + project `name` + invariant test must change or the next `up` still steals 8080 and the current test pins the bad mapping. |

Historical change package `372269` is not edited. Product spec/plan/activation/compose/tests/`decisions.md` on this branch are.

---

## Host occupancy (probed, no secrets)

| Probe | Result |
| --- | --- |
| `hostname` | `claw` |
| Chassis | desktop (not laptop) |
| CPU | Xeon E5-2680 v4 @ 2.40GHz |
| RAM | ~16 GiB |
| OS | Ubuntu 24.04.4 LTS |
| `127.0.0.1:8080` | LISTEN; SearXNG container `searxng-instance` `127.0.0.1:8080->8080/tcp` |
| `18080` | **not listening** — selected published host port |
| Other loopback/host ports (do not steal) | `1080`, `11080`, `3001`, `5433`, `5678`, `5984`, `8000`, `8083`, `22`, Samba `139/445` |
| Trust CI runtime | no Trust CI containers; leftover images may exist and stay stopped |
| Git | `milestone/m0-live-trust-authority` @ `9f84dfd`; PR https://github.com/Dimkox/adaptive-grok-build-pro/pull/5 draft vs `main` |

Same Docker engine (names only, from repo_explorer): `n8n-core`, `n8n-proxy`, `backup-postgres`, `drive-sync`, `ruflo-mcp`, `backup-mongo`, `ruflo-mongo`, `postgres-db`, `proxy-gateway`, `pulsengineering-dev-gateway-1`, `pulsengineering-dev-web-1`, `pulsengineering-dev-db-1`, `proxy-gateway-a2`, `domestos-pg`, `obsidian-couch`, `searxng-instance`.

---

## Compose contract (file change now; `up` later)

`trust-ci/compose.yaml` today has **no** top-level `name:` (project would default to directory `trust-ci`) and hard-codes:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

Required shape:

```yaml
name: adaptive-trust-ci

# services: unchanged except api.ports
      ports:
        - "127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"
```

Keep:

- API process `--port 8080` / in-container healthcheck URL `http://127.0.0.1:8080/health/ready`
- Loopback-only publish (`127.0.0.1:`, never `0.0.0.0:`)
- Named volumes **not** `external: true` (they become `adaptive-trust-ci_trust-ci-postgres` etc.)
- Networks **not** renamed to a bare `trust-ci` / `executor` that might already exist

Compose interpolates `TRUST_CI_API_HOST_PORT` from the compose process environment / `trust-ci/.env`, **not** from `env_file:` on `api`. Default `:-18080` is the fail-safe so an operator who forgets the var still does not bind SearXNG’s 8080. Do not add a required `:?` on the host port.

`compose.test.yaml` / `compose.build.yaml`: do not give them `name: adaptive-trust-ci`. Test compose may later use `adaptive-trust-ci-test` (out of this slice). `make trust-ci-compose` (`docker compose … config`, no `up`) is allowed after the file change; **`up` is not**.

Operator curl examples that still say `http://127.0.0.1:8080/health/ready` would hit SearXNG on claw. Update those strings to `http://127.0.0.1:18080/health/ready` (or `${TRUST_CI_API_HOST_PORT:-18080}`) in the same write: `trust-ci/README.md`, `engineering/runbooks/trust-ci-rollout.md`, `QUICKSTART.md` Trust CI health snippet, `trust-ci/scripts/smoke.sh` default `base_url`. Do **not** rewrite DARK_FACTORY / consumer “laptop session” language; that is a different meaning.

TLS reverse proxy and `TRUST_CI_PUBLIC_BASE_URL=https://…` remain M0.1+ host-owned work. This slice does not add Caddy/nginx or steal `:80`/`:443`.

---

## Spec / plan / activation edits

### `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`

| Location | From | To |
| --- | --- | --- |
| Live gap `127.0.0.1:8080` row | keep SearXNG fact | keep; add that Trust CI **must not** publish host 8080; published default `18080` |
| Untrusted list | `this laptop` | drop the host-as-device. Untrusted = PR tree, `AGENTS.md`, `.grok/**`, local receipts, delegated grants, agent output, GitGuardian, leftover Actions. **Agent workspace on claw is untrusted even though claw is the CI host.** Trusted = deployed project `adaptive-trust-ci` images/policy/holdout/Postgres/keys, not the checkout. |
| Host section | “This laptop is **forbidden** as the Trust CI host…” | **Host is `claw`.** User named it. Port 8080 is SearXNG; n8n/Caddy/app DBs share the engine; privileged DinD remains residual; `TRUST_CI_PUBLIC_BASE_URL` must still be HTTPS. Hostname gate for M0.1 is **satisfied**. Compose-up still needs `migration_or_external_write_approval`. |
| Forbidden | “Using this laptop as the CI host” | “Calling `claw` a laptop”; “Publishing Trust CI on host 8080”; “Stealing existing containers/volumes/networks”; “compose-up / webhook / branch-protect in the host-name slice” |

Do not add “using host claw as the CI host” to Forbidden.

### `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`

- M0.0 invariant bullet: compose publishes `127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080`, project `name: adaptive-trust-ci`, not `127.0.0.1:8080:8080`.
- M0.1: named host **is `claw`**. Delete “host name is still required before this slice” and “(not this laptop)”. Keep `migration_or_external_write_approval`. Keep “webhook still absent; `main` still unprotected.” Note published port 18080 and project `adaptive-trust-ci`.
- This host-name correction lands **on the existing M0.0 PR**, not as M0.1 execution.

### `engineering/runbooks/trust-ci-activation-report.md`

| Field | Value |
| --- | --- |
| Dedicated CI host (hostname only) | `claw` |
| All other live fields | stay `UNKNOWN` |

---

## Tests (TDD; red then green)

`trust-ci/tests/test_m0_invariants.py` currently **pins the defect**:

```python
self.assertIn("127.0.0.1:8080:8080", text)
```

Change `test_compose_publishes_loopback_not_all_interfaces` to assert:

- top-level `name: adaptive-trust-ci`
- published `"127.0.0.1:${TRUST_CI_API_HOST_PORT:-18080}:8080"`
- **absence** of published `"127.0.0.1:8080:8080"`
- absence of `0.0.0.0:` publish
- healthcheck still `http://127.0.0.1:8080/health/ready`

Add `test_m0_docs_name_claw_not_laptop`: spec + plan contain `claw` and do not contain `this laptop`; activation report host cell is `claw`. Do not globally ban the word “laptop” (DARK_FACTORY / consumer QUICKSTART). Do not assert live `main` protection or empty check-runs.

Allowed check this slice: `python3 -m unittest trust-ci.tests.test_m0_invariants` then `python3 scripts/grok_verify.py --mode pr`. Forbidden: any `docker compose up`.

---

## Implementer file list

**Must**

- `docs/superpowers/specs/2026-08-24-m0-live-trust-authority.md`
- `docs/superpowers/plans/2026-08-24-m0-live-trust-authority.md`
- `engineering/runbooks/trust-ci-activation-report.md`
- `trust-ci/compose.yaml` (`name:` + host port interpolation)
- `trust-ci/tests/test_m0_invariants.py`
- `decisions.md` (exact three-sentence entry above)
- this change package (`architecture.md`, `requirements.md`, `brief.md`, `test-plan.md`, `change-spec.yaml`) so shared memory matches the ruling

**Same write (operator curl would otherwise still steal 8080)**

- `trust-ci/README.md` health curl
- `engineering/runbooks/trust-ci-rollout.md` health curl
- `QUICKSTART.md` Trust CI health curl only
- `trust-ci/scripts/smoke.sh` default `base_url`

**Must not**

- `docker compose up` / systemd enable / `/health/ready` against a live Trust CI (none exists)
- GitHub webhook, `branch-protect`, disable workflow `340420982`
- read/commit PEM, `.env`, human approval keys
- M1 typed-spec files, M2–M9, `factory/`, VERSION/tag/release
- `.github/workflows/**`
- push, merge, mark PR #5 ready
- edit historical `372269` package; edit Bitrix core; steal containers
- `container_name:` overrides that collide with `searxng-instance` / `n8n-*` / `postgres-db`

---

## Residual risk (accepted, not solved)

- Privileged rootless DinD on the same Docker engine as n8n/app Postgres/Mongo/SearXNG.
- Agent workspace on claw can see gitignored `trust-ci/runtime/github-app-private-key.pem` filename; M0.1 must mount a **host-owned** key, and agents still must not open it.
- No Trust CI TLS name yet; GitHub will not deliver webhooks to `http://127.0.0.1:18080`.
- ~16 GiB RAM + co-located stacks: worker/DinD memory pressure is operational, not a naming issue.
- Leftover Actions workflow `340420982` stays for M0.3.
- Bootstrap-exception language stays until a live App-owned check exists.

---

## STOP

Until a **later** route with `migration_or_external_write_approval` and an exact host grant, nobody may:

1. `docker compose -f trust-ci/compose.yaml up` (any port, including 18080).
2. Register or modify a GitHub webhook.
3. `adaptive-trust-ci branch-protect` or otherwise protect `main`.
4. Read, print, copy, or commit App PEM, signing key, webhook secret, or human approval private keys.
5. Forge `adaptive-trust-ci/verified@*`.
6. Add GitHub Actions.
7. Leave this branch for M1/M2 work.
8. Call `claw` a laptop in product spec, plan, or activation report.

Write owner: `general_implementer`. Stay on PR #5.
