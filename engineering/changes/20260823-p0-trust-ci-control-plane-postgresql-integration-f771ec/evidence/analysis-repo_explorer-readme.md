# Repo explorer — README / QUICKSTART / pins vs current tree

Change: `20260823-p0-trust-ci-control-plane-postgresql-integration-f771ec`  
Active route: `2335b3d0d9fc` (intent=docs, complexity=micro, write=`general_implementer`, analysis=`repo_explorer`, review=`code_reviewer`)  
Branch for delivery: `feat/trust-ci-control-plane` (PR-only). Direct push to `main` is prohibited.  
Inspected: 2026-08-23. Read-only. No `.env`, keys, push, merge, or deploy.

This report answers: what must change so the root README and QUICKSTART match the current tree (every application and database with install instructions, a rebuilt complete stack graph, updated dependency pins) without breaking tests.

Do **not** commit `engineering/changes/20260817-user-query-вычисти-*`. That package is leftover 2.0.10 cleanup paperwork and is not this work.

---

## 1. Current README stack-graph nodes and the K10 / 45-edge contract

### AGENTS.md “README before push” graph rule (quote)

> Before proposing a release, update `README.md` so it matches this tree: current VERSION, what exists, where it lives, and how the pieces connect.
>
> The README stack graph must stay complete: every listed core node is linked to every other with a `---` edge. A missing edge means the map is stale. Do not propose a release whose graph or current-state section is behind the tree.

Source: `AGENTS.md` § README before push (lines 17–19). `decisions.md` (2026-08-16) restates the same invariant: enumerate all pairwise `---` edges so a structure test can fail on a missing link.

### Current mermaid (first and only fence in `README.md`)

Caption today: local-workflow complete graph; **Trust CI is deliberately outside** the prompt-controlled graph.

Labeled vertices in the fence:

```text
Contract["AGENTS.md"]
Decisions["decisions.md"]
Mistakes["mistakes.md"]
```

Unlabeled vertices (IDs used as both node id and display text): `Route`, `Skills`, `Agents`, `Hooks`, `Policy`, `Verify`, `Packages`.

Node-role table under the fence (10 rows):

| Node | Role in README today |
| --- | --- |
| Route | `scripts/grok_route.py` / active-route |
| Skills | `.grok/skills/` and `.agents/skills/` |
| Agents | `.grok/agents/` |
| Hooks | `.grok/hooks/` |
| Policy | `.grok-stack/adaptive_grok/policy.py` |
| Verify | `scripts/grok_verify.py` + local receipts |
| Packages | `packages/` + `scripts/package_stack.py` |
| Contract | `AGENTS.md` |
| Decisions | root `decisions.md` |
| Mistakes | root `mistakes.md` |

That is a **K10**. \(C(10,2)=45\) undirected `---` edges. The fence currently contains those 45 lines and no extra `---` lines.

### Exact completeness contract in `tests/test_structure.py`

Method: `test_readme_local_stack_graph_is_complete_k10` (lines 56–80).

It does four things:

1. Hardcodes this 10-id list:

```python
nodes = [
    "Route", "Skills", "Agents", "Hooks", "Policy",
    "Verify", "Packages", "Contract", "Decisions", "Mistakes",
]
```

2. For every unordered pair, requires the README **file text** (not only the fence) to contain `Left --- Right` or `Right --- Left`.
3. Parses the **first** ` ```mermaid ` fence.
4. Counts lines matching `\S+ --- \S+` and asserts `len(edge_lines) == 45`.

It does **not**:

- assert the node-role table;
- forbid extra mermaid fences (it only parses the first);
- assert Trust CI / Postgres / Docker nodes are absent;
- derive 45 from `combinations`; 45 is a literal.

Related structure locks that a README edit can also trip:

| Test | What it freezes |
| --- | --- |
| `test_version_identity_matches_readme` | README H1 must be `# Adaptive Grok Build Pro v{VERSION}\n`. `VERSION` is `2.0.11`. |
| `test_core_product_files_exist` | `README.md` and `VERSION` exist. **`QUICKSTART.md` is not in this list.** |
| `test_trust_ci_control_plane_is_complete` | `trust-ci/` files exist; does not parse the mermaid. |
| `test_no_github_actions_workflow_exists` | no `.github/workflows`. |
| `tests/test_manifest_package.py::test_included_files_and_shipped_zip_have_no_github_actions` | `VERSION == '2.0.11'` **hardcoded**, and the shipped zip `VERSION` member is `2.0.11`. |

Historical note: CHANGELOG 2.0.8 records “K10 complete graph”. Do not rewrite that historical section. A later identity (if bumped) may mention the rebuilt graph.

### Exact test updates required if we add core nodes

If the first mermaid fence gains nodes, **the current test goes red** until all of the following change together:

1. **`tests/test_structure.py` `test_readme_local_stack_graph_is_complete_k10`**
   - Extend `nodes` with the new IDs (exact mermaid vertex ids, case-sensitive).
   - Replace the literal `45` with `len(list(itertools.combinations(nodes, 2)))` (or the matching integer). Counts:
     - K11 → 55
     - K12 → 66
     - K13 → 78
     - K14 → 91
     - K15 → 105
     - **K16 → 120** (recommended rebuilt graph below)
     - K17 → 136
   - Rename the method if it still says `k10` (optional but avoids lying). Suggested: `test_readme_stack_graph_is_complete`.
   - Keep undirected `---` only in that fence. A `-->` line is **not** counted by the current regex, so a directed leftover would silently under-count.
   - Do not emit duplicate `---` lines: `len(edge_lines)` is an exact equality, so extras fail.
   - Generate edges from `itertools.combinations(nodes, 2)` and write each pair once as `{left} --- {right}`.
2. **README mermaid + node-role table** must list the same IDs. The pair check scans the whole README, so an edge written only in prose as `Route --- Skills` would satisfy the missing-pair loop even if omitted from mermaid; the `len(edge_lines) == C(n,2)` check then fails if mermaid is short, or passes-with-a-lie if extras exist in prose. Keep every pair **inside the fence**.
3. **Caption.** Update “K10” / “local-workflow only” / “Trust CI is deliberately outside this graph” so it is not stale. AGENTS.md rule does not name K10; it names completeness over **listed core nodes**. Changing the listed set is allowed if every pair is linked.
4. **Do not add a second 45-edge paste into `QUICKSTART.md`.** QUICKSTART has no mermaid today. A second complete graph there is not locked and would rot.
5. **`CHANGELOG.md`**: only a new identity section if VERSION moves. Leave 2.0.8’s K10 sentence as history.
6. **`decisions.md`**: one ≤3-sentence entry if the implementer expands the clique (pattern + why). Not required to keep tests green.
7. **No other test currently asserts the 10-id set.** `test_toolchain.py` / installer tests do not parse mermaid.

If the implementer instead keeps the first fence as K10 and adds a **second** mermaid for Trust CI, the existing test stays green. Then add a **new** method, e.g. `test_readme_trust_ci_graph_is_complete`, that parses the **second** fence and checks its own \(C(n,2)\) pairs. Also update AGENTS.md if “the stack graph” becomes two complete graphs. That is the lower-risk option for not breaking the locked K10 test; it is **not** a single rebuilt K-graph.

---

## 2. Inventory of applications, services, databases, and host tools

There is **one product** (`Adaptive Grok Build Pro` identity `2.0.11`) and **one independently versioned service package** (`adaptive-trust-ci` `2.1.0` in `trust-ci/pyproject.toml` and `trust-ci/src/adaptive_trust_ci/__init__.py`). `install_into.py` copies the local Grok stack only. It does **not** copy `trust-ci/`, `README.md`, `QUICKSTART.md`, or `VERSION`.

### 2.1 Local Grok stack (copied by `install_into.py`)

| Surface | Path |
| --- | --- |
| Skills | `.grok/skills/`, `.agents/skills/` (15 managed skills in `.grok-stack/config/managed.json`) |
| Agents | `.grok/agents/` (21 managed agents) |
| Hooks | `.grok/hooks/` + root shims `session_start.py` … `user_prompt_submit.py` |
| Runtime lib | `.grok-stack/adaptive_grok/` |
| Config | `.grok-stack/config/{routing,policy,toolchain,managed}.json`, `quality-profiles/*.json` |
| Scripts | `scripts/grok_{route,change,status,verify,review,approve,deploy,doctor}.py`, `scripts/install_into.py`, `scripts/package_stack.py` |
| Quality configs | `ruff.toml`, `bandit.yaml`, `.coveragerc` (`fail_under = 74`) |
| Contract / memory | `AGENTS.md`, `decisions.md`, `mistakes.md` |
| Scaffold only | empty `engineering/{changes,adr,runbooks,reviews,contracts/*}` on consumers |

Not a database. Not a compose app.

### 2.2 Trust CI production compose — `trust-ci/compose.yaml`

Long-running / oneshot services:

| Service | Image env | Role |
| --- | --- | --- |
| `postgres` | `TRUST_CI_POSTGRES_IMAGE` (must be `name@sha256:`) | Durable PostgreSQL. Volume `trust-ci-postgres`. Init: `trust-ci/postgres/init/001_roles.sh`. |
| `migrate` | `TRUST_CI_API_IMAGE` | Oneshot `adaptive-trust-ci migrate`. Same API image. |
| `api` | `TRUST_CI_API_IMAGE` | FastAPI, `127.0.0.1:8080`. No Docker, no Git, no App key. |
| `docker-engine` | `TRUST_CI_DIND_IMAGE` | Privileged rootless DinD, TCP 2375 on `executor` network. |
| `runner-loader` | `TRUST_CI_WORKER_IMAGE` | Oneshot: pull/verify runner digest into DinD. |
| `worker` | `TRUST_CI_WORKER_IMAGE` | Claims jobs, checkout, holdout, sandbox, attestation, Checks API. |

Networks: `trust-ci`, `executor`. Volumes: `trust-ci-postgres`, `trust-ci-docker-data`, `trust-ci-workspaces`.

**No `build:` in production compose.** Builds are in `trust-ci/compose.build.yaml`.

### 2.3 Build override — `trust-ci/compose.build.yaml`

| Target | Dockerfile | Image tag |
| --- | --- | --- |
| `migrate` / `api` | `trust-ci/Dockerfile.api` | from `TRUST_CI_API_IMAGE` / untagged unless env sets it |
| `worker` | `trust-ci/Dockerfile.worker` | from `TRUST_CI_WORKER_IMAGE` |
| `runner-image` (`profiles: ["build"]`) | `trust-ci/runner.Dockerfile` | `TRUST_CI_RUNNER_BUILD_TAG` default `adaptive-trust-ci-runner:2.1.0` |

`Makefile` already merges both files:

```bash
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml config
docker compose -f trust-ci/compose.yaml -f trust-ci/compose.build.yaml --profile build build api worker runner-image
```

`trust-ci/README.md` and `engineering/runbooks/trust-ci-rollout.md` still say `docker compose --profile build build api worker runner-image` against `compose.yaml` alone. That **will not build**. QUICKSTART must not copy the stale command.

### 2.4 Test compose — `trust-ci/compose.test.yaml`

| Service | Role |
| --- | --- |
| `postgres-test` | Disposable Postgres with test role passwords. |
| `postgres-integration` | Test image (`Dockerfile.test`, default tag `adaptive-trust-ci-test:2.1.0`) running `test_postgres_integration.py`. |

Makefile / script exit code from **`postgres-integration`**, not `tests`. Stale runbook/README: `--exit-code-from tests`.

Scripts:

- `trust-ci/scripts/postgres-integration.sh`
- `trust-ci/scripts/postgres-restart-drill.sh`
- `make trust-ci-postgres-test`

### 2.5 Dockerfiles

| File | What it is |
| --- | --- |
| `trust-ci/Dockerfile.api` | `postgresql-client`, pip-installs `trust-ci/pyproject.toml`, uid 10001, `CMD api`. |
| `trust-ci/Dockerfile.worker` | `git` + `docker.io`, `CMD worker`. |
| `trust-ci/runner.Dockerfile` | `git php-cli composer nodejs npm` + pip `coverage==7.15.4 ruff==0.16.2 bandit==1.9.4 tomli==2.4.1`. Workdir `/workspace`. |
| `trust-ci/Dockerfile.test` | copies `src`, `tests`, `sql`; pip `.[test]`. |

All start `ARG PYTHON_BASE_IMAGE` / `FROM ${PYTHON_BASE_IMAGE}`. Locked by `trust-ci/tests/test_ops.py`.

### 2.6 PostgreSQL — the only database in this tree

No Redis, SQLite product store, Elasticsearch, ClickHouse, or MySQL.

SQL / init:

| Path | Role |
| --- | --- |
| `trust-ci/sql/001_schema.sql` (+ packaged `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql`) | `trust_ci_jobs`, `trust_ci_job_attempts`, `trust_ci_approvals`, `trust_ci_attestations`, plus events / `trust_ci_claim_job` (FOR UPDATE SKIP LOCKED). |
| `trust-ci/sql/002_operational_indexes.sql` | lease, terminal, approval expiry, attempt, attestation indexes. |
| `trust-ci/sql/003_database_roles.sql` | GRANT split: api / worker / backup / migrator. |
| `trust-ci/postgres/init/001_roles.sh` | Creates `trust_ci_api`, `trust_ci_worker`, `trust_ci_migrator`, `trust_ci_backup` at init. |

Logical database name in examples: `trust_ci` (prod) / `trust_ci_test` (harness).

Env templates (do not commit filled copies):

| File | DB-related vars |
| --- | --- |
| `trust-ci/env/postgres.env.example` | `POSTGRES_DB/USER/PASSWORD`, four role passwords |
| `trust-ci/env/api.env.example` | `TRUST_CI_DATABASE_URL` as `trust_ci_api@postgres:5432/trust_ci` |
| `trust-ci/env/worker.env.example` | `TRUST_CI_DATABASE_URL` as `trust_ci_worker@…` |
| `trust-ci/env/migration.env.example` | `TRUST_CI_DATABASE_URL` as `trust_ci_migrator@…` |
| `trust-ci/env/backup.env.example` | `TRUST_CI_BACKUP_DATABASE_URL` as `trust_ci_backup@…` |
| `trust-ci/env/common.env.example` | **no** DSN (policy path, public URL, kill-switch only) |

`.env.example` image pins (placeholders, not real digests):

```text
TRUST_CI_PYTHON_BASE_IMAGE=python:3.12-slim-bookworm@sha256:REPLACE_WITH_BASE_DIGEST
TRUST_CI_POSTGRES_IMAGE=postgres:17.6-bookworm@sha256:REPLACE_WITH_POSTGRES_DIGEST
TRUST_CI_DIND_IMAGE=docker:29-dind-rootless@sha256:REPLACE_WITH_DIND_DIGEST
TRUST_CI_API_IMAGE=registry.example.com/adaptive-trust-ci-api@sha256:REPLACE_WITH_API_DIGEST
TRUST_CI_WORKER_IMAGE=registry.example.com/adaptive-trust-ci-worker@sha256:REPLACE_WITH_WORKER_DIGEST
TRUST_CI_RUNNER_IMAGE=registry.example.com/adaptive-trust-ci-runner@sha256:REPLACE_WITH_RUNNER_DIGEST
```

### 2.7 Holdout, systemd, supply-chain, examples

| Path | Role |
| --- | --- |
| `trust-ci/holdout.example/validate.py` | Example external holdout (forbids GHA; requires App/worker split). |
| `trust-ci/config/policy.example.json` | Holdout digest locked by `test_ops.py`; runner image still a REPLACE digest. |
| `trust-ci/systemd/adaptive-trust-ci-compose.service` | `verify-supply-chain.sh` then `compose up` postgres/migrate/api/docker-engine/runner-loader/worker. |
| `trust-ci/systemd/adaptive-trust-ci-backup.service` + `.timer` | Daily `backup-create`. |
| `trust-ci/scripts/supply-chain-release.sh` | Requires host tools: `docker python3 trivy syft cosign sha256sum git`. SBOM via **syft**, vuln scan via **trivy image**, sign via **cosign**. **No grype.** |
| `trust-ci/scripts/verify-supply-chain.sh` | cosign + digest verify before start. |
| `trust-ci/env/supply-chain.env.example` | `TRUST_CI_SUPPLY_CHAIN_DIR`, `COSIGN_PUBLIC_KEY`. |
| `examples/bitrix-module/` | Reference D7 module. Install: `composer install && composer test`. |
| `examples/contracts/` | OpenAPI / AsyncAPI / JSON schema examples. Not a runtime DB. |

CLI entry: `adaptive-trust-ci` from `trust-ci/pyproject.toml` → `adaptive_trust_ci.cli:main`.

### 2.8 Host tools that actually exist as product checks vs those that only exist in Trust CI scripts

Local doctor (`toolchain.json`): Python, Git, Grok CLI, gh, Node, npm, PHP, Composer.

`grok_verify` optional scanners (not in toolchain.json): ruff, bandit, coverage, semgrep (signal), trivy-config (signal = root `Dockerfile`/`dockerfile`/`Containerfile` **or root** `docker-compose*.yml(l)`). This tree’s compose files live under `trust-ci/`, so **root `grok_verify` does not emit `trivy-config` today**. Do not add a root `docker-compose.yml` just to document Trust CI — that would start emitting `trivy-config` and fail-closed if `trivy` is installed and config-scan is dirty.

Trust CI supply-chain scripts additionally require **docker, trivy, syft, cosign**. **grype is not in this tree.** Do not add a grype pin unless a script actually calls it.

`scripts/grok_verify.py --mode pr` discovers **`tests/` only**, not `trust-ci/tests`. Holdout policy.example.json does run both discovers as sandbox commands.

---

## 3. QUICKSTART.md gaps vs Trust CI bootstrap and rollout

`QUICKSTART.md` is a 7-step **consumer** path: doctor → install Grok CLI → auth → `install_into` → `grok` → `/adaptive-delivery` → `grok_verify --mode pr` → `/hooks-trust`.

It does not mention Trust CI, PostgreSQL, Docker, images, holdout, GitHub App, backups, or examples.

### Missing sections (what the implementer should add)

Keep consumer steps 0–7. Then add an operator split so `install_into` consumers are not told to stand up Postgres on every laptop.

**A. Scope split (required prose)**

- Local stack install (`install_into`) does **not** deploy Trust CI and does not copy `trust-ci/`.
- Merge trust, when deployed, is the App-owned check. Local verify is preflight only.
- Delivery of **this** repository is PR-only on `feat/trust-ci-control-plane`. Do not `git push origin main`.

**B. Local quality tools (short)**

- `python3 scripts/grok_doctor.py --offer-install` (already step 0).
- Optional: ruff / bandit / coverage for `grok_verify --mode pr` (`fail_under` 74). These are not in `toolchain.json` today.

**C. Bitrix example app**

```bash
cd examples/bitrix-module
composer install
composer test
```

**D. Trust CI host prerequisites**

- Dedicated Linux CI host, Docker Engine, Compose v2.
- HTTPS reverse proxy (none is in-tree).
- Do not colocate privileged DinD with production workloads.

**E. PostgreSQL (the database)**

Copy templates, do not commit filled files:

```bash
cd trust-ci
mkdir -p runtime/control runtime/holdout
cp env/common.env.example env/common.env
cp env/api.env.example env/api.env
cp env/worker.env.example env/worker.env
cp env/migration.env.example env/migration.env
cp env/postgres.env.example env/postgres.env
cp env/backup.env.example env/backup.env
cp config/policy.example.json runtime/policy.json
cp config/trust-store.example.json runtime/trust-store.json
```

Explain: one logical DB `trust_ci`; four login roles created by `postgres/init/001_roles.sh`; schema from `sql/001_schema.sql` + `002_operational_indexes.sql` + `003_database_roles.sql` applied by `migrate`. Admin password ≠ API/worker/migrator/backup passwords.

Live harness (correct service name):

```bash
make trust-ci-postgres-test
# or
./trust-ci/scripts/postgres-integration.sh
./trust-ci/scripts/postgres-restart-drill.sh
```

**F. Build and pin images (correct command)**

```bash
docker compose -f compose.yaml -f compose.build.yaml --profile build build api worker runner-image
docker image inspect "$TRUST_CI_API_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_WORKER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
docker image inspect "$TRUST_CI_RUNNER_IMAGE" --format '{{.Id}} {{index .RepoDigests 0}}'
PYTHONPATH=src python3 -m adaptive_trust_ci.cli holdout-digest --path /absolute/reviewed/holdout
```

Do **not** copy README/runbook inspect of `adaptive-trust-ci-api:2.1.0` — `compose.build.yaml` does not set that tag for api/worker.

**G. Keys (split, never in git)**

- CI attestation key: worker-only (`adaptive-trust-ci keygen`).
- GitHub App RSA key: worker-only; API must not receive App ID / installation ID / key.
- Human Ed25519 approval key: **human workstation only**. Agent must not generate it.

**H. Start + health**

```bash
docker compose -f compose.yaml up -d postgres migrate api worker
# systemd unit also starts docker-engine + runner-loader
curl -fsS http://127.0.0.1:8080/health/ready
```

`/health/ready` stays 503 until Postgres is up **and** the trust store has an active human public key.

**I. Webhook, proof, then branch protection**

Copy the runbook order, not the handoff’s “update draft PR #2” as the first proof: code **ignores draft PRs**. Prove on a non-draft disposable docs PR, then consider `#2`. `branch-protect` only after the App-owned check exists.

**J. Backup / kill-switch / supply-chain**

- `adaptive-trust-ci backup-create` / `restore-drill --confirm-disposable` / systemd timer.
- `adaptive-trust-ci kill-switch on|off|status`.
- Operator-only: `trust-ci/scripts/supply-chain-release.sh --confirm-push` needs docker, trivy, syft, cosign.

**K. Pointer**

One line: full operator contract remains `trust-ci/README.md` + `engineering/runbooks/trust-ci-rollout.md`. QUICKSTART should still contain **working** commands for every app/DB, because those two files currently contain stale compose/test service names.

### Stale commands that QUICKSTART must not inherit

| Source | Stale | Use instead |
| --- | --- | --- |
| `trust-ci/README.md` Bootstrap / Verification | `docker compose --profile build build` on `compose.yaml` alone; `compose.yaml build api worker` | two-file merge + `--profile build` |
| same | inspect `adaptive-trust-ci-api:2.1.0` / `…-worker:2.1.0` | inspect `$TRUST_CI_*_IMAGE` |
| README + runbook | `--exit-code-from tests` | `--exit-code-from postgres-integration` or `make trust-ci-postgres-test` |
| Handoff | “four skipped Postgres tests” / prove on draft PR #2 first | eight `skipUnless` tests; non-draft disposable PR first |

---

## 4. Current dependency pins and which tests assert them

### Product identity

| Pin | Value | Asserted by |
| --- | --- | --- |
| `VERSION` | `2.0.11` | `test_structure.test_version_identity_matches_readme`; `test_manifest_package` hardcodes `'2.0.11'` twice |
| README H1 | `# Adaptive Grok Build Pro v2.0.11` | same |
| `.grok-stack/adaptive_grok/__init__.py` | `__version__ = "2.0.11"` | packaging/version tests historically; keep in sync if bumped |
| `trust-ci/pyproject.toml` + `trust-ci/src/adaptive_trust_ci/__init__.py` | `2.1.0` | not locked to product VERSION. Intentional independent service. |
| `packages/adaptive-grok-build-pro-v2.0.11.zip` | shipped zip | `test_manifest_package` if the zip exists |

Do **not** bump product VERSION just to document Trust CI. A docs/graph/pin-table change can stay `2.0.11` unless a release is explicitly in scope. If VERSION **is** bumped, also rewrite `test_manifest_package` literals, `__version__`, CHANGELOG, and rebuild the zip — or that test fails.

CHANGELOG 2.0.11 still claims AGENTS.md “names `git push origin main`”. Current `AGENTS.md` **forbids** direct push to `main`. That changelog line is historically stale; do not “fix” it by teaching QUICKSTART to push main.

### README Requirements table vs `.grok-stack/config/toolchain.json`

They currently match. Pins are **minimum or newer**; `built` is the tested pin.

| Tool id | Minimum | Built | Fallback | Required | Profile |
| --- | --- | --- | --- | --- | --- |
| python3 | 3.10 | 3.12.3 | 3.12 | yes | — |
| git | 2.34 | 2.43.0 | 2.43 | yes | — |
| grok | 1.0.0 | 1.0.4 | 1.0.4 | yes | tui |
| gh | 2.40 | 2.86.0 | 2.86 | no | release |
| node | 18.0 (README table says 18) | 24.19.0 | 20 | no | frontend |
| npm | 9.0 (README table says 9) | 11.17.0 | 10 | no | frontend |
| php | 8.1 | 8.2 | 8.2 | no | php |
| composer | 2.2 | 2.7 | 2.7 | no | php |

README table omits `id` and shows Node minimum as `18` vs JSON `18.0`. Harmless. **No test asserts README table rows equal toolchain.json.** Drift is easy.

### Toolchain schema — adding docker / postgres / syft / trivy / grype

There is **no JSON Schema file**. `adaptive_grok.toolchain.load_toolchain` loads `.grok-stack/config/toolchain.json` as a dict. `check_toolchain` iterates `data["tools"]` objects.

Per-tool keys actually used:

```text
id, name, required, profile, commands[], version_args[], built, minimum, fallback,
install.{linux,darwin,windows,generic}
```

`grok_doctor.run_doctor` appends one `DoctorItem` per tool (`tool:{id}`). Status `fail` only if `required` and missing/too old. Optional missing → `info`. `install_into.py` calls `pull_dependencies`; required tools install by default; `--no-deps` skips; `--all-deps` includes optional.

**Adding a new object to `tools[]` is supported** without code changes, if:

- `required: false` (or the tool is actually present on the doctor host);
- `install.linux` is a shell command, **not** a URL you expect `pull_dependencies` to execute (HTTP(S) → `manual-url`, never exec’d);
- `commands` are binaries `command_exists` can see (`docker`, `psql`, `syft`, `trivy`; Compose v2 is `docker compose`, so pin **docker**, not a fake `docker-compose` id, unless a standalone binary exists).

Tests that matter:

| Test | Effect of new tools |
| --- | --- |
| `test_toolchain.test_real_toolchain_json_required_and_optional_sets` | Only asserts python3/git required and php/gh/node optional. **Adding ids is fine.** Does not assert closed set or length. |
| `test_toolchain.test_optional_missing_does_not_fail_doctor` | Fails if any **required** tool is missing on the doctor host. **Do not mark docker/postgres/syft/trivy/cosign required** or consumer `install_into` / `make doctor` goes red. |
| installer tests | Mock `check_toolchain`; they do not freeze the catalog. |
| `test_this_repo_shaped_tree_omits_bucket_b` | Unrelated to toolchain.json. Breaks if a **root** Dockerfile / docker-compose appears. |

**Recommendation for toolchain rows (all `required: false`):**

| id | profile | Why | Notes |
| --- | --- | --- | --- |
| docker | `trust-ci` | Compose / DinD / supply-chain | Measure `built` from the CI host; do not invent. |
| (optional) psql | `trust-ci` | `postgresql-client` for backup/debug | Server is the compose image, not a host package. |
| syft | `supply-chain` | `supply-chain-release.sh` | Script requires it; doctor should offer it. |
| trivy | `supply-chain` | same | Also used by `grok_verify` trivy-config **if** a root Docker signal exists. |
| cosign | `supply-chain` | sign/verify | In the script; user asked syft/trivy/grype but cosign is the actual third tool. |
| **grype** | — | **Not in tree** | Do **not** add. Trivy is the vuln scanner. Adding grype would document a non-app. |
| ruff | `quality` | `grok_verify` + runner pin `0.16.2` | Optional; runner Dockerfile already pins it. |
| bandit | `quality` | pin `1.9.4` | same |
| coverage | `quality` | pin `7.15.4`; fail-under 74 | same |

If `built` is updated for existing tools, also update the README Requirements table (no test will catch a mismatch). Re-measure; do not copy this report’s numbers as “updated” unless doctor was run on the ship host.

### Other lock / pin files

| File | Pins | Tests |
| --- | --- | --- |
| `trust-ci/pyproject.toml` | `setuptools==84.0.0`; runtime `cryptography==46.0.4`, `fastapi==0.128.2`, `psycopg[binary]==3.3.4`, `uvicorn==0.48.0`; test `httpx==0.28.1`; `requires-python = ">=3.11"` | `trust-ci/tests/test_ops.py::test_runner_tools_and_build_backend_are_exactly_pinned` locks setuptools exact (no `>=`) |
| `trust-ci/runner.Dockerfile` | `coverage==7.15.4 ruff==0.16.2 bandit==1.9.4 tomli==2.4.1` | same test, string-in-file |
| `ruff.toml` | `target-version = "py310"`, line-length 120 | exercised by grok_verify, not version-asserted |
| `bandit.yaml` | skips B101/B404/B603/B607 | same |
| `.coveragerc` | `fail_under = 74` | adapter tests fail-closed on coverage non-zero; **74 is not hardcoded in Python** |
| `trust-ci/.env.example` | image **names** postgres 17.6, python 3.12 slim, docker 29 dind-rootless; digests REPLACE | ops tests require digest-shaped production compose |
| `trust-ci/config/policy.example.json` | runner `…@sha256:REPLACE_WITH_IMMUTABLE_RUNNER_DIGEST`; holdout digest locked to `holdout.example` | `test_structure.test_trust_ci_policy_uses_immutable_sandbox_and_external_status`; `test_ops.test_example_holdout_digest_matches_example_bundle` |
| `trust-ci/tests/test_supply_chain.py` | asserts scripts contain `trivy image`, `syft`, `cosign sign` | adding toolchain rows is independent of this |

No root `pyproject.toml` / `requirements.txt` / `setup.py` (locked absent by `test_root_has_no_packaging_marker`).

---

## 5. Control-plane / protected files and grants

Local policy is a usability guardrail, not merge authority. Structured writes to protected paths need an exact `protected-path-write` grant bound to repo/route/change/HEAD/tree. Shell mutation of control-plane paths is blocked even with a path grant (`test_control_plane_shell_mutation_is_blocked_even_with_path_grant`).

### In both `policy.json` and `policy.py` DEFAULT_CONTROL_PLANE / DEFAULT_PROTECTED

| Path | Protected? | Control-plane (shell mutation)? | Grant to edit |
| --- | --- | --- | --- |
| `README.md` | yes | yes | `--scope protected-path --action protected-path-write --resource README.md` |
| `CHANGELOG.md` | yes | yes | same, `CHANGELOG.md` |
| `VERSION` | yes | yes | `VERSION` |
| `tests/test_*.py` | yes (glob) | yes | exact file, e.g. `tests/test_structure.py` |
| `.grok-stack/**` | yes | yes | exact file, e.g. `.grok-stack/config/toolchain.json` |
| `AGENTS.md`, `decisions.md`, `mistakes.md` | yes | yes | exact file |
| `trust-ci/**` | yes | yes | exact file under `trust-ci/` |
| `scripts/grok_*.py`, `scripts/install_into.py` | yes | yes | exact file |

`policy.json` additionally protects `packages/**` (not in `DEFAULT_CONTROL_PLANE`).

### `QUICKSTART.md` is **not** protected today

It is absent from `control_plane_paths`, `protected_paths`, and `DEFAULT_CONTROL_PLANE`. A `Write`/`Edit` of `QUICKSTART.md` does not need a grant.

If the implementer wants QUICKSTART treated like README, they must add `"QUICKSTART.md"` to **both** lists in `.grok-stack/config/policy.json` **and** `DEFAULT_CONTROL_PLANE` in `.grok-stack/adaptive_grok/policy.py` (those Python files are themselves protected). Then `test_local_policy_protects_control_plane` only checks a subset (`.github/**`, `.grok/**`, `.grok-stack/**`, `AGENTS.md`, `trust-ci/**`, grok_verify script) — adding QUICKSTART does **not** require changing that test unless they want it locked.

### Trust CI external approval globs (`trust-ci/config/policy.example.json`)

`README.md`, `QUICKSTART.md`, `VERSION`, `CHANGELOG.md` are **not** in the example `governance` globs. `tests/test_structure.py` **is**. `trust-ci/**` is governance. `**/*.sql` is `database`. Compose/Dockerfiles are `production`.

So: a docs-only README/QUICKSTART PR may **not** need a human Ed25519 governance approval under the **example** policy; a `tests/test_structure.py` or `toolchain.json` change **does** (`toolchain.json` is under `.grok-stack/**` → governance). Confirm against the **deployed** policy, not only the example.

### Evidence path for this report

`engineering/changes/**` is not a protected glob (except `engineering/runbooks/publish-v*.md`). This file is workflow evidence, not merge authority.

### Delivery / push grants (out of this analysis)

- Direct `git push origin main` is forbidden by AGENTS.md and `test_merge_trust_is_external_and_pr_only`.
- A later `git-push-branch` grant may name `feat/trust-ci-control-plane` only if the user explicitly delegates that action. This docs analysis does not authorize it.
- Local grants cannot create `adaptive-trust-ci/verified`.

---

## 6. Do not commit `engineering/changes/20260817-user-query-вычисти-*`

That package (`20260817-user-query-вычисти-и-оставь-только-2-0-10-в-гите-33e0c2`) is a 2.0.10 working-tree cleanup ruling: restore dirty `state.json`, delete untracked leftover evidence, **do not create a new commit**. It is unrelated to Trust CI docs/graph work. Committing it would mix abandoned cleanup paperwork into the control-plane PR. Leave it untracked or ignore it.

Also: do not push `main`. Ship docs through `feat/trust-ci-control-plane` and the existing draft PR.

---

## Return block (for the write owner)

### Node list recommendation for the rebuilt complete K-graph

**Pick K16 as the single first mermaid fence** so “every listed core node” includes the applications and the database that now exist, and every pair is a `---` edge (\(C(16,2)=120\)).

Exact vertex IDs (use these strings in mermaid and in the structure-test `nodes` list):

```text
Route
Skills
Agents
Hooks
Policy
Verify
Packages
Contract
Decisions
Mistakes
TrustAPI
TrustWorker
Postgres
Runner
Holdout
GitHubApp
```

Suggested labels (do not change the IDs):

```text
Contract["AGENTS.md"]
Decisions["decisions.md"]
Mistakes["mistakes.md"]
TrustAPI["trust-ci API"]
TrustWorker["trust-ci worker"]
Postgres["PostgreSQL 17"]
Runner["isolated runner"]
Holdout["external holdout"]
GitHubApp["GitHub App Checks"]
```

Oneshots `migrate` and `runner-loader` share API/worker images — node-role table footnotes, not extra vertices. Rootless DinD is an edge of Runner, not a 17th node (K17 = 136 edges).

Emit edges with:

```python
for left, right in itertools.combinations(nodes, 2):
    print(f"  {left} --- {right}")
```

120 lines, no duplicates, no `-->`.

Caption to replace the “Trust CI is outside this graph” sentence: local workflow plus the independently deployed Trust CI applications and PostgreSQL; prompts still are not merge authority.

**Lower-risk alternative if 120 edges is rejected:** keep first fence K10 (existing test untouched) and add a second complete fence K8: `TrustAPI TrustWorker Postgres Runner Holdout GitHubApp PolicyEpoch BranchProtect` (28 edges) plus a new test on fence #2. That is two complete graphs, not one rebuilt clique. Record the choice in `decisions.md`.

### QUICKSTART sections to add

1. Consumer vs operator split (`install_into` does not install Trust CI).
2. PR-only delivery; no push to `main`.
3. Bitrix example: `composer install && composer test`.
4. Trust CI host: Docker Engine + Compose v2, dedicated host.
5. Postgres: env templates, four roles, migrate, `make trust-ci-postgres-test` + restart drill.
6. Image build with **two-file compose merge**; inspect `$TRUST_CI_*_IMAGE`; holdout-digest.
7. Key split (CI / App / human).
8. `docker compose up -d postgres migrate api worker` + `/health/ready`.
9. Webhook on a **non-draft** disposable PR, then branch-protect.
10. Backup, kill-switch, supply-chain (syft/trivy/cosign — not grype).
11. Pointer to `trust-ci/README.md` and the rollout runbook, with the stale-command corrections applied in the copied snippets.

### Toolchain rows to add / update

Add, all `required: false`:

- `docker` profile `trust-ci`
- `syft` profile `supply-chain`
- `trivy` profile `supply-chain`
- `cosign` profile `supply-chain` (actual tree tool; user said grype — **omit grype**)
- optional `psql` profile `trust-ci`
- optional `ruff`, `bandit`, `coverage` profile `quality` (align `built` with runner pins 0.16.2 / 1.9.4 / 7.15.4 after measuring host)

Update existing README table only if `built` values are re-measured. Keep python3/git required. Do not make Docker required.

### Tests to change

Must change if the first mermaid fence grows:

- `tests/test_structure.py` `test_readme_local_stack_graph_is_complete_k10` — node list + edge count (120 for K16). Prefer `assertEqual(len(edge_lines), len(list(itertools.combinations(nodes, 2))))`.

Optional:

- Same file: require `QUICKSTART.md` in `test_core_product_files_exist`.
- `tests/test_toolchain.py`: assert new ids exist and `required is False` (prevents someone marking docker required).
- `tests/test_manifest_package.py` **only if VERSION changes**.

Do not add a root Dockerfile/compose just for docs (`test_this_repo_shaped_tree_omits_bucket_b` / live `trivy-config`).

### Files to touch (write owner)

| File | Grant |
| --- | --- |
| `README.md` | protected-path-write `README.md` |
| `QUICKSTART.md` | none today |
| `tests/test_structure.py` | protected-path-write `tests/test_structure.py` |
| `.grok-stack/config/toolchain.json` | protected-path-write `.grok-stack/config/toolchain.json` |
| `tests/test_toolchain.py` | if asserting new ids |
| `decisions.md` | if recording the K16 vs dual-graph ruling |
| `CHANGELOG.md` / `VERSION` / `__init__.py` | **only** if identity bump (not required for this docs pass) |
| `trust-ci/README.md` + `engineering/runbooks/trust-ci-rollout.md` | recommended so QUICKSTART does not fork stale compose commands; both are protected (`trust-ci/**`, runbook is not `publish-v*` so the runbook may **not** be in control_plane — check: `engineering/runbooks/trust-ci-rollout.md` is **not** in protected_paths). Runbook is writable without grant; `trust-ci/README.md` needs grant. |

Do **not** touch: `.env`, `trust-ci/env/*.env`, `trust-ci/runtime/**`, keys, `engineering/changes/20260817-user-query-вычисти-*`, `.github/`.

### Residual risks

- 120-edge mermaid is unreadably dense; dual-graph is more usable but needs a second test + AGENTS.md wording if adopted.
- `trust-ci/README.md` / rollout still teach commands that fail; copying them into QUICKSTART ships a broken install path.
- Product `2.0.11` vs Trust CI `2.1.0` will look like a docs bug unless README Current state names both identities.
- Example policy runner digest is still REPLACE; documenting “pin the digest” is correct, inventing a digest is not.
- Making docker/syft/trivy `required: true` breaks `make doctor` / `install_into` on machines without those binaries (`test_optional_missing_does_not_fail_doctor`).
- Adding grype documents a scanner the tree does not run.
- `QUICKSTART.md` is unprotected; an implementer can edit it without a grant, then a later policy tightening would surprise.
- `tests/test_structure.py` and `.grok-stack/config/toolchain.json` are Trust CI **governance** globs; the deployed runner will `needs_approval` until a human Ed25519 envelope exists. README/QUICKSTART alone may not.
- Draft PR #2 still will not enqueue jobs; docs that say “push this branch and the check appears” are false until the PR is non-draft or a disposable non-draft PR is used.
- Local receipts / this evidence file / delegated grants are not merge authority.
- Direct push to `main` remains prohibited regardless of how complete the graph is.

---

Route `2335b3d0d9fc` analysis complete. Write owner is `general_implementer`. Review after implementation: `code_reviewer` only (this micro docs route).
