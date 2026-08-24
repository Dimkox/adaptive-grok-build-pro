# Analysis: M0 (live Trust CI) vs M1 (typed change spec)

Route: `5a2a54f045d1`. Change: `20260823-user-query-погнал-всё-исполнять-я-спать-где-потр-5a2a54`. HEAD: `d8cf1a1` on `docs/dark-factory-roadmap`. Authority: `DARK_FACTORY_ROADMAP.md` plus in-tree files. GitHub App install, live Check Run, and branch protection are **not** in git and were not queried.

## Presence of named M1 / factory paths

| Path | Present |
| --- | --- |
| `schemas/` (repo root) | **No** |
| `factory/` | **No** |
| `scripts/grok_spec.py` | **No** |
| `change-spec.yaml` (any) | **No** |
| `schemas/change-spec.schema.json` | **No** |
| `.grok-stack/templates/change/change-spec.yaml` | **No** |
| `.grok-stack/adaptive_grok/spec.py` | **No** |
| `tests/test_change_spec.py` | **No** |
| `trust-ci/holdout.example/change_spec_validate.py` | **No** |

Related but not M1: empty `engineering/contracts/schemas/` and `examples/contracts/schemas/order-changed.v1.json` (example event schema, not change-spec).

Durable change templates today (Markdown + `state.json` only):

- `.grok-stack/templates/change/architecture.md`
- `.grok-stack/templates/change/brief.md`
- `.grok-stack/templates/change/evidence/README.md`
- `.grok-stack/templates/change/release.md`
- `.grok-stack/templates/change/requirements.md`
- `.grok-stack/templates/change/rollback.md`
- `.grok-stack/templates/change/state.json`
- `.grok-stack/templates/change/tasks.md`
- `.grok-stack/templates/change/test-plan.md`

## M0 — in-repo Trust CI source (implemented; live proof not in git)

Roadmap M0 surfaces `trust-ci/`, `engineering/runbooks/trust-ci-rollout.md`, plus **external** GitHub App / webhook / `main` protection / CI host. Source tree:

### Compose, images, holdout, policy examples

- `trust-ci/compose.yaml`
- `trust-ci/compose.build.yaml`
- `trust-ci/compose.test.yaml`
- `trust-ci/Dockerfile.api`
- `trust-ci/Dockerfile.worker`
- `trust-ci/Dockerfile.test`
- `trust-ci/runner.Dockerfile`
- `trust-ci/.dockerignore`
- `trust-ci/pyproject.toml`
- `trust-ci/README.md`
- `trust-ci/.env.example`
- `trust-ci/config/policy.example.json`
- `trust-ci/config/trust-store.example.json`
- `trust-ci/env/api.env.example`
- `trust-ci/env/backup.env.example`
- `trust-ci/env/common.env.example`
- `trust-ci/env/migration.env.example`
- `trust-ci/env/postgres.env.example`
- `trust-ci/env/supply-chain.env.example`
- `trust-ci/env/worker.env.example`
- `trust-ci/holdout.example/validate.py`

### SQL, systemd, ops scripts

- `trust-ci/sql/001_schema.sql`
- `trust-ci/sql/002_operational_indexes.sql`
- `trust-ci/sql/003_database_roles.sql`
- `trust-ci/postgres/init/001_roles.sh`
- `trust-ci/systemd/adaptive-trust-ci-backup.service`
- `trust-ci/systemd/adaptive-trust-ci-backup.timer`
- `trust-ci/systemd/adaptive-trust-ci-compose.service`
- `trust-ci/scripts/postgres-integration.sh`
- `trust-ci/scripts/postgres-restart-drill.sh`
- `trust-ci/scripts/restore-drill.sh`
- `trust-ci/scripts/smoke.sh`
- `trust-ci/scripts/supply-chain-release.sh`
- `trust-ci/scripts/verify-supply-chain.sh`

### Python package (`adaptive_trust_ci`)

- `trust-ci/src/adaptive_trust_ci/__init__.py`
- `trust-ci/src/adaptive_trust_ci/api.py`
- `trust-ci/src/adaptive_trust_ci/backup.py`
- `trust-ci/src/adaptive_trust_ci/cli.py`
- `trust-ci/src/adaptive_trust_ci/github.py`
- `trust-ci/src/adaptive_trust_ci/github_app.py`
- `trust-ci/src/adaptive_trust_ci/holdout.py`
- `trust-ci/src/adaptive_trust_ci/lease.py`
- `trust-ci/src/adaptive_trust_ci/lookup.py`
- `trust-ci/src/adaptive_trust_ci/metrics.py`
- `trust-ci/src/adaptive_trust_ci/migrations.py`
- `trust-ci/src/adaptive_trust_ci/models.py`
- `trust-ci/src/adaptive_trust_ci/policy.py`
- `trust-ci/src/adaptive_trust_ci/runner.py`
- `trust-ci/src/adaptive_trust_ci/sandbox.py`
- `trust-ci/src/adaptive_trust_ci/settings.py`
- `trust-ci/src/adaptive_trust_ci/signing.py`
- `trust-ci/src/adaptive_trust_ci/store.py`
- `trust-ci/src/adaptive_trust_ci/webhooks.py`
- `trust-ci/src/adaptive_trust_ci/worker.py`
- `trust-ci/src/adaptive_trust_ci/workspace.py`
- `trust-ci/src/adaptive_trust_ci/resources/__init__.py`
- `trust-ci/src/adaptive_trust_ci/resources/001_schema.sql`
- `trust-ci/src/adaptive_trust_ci/resources/002_operational_indexes.sql`
- `trust-ci/src/adaptive_trust_ci/resources/003_database_roles.sql`

### Tests

- `trust-ci/tests/__init__.py`
- `trust-ci/tests/_support.py`
- `trust-ci/tests/postgres_restart_probe.py`
- `trust-ci/tests/test_api.py`
- `trust-ci/tests/test_backup.py`
- `trust-ci/tests/test_database_roles.py`
- `trust-ci/tests/test_github_app.py`
- `trust-ci/tests/test_key_rotation.py`
- `trust-ci/tests/test_metrics.py`
- `trust-ci/tests/test_migrations.py`
- `trust-ci/tests/test_ops.py`
- `trust-ci/tests/test_policy.py`
- `trust-ci/tests/test_postgres_integration.py`
- `trust-ci/tests/test_runner.py`
- `trust-ci/tests/test_signing.py`
- `trust-ci/tests/test_store.py`
- `trust-ci/tests/test_supply_chain.py`
- `trust-ci/tests/test_webhooks_github.py`

### Docs / runbooks / prior plans (M0-related, not live proof)

- `engineering/runbooks/trust-ci-rollout.md` (compose health curl uses `http://127.0.0.1:8080/health/ready`; **port 8080 is SearXNG on this host**, not Trust CI)
- `engineering/runbooks/protected-control-plane-write.md`
- `engineering/reviews/trust-ci-p0-local-verification.md`
- `docs/superpowers/plans/2026-08-23-trust-ci-control-plane.md`
- `docs/superpowers/plans/2026-08-23-trust-ci-operations-hardening.md`
- `docs/superpowers/specs/2026-08-23-trust-ci-control-plane-design.md`
- `DARK_FACTORY_ROADMAP.md` (M0/M1 definitions)

### Untracked GHCR pin (not merge evidence)

- `build/adaptive-trust-ci-pin.env` — **not in git** (`git ls-files` miss). Contains digest pins:
  - `ghcr.io/dimkox/adaptive-trust-ci-api@sha256:70a80960486b6008dac2dfe2ffc8e0b8e28f7ed8c03c52e673188fdb11207b23`
  - `ghcr.io/dimkox/adaptive-trust-ci-worker@sha256:bffd013ce1510bda55c74fa7926647f0000c3fc84dbd55114f36ea74b5f62227`
  - `ghcr.io/dimkox/adaptive-trust-ci-runner@sha256:900cfaaa49f1e6d9e6e7f0077ed1c481816ba639f17bb9065983c7279c291cb2`
- Image push ≠ live Check Run, App install, or branch protection.

### Explicitly unread / not inferable from git

- `trust-ci/runtime/` (operator secrets; `github-app-private-key.pem` listed by dir walk — **not read**)
- GitHub App installation, App ID, installation ID
- webhook delivery to `/webhooks/github`
- live Check Run `adaptive-trust-ci/verified@<policy-sha12>` on a PR SHA
- `main` branch protection response
- deployed policy/holdout digests, HTTPS endpoint, PostgreSQL operator state

Roadmap §3.3 and M0 exit criteria remain **operational**, not source. M0 live proof is **blocked from this repository snapshot**.

## M1 — missing; Markdown change packages only

M1 recommended files (roadmap §M1) are all absent. Existing local workflow (`engineering/changes/**`, `scripts/grok_change.py`, `.grok-stack/adaptive_grok/change.py`) is Markdown-first. This change package has no `change-spec.yaml`.

## Bootstrap note

Roadmap: M1 may start only after M0 live proof **or** a documented user bootstrap exception. User auto-approval of interventions is chat consent, not Trust CI / branch-protection proof.

## First in-repo implementable files for M1 if M0 live proof is blocked

Create these first (schema + template + library + CLI + tests; holdout later):

1. `schemas/change-spec.schema.json`
2. `.grok-stack/templates/change/change-spec.yaml`
3. `.grok-stack/adaptive_grok/spec.py`
4. `scripts/grok_spec.py`
5. `tests/test_change_spec.py`

Then package copy: `engineering/changes/<id>/change-spec.yaml`. Defer `trust-ci/holdout.example/change_spec_validate.py` and attestation digest fields until M0 holdout/deploy is real. Do **not** create `factory/` (M4).
