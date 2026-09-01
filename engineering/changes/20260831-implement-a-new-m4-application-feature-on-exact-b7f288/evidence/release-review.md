# Release review — round 3

## Verdict and binding

**FAIL — NO-GO for local source release.**

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `8435e23458885a48e2d5784f8cd01e84d978c28c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c`
- Exact-head verification fingerprint: `7f5f5a2c7eb5985b7b83643fee8158aba5a5fc4693eba826f58d9e9e1d519f70`
- Critical findings: 0
- Important findings: 2
- Moderate findings: 1

The implementation materially closes all six prior release-review blockers. It is still a no-go because the effective runtime role can insert a repository capacity counter with an arbitrary policy ceiling and make the supported scheduler grant reader 11, and because the root README says the candidate has five migrations while the release tree contains six. The exact-head security review therefore also returns FAIL, and the route's all-review release gate cannot pass.

Do not record a passing `release_review` receipt for this head.

## Severity-ordered findings

### Important — I-1: `factory_runtime` can bypass the hard 10-reader repository ceiling through INSERT

Migration 003 grants table-level INSERT on `factory.capacity_counters` to `factory_runtime` (`factory/src/adaptive_factory/resources/003_budgets_kills_reconciliation.sql:48-53`). Migration 006 revokes table UPDATE and restores only `active_count` UPDATE (`factory/src/adaptive_factory/resources/006_runtime_policy_privileges.sql:1-2`), but it leaves INSERT intact. The schema accepts every positive ceiling (`factory/src/adaptive_factory/resources/002_runs_leases_capacity.sql:38-43`). Claim inserts ceiling 10 only if the row is absent, then trusts the persisted ceiling for admission (`factory/src/adaptive_factory/store.py:423-464`).

The exact-head security reviewer demonstrated under effective `factory_runtime` that an INSERT of `repository:probe/repo:reader` with ceiling `999` succeeds and that 11 ordinary tasks for the same repository can then be claimed through `FactoryService`. The checked-in privilege regression tests UPDATE denial but never attempts the policy-bearing INSERT (`factory/tests/test_postgres_integration.py:608-654`).

Impact: a compromised runtime credential, a future SQL-injection defect, or an unintended runtime statement can change scheduler policy without migrator authority. This violates the advertised/database-authoritative 20/10/1 limits (`factory/README.md:3`, `requirements.md:8`, `change-spec.yaml:18`) and can overcommit repository-local resources during rollout. Readiness and metrics would still report normally because neither validates canonical counter ceilings.

Required repair: make ceilings schema-authoritative. Constrain/trigger exact values (`global:reader=20`, `global:writer=1`, `repository:*:reader=10`) or revoke direct INSERT and expose a narrowly scoped function that creates canonical repository rows. Add an effective-role arbitrary-INSERT denial and an end-to-end malformed/preseeded-counter test proving reader 11 is impossible.

### Important — I-2: README current-state migration inventory is stale

`README.md:13` says M4 has “five isolated checksum PostgreSQL migrations,” while the exact tree ships contiguous migrations `001` through `006`, including `005_security_accounting_commands.sql` and `006_runtime_policy_privileges.sql`. `factory/README.md:18` and rollback guidance correctly describe migrations 005, 006, and future `007+`, so the root current-state statement is the inconsistent one.

Impact: the repository contract forbids proposing a release when README current state is behind the tree. An operator using the root status as inventory could expect schema version 5 while dependency-aware readiness requires exactly version 6 (`factory/src/adaptive_factory/store.py:61-65`). Change “five” to “six” and retain the exact migration/version parity test before the next review round.

### Moderate — M-1: transferable installer omits the verified dependency lock and exit harness

The installer correctly transfers the server, actor template, contracts, runtime source, and all six migrations through its managed `factory/src` tree (`scripts/install_into.py:17-30`). It intentionally excludes `factory/tests`, and it also omits `factory/uv.lock`. The exact-head verifier's mandatory exit uses both the test runner and `uv --project factory`, but an installed target receives neither the exit harness nor the locked transitive dependency graph.

This does not create an external-write path and direct runtime dependencies remain exactly pinned in `factory/pyproject.toml:1-9`; however, the transferred package cannot reproduce the same P0 verification/dependency closure as the reviewed repository. Before an installed-target activation is proposed, either ship the lock and an appropriate verification artifact or explicitly document that exact source-repository verification and separately built immutable artifacts are prerequisites.

## Prior blocker recheck

| Prior blocker | Round-3 result | Evidence |
| --- | --- | --- |
| UDS composition/start path | **Closed** | `adaptive-factory-server` is installed (`factory/pyproject.toml:11-13`); it builds store/service/authenticator, pre-binds only `AF_UNIX`, validates ownership/path safety, applies `0660`, and passes only that socket to Uvicorn (`factory/src/adaptive_factory/server.py:73-121`). Actor and token files are bounded, no-follow mode `0600` inputs. |
| Cancel/supersede capacity leak | **Closed** | `_close_active_lease` atomically locks and releases the run/allocation and decrements counters; orphan repair is isolated and idempotent (`factory/src/adaptive_factory/store.py:532-605`). Exact-head PostgreSQL receipt passes cancel/supersede and two-pass reconciliation tests. |
| Effective database roles | **Closed except I-1 policy INSERT** | Every store connection executes `SET ROLE factory_runtime` (`factory/src/adaptive_factory/store.py:45-59`); readiness reports that effective role and schema 6. Migration 006 narrows UPDATE privileges, but I-1 remains. |
| Readiness, metrics, runbook | **Closed** | `/health/ready` checks database/effective role/schema and returns 503 on failure; authenticated `/metrics` exposes the three declared bounded families (`factory/src/adaptive_factory/api.py:128-145`, `factory/src/adaptive_factory/store.py:61-87`). Release and rollback now name backup restore, schema/role checks, UDS mode, synthetic accounting flow, actual restart, two-pass reconciliation, owner evidence and forward migration `007+` (`release.md:3-7`, `rollback.md:3-5`). |
| Verifier inclusion | **Closed** | PR/release verification mandates `factory/tests/run_disposable_exit.py` (`.grok-stack/adaptive_grok/verification.py:574-599`). The exact-head receipt passed 42 API/PostgreSQL/effective-role tests plus an actual restart/reconcile probe. |
| Rollback version | **Closed** | Current schema is 006 and recovery consistently names migration `007+` (`factory/README.md:18,30-34`, `rollback.md:5`, `architecture.md:31`). |

## README, packaging, and no-external-write assessment

- Product identity remains `2.0.12`; the identity test passed (`README.md:1,7`, `VERSION`).
- The K17 stack graph still has all 136 pairwise `---` edges including Factory; `test_readme_stack_graph_is_complete` passed (`README.md:91-263`).
- Installer inventory tests passed and include `actors.example.json`, server source, OpenAPI, and migrations through 006; credentials, sockets, database state, and factory tests are excluded.
- `factory/uv.lock` supplies an exact dependency solution in the source repository, but M-1 applies to transferred installs.
- Static inspection of exact-head `factory/src/adaptive_factory` found no provider execution, shell/subprocess, repository/Git/GitHub client, systemd, deployment, TCP listener, production mutation, or Trust CI write path. The only server socket family is `AF_UNIX`; the CLI uses explicit HTTP-over-UDS.
- The sample PostgreSQL port is loopback-only (`factory/compose.yaml:8-9`), and source delivery activates nothing. The verification runner's Docker/PostgreSQL writes are bounded to a randomized disposable local container and are not product runtime behavior.
- No external write, merge, deployment, publication, tag, production database mutation, or Trust CI mutation was performed by this review.

## Verification and review evidence

```text
git rev-parse HEAD
8435e23458885a48e2d5784f8cd01e84d978c28c

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..8435e23458885a48e2d5784f8cd01e84d978c28c
PASS (no output)

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
PASS — 30/30

python3 -m unittest tests.test_installer tests.test_structure -v
PASS — 32/32

exact-head .grok-stack/runtime/receipts/b7f288f1e81e/verification.json
PASS — fingerprint 7f5f5a2c7eb5985b7b83643fee8158aba5a5fc4693eba826f58d9e9e1d519f70;
485 root tests, 21 factory unit tests, 42 disposable API/PostgreSQL/effective-role tests,
actual PostgreSQL restart/reconciliation, architecture/governance/contracts/SQL safety,
Ruff, Bandit, secret scan, coverage, diff check, and source stability passed.

exact-head security review empirical probes
factory_runtime arbitrary repository counter INSERT: succeeded with ceiling 999
supported scheduler grants for one repository: 11
security verdict: FAIL, 1 Important

installer exact inventory probe
included: actors.example.json, server.py, migrations 005 and 006
excluded: uv.lock and factory/tests/run_disposable_exit.py

exact-head product external-write static search
no subprocess/shell/GitHub/external HTTP/TCP listener match under factory/src/adaptive_factory
```

The current shared worktree contains reviewer report rewrites, so `grok_status` correctly calls the earlier verification fingerprint stale after those evidence-file changes and review receipts are not yet complete. More fundamentally, security review is FAIL and the checked-in data review is still bound to old head `01643c6594947535e690c5722f710081c9b9db9f`, so the five exact-head independent-review gate is not satisfied.

## Required disposition

Return I-1 and I-2 to the single route write owner. After the schema/privilege, regression, and README repairs, rerun the mandatory disposable exit and `python3 scripts/grok_verify.py --mode pr` on the new exact tree, then rerun all five independent reviews against that fingerprint. PR delivery, App-owned exact-SHA Trust CI, signed scopes, merge, tagging, publication, and activation remain separately controlled and were not performed.
