# M4 implementation report

## Result

M4 is implemented as a separate local `factory/` package on accepted M3 base `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`. It validates immutable M1/M2/M3/M0-bound intake, persists isolated PostgreSQL operational truth, schedules fenced bounded leases, and exposes authenticated scoped control over an explicit Unix socket. It has no provider execution, repository command, GitHub/external write, deployment, systemd, production or Trust CI authority.

## Delivered behavior

- Closed typed intake, handoff, actor, task, run, attempt and limit records with canonical digests, exact duplicate return and atomic supersession.
- Four contiguous checksum-locked factory migrations, isolated `NOLOGIN` roles and no `trust_ci` privileges.
- Transactional `FOR UPDATE SKIP LOCKED` claims, monotonic per-task fences, database-time leases/deadlines and 20 global readers / 10 per repository / one writer capacity.
- Initial attempt plus two infrastructure retries, terminal dead/needs-human handling, 14,400-second and USD 25/token/output/event/repair ceilings, durable fail-closed missing accounting and idempotent usage observations.
- Global/repository kills, append-only hash-chained audit with bounded verification, and ordered reconciliation capped at 100 candidates and five seconds.
- Constant-time scoped bearer authentication, repository authorization, bounded/redacted errors, 1 MiB body limit, checked-in OpenAPI, and CLI health/intake/show/list/cancel/claim/heartbeat/proposal/kill/reconcile over Unix HTTP only.
- Architecture model/rules/diagrams, K17 README graph, roadmap/status, installer inventory, verifier integration, release and forward-recovery documentation.

## Commits

- `6c7aa3f` — freeze accepted M4 scope and exact-base package.
- `8ca3bca` — closed factory contracts.
- `abfdcaa` — closed task state/retry policy.
- `3d395a2` — durable migration foundation.
- `149424e` — PostgreSQL store, intake, leases, capacity and reconciliation.
- `c7bdb91` — scoped local API/CLI.
- `6a75ae3` — isolated executable architecture model.
- `1924cb2` — bounded delivery/docs/installer/verifier/accounting completion.
- `39dafa4` — exact verification-gate repairs.

## Verification evidence

- Factory suite: 30/30 passed against fresh disposable PostgreSQL 17 in 7.046 seconds after the final migration checksum.
- Restart probe: expired holder reclaimed once, higher fence issued, late heartbeat rejected.
- Architecture model/fitness: 131/131 passed; validate, drift, diagram check and full worktree fitness passed.
- Former root-verifier regressions: all 15 targeted failures passed; API/contract/state/migration/service unit subset 25/25 passed.
- Secret scan: zero findings. Ruff and Bandit: passed.
- The first root verifier failure and every bounded correction are recorded in `implementation-ledger.md`. The final `python3 scripts/grok_verify.py --mode pr` runs after this report is committed so its fingerprint-bound receipt, rather than mutable prose, records the exact-tree verdict.

## Disposable migration evidence and cleanup

Only the exact local container `m4-factory-pg-b7f288` and its fresh `m4_factory_final` database were mutated. After the final PostgreSQL suite the exact container was removed; its disposable data is not recoverable, and no other container, shared database, Trust CI state, external system or production resource was touched.

## Rollout, rollback and remaining authority

Source rollout only: no service was activated and no migration was run outside the disposable database. Recovery after durable intake is global kill, stop local intake/claims, preserve audit/state, restore backup into a separate comparison database and forward-fix with migration `005+`; destructive down-migration is prohibited.

Independent route reviews, PR delivery, the App-owned policy-epoch check on the exact PR head, signed approval scopes, merge and any deployment remain outside this implementation report and are not claimed here. The calendar deadline does not change the product runtime contract or bypass those gates.
