# Release review — round 4

## Verdict and binding

**PASS** for local `release_review` on the exact product head.

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Round-4 fix range: `8435e23458885a48e2d5784f8cd01e84d978c28c..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`
- Exact-head verification fingerprint: `463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4`
- Critical findings: 0
- Important findings: 0
- Moderate findings: 1

The prior capacity-authority, README-parity, and transferable-installer blockers are closed. Source delivery remains inert and local; it does not itself activate a service, migrate a non-disposable database, deploy, merge, publish, or perform an external write.

This PASS is local preflight evidence only. It does not authorize PR delivery, merge, deployment, tagging, publication, migration, or activation, and it cannot replace the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and required signed scopes on the exact PR head.

## Findings

No Critical or Important release finding remains.

### Moderate — M-1: obsolete direct allocation-release UPDATE grant remains

Migration 005 granted `factory_runtime` direct UPDATE of `factory.capacity_allocations.released_at` (`factory/src/adaptive_factory/resources/005_security_accounting_commands.sql:67`). Migration 007 revokes direct counter INSERT/UPDATE and allocation INSERT, but does not revoke that older column grant (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:160-169`). The exact-head security review confirms the grant remains.

The store no longer uses this privilege: legitimate release and reconciliation call the bounded `factory.capacity_release(uuid)` security-definer function. Abuse can mark an allocation released without decrementing its counter, making counter/allocation agreement fail and readiness return `not_ready`; it cannot create additional capacity or exceed the 20/10/1 limits. This is a fail-closed availability/evidence-consistency hardening item, not a release-blocking authorization bypass.

Recommended forward cleanup: revoke direct UPDATE on `capacity_allocations` from `factory_runtime` in migration `008`, add an effective-role denial regression, and retain positive release/reconciliation coverage through `capacity_release`.

## Prior release-finding closure

| Prior finding | Round-4 result | Evidence |
| --- | --- | --- |
| Runtime could INSERT arbitrary repository capacity ceilings | **Closed** | Migration 007 constrains canonical rows to global reader 20, global writer 1, and repository reader 10; revokes direct runtime counter/allocation creation; and exposes fixed-search-path capability functions only (`factory/src/adaptive_factory/resources/007_capacity_authority.sql:1-169`). Store claim/release paths call those functions (`factory/src/adaptive_factory/store.py:418-520`). Fresh effective-role probes reject forged DML, and the supported scheduler rejects reader 11/global reader 21/writer 2. |
| README migration count was stale | **Closed** | Root current state says seven checksum migrations and the tree contains exactly `001` through `007` (`README.md:13`, `factory/src/adaptive_factory/resources/`). Product identity remains `2.0.12` (`README.md:1,7`, `VERSION`). |
| Installer omitted lockfile and exit harness | **Closed** | Managed payload includes `factory/uv.lock`, the exit runner, restart probe, and all factory tests (`scripts/install_into.py:24-41`). Installer tests assert the exact inventory (`tests/test_installer.py:144-200`). The round-4 test reviewer materialized a fresh install and ran that installed copy's own exit runner: all 42 tests plus actual PostgreSQL restart/reconciliation passed. |
| Rollout/rollback version drift | **Closed** | Current schema is 007; release applies through exact schema 007 and forward recovery consistently uses migration `008+` (`release.md:3-7`, `rollback.md:3-5`, `factory/README.md:18,30-34`, `architecture.md:29-31`). |
| UDS composition, readiness, metrics and runbook | **Closed** | `adaptive-factory-server` composes the service and pre-binds only an owned safe mode-0660 `AF_UNIX` socket; no TCP option exists. Readiness verifies effective runtime role, schema 7, canonical capacity rows and allocation/counter agreement; authenticated metrics expose the three bounded redacted families. Release/rollback name owner evidence, backup restore, role/schema/readiness/capacity checks, synthetic accounting flow, actual restart, two-pass reconciliation, kill and forward recovery. |
| Exact verifier omitted P0 exit | **Closed** | PR/release verification mandates the disposable exit runner. The fresh exact-head receipt passed factory unit plus 42 API/PostgreSQL/effective-role tests and actual restart/reconciliation. |

## README, graph, migration, packaging, and rollout assessment

- README identity and current state match the tree: product `2.0.12`, accepted M3 base, seven factory migrations, database-owned capacity, UDS server, readiness/metrics, and pending external gates.
- The K17 stack graph remains complete with all 136 pairwise `---` edges including Factory. `test_readme_stack_graph_is_complete` and `test_version_identity_matches_readme` passed (`README.md:91-263`).
- Migrations are contiguous `001..007`, immutable/checksum-planned under the factory advisory lock, and forward-only after durable intake. Migration 007 uses canonical constraints plus bounded `SECURITY DEFINER` functions with fixed `pg_catalog,factory` search paths and no PUBLIC execute.
- Installer materialization remains read-only for existing targets and atomic/no-replace for a new target. The payload contains runtime source, OpenAPI, actor template, all SQL migrations, exact dependency lock, and the complete disposable exit/restart test harness; it excludes credentials, sockets, database contents, and runtime state.
- The installed-copy evidence is behavioral, not inventory-only: the package built from the installed path and passed 42 tests plus an actual PostgreSQL restart, one repair, replay no-op, higher fence, and stale-holder rejection.
- Rollout starts killed, verifies backup by restore to a distinct comparison database, migrates with the separate migrator credential through schema 007, checks mode-0660 UDS/readiness/metrics/capacity agreement, runs the synthetic intake/claim/accounting/release/restart/two-pass-reconcile flow, then explicitly clears kill. Any mismatch remains no-go.
- Rollback is forward recovery: global kill, stop intake/claims/socket process, preserve rows/audit/logs/evidence, compare a restored backup separately, and use reviewed migration `008+`; never down-migrate or delete audit after durable intake.

## No-external-write guarantee

Static inspection of exact-head `factory/src/adaptive_factory` found no provider execution, subprocess/shell, repository/Git/GitHub client, connector, systemd, deployment, TCP client/listener, production mutation, or Trust CI authority/write path. The server pre-binds only `AF_UNIX`; the CLI uses HTTP-over-UDS. The sample PostgreSQL port is loopback-only, and source delivery starts nothing.

The verifier's Docker/PostgreSQL activity is explicitly randomized disposable local test state, bounded by the exit runner and removed afterward. No shared, production, external, or Trust CI database is read or mutated. This reviewer performed no external write, merge, deployment, publication, tag, production migration, or Trust CI mutation.

## Verification and independent-review evidence

```text
git rev-parse HEAD
9fd2a56c57f834ad39c03a2f748bdbaefc79c91c

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..9fd2a56c57f834ad39c03a2f748bdbaefc79c91c
PASS (no output)

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
PASS — 30/30

python3 -m unittest tests.test_installer tests.test_structure -v
PASS — 32/32

exact-head .grok-stack/runtime/receipts/b7f288f1e81e/verification.json
PASS — fingerprint 463b893d2ee9539ca8f2d0b7bb1c46b797b596ad322b297ccc9b4bb90d5fd0d4;
485 root tests, 21 factory unit tests, 42 disposable API/PostgreSQL/effective-role tests,
actual PostgreSQL restart/reconciliation, architecture/governance/contracts/SQL safety,
Ruff, Bandit, secret scan, coverage, diff check, and source stability passed.

round-4 code review: PASS — no Critical/Important findings
round-4 test review: PASS — no Critical/Important findings; installed-copy exit passed
round-4 security review: PASS — no Critical/Important findings; one Moderate fail-closed grant cleanup

installed-copy evidence from round-4 test review
materialize-new: PASS, verified payload includes lockfile and complete exit harness
installed factory/tests/run_disposable_exit.py: PASS — 42/42 plus actual restart/reconciliation

exact-head product external-write static search
no subprocess/shell/GitHub/external HTTP/TCP listener match under factory/src/adaptive_factory
```

The shared worktree currently contains reviewer-report rewrites, so `grok_status` correctly considers the earlier product fingerprint stale after evidence changes and review receipts are not yet complete. Record this passing report only after the evidence set is frozen and bound through the repository review command. Any subsequent repository change invalidates the receipt and requires affected verification/review again.

## Release decision

**PASS** for the route-selected local release review of exact head `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c`. No Critical or Important release-readiness issue remains. Final route closure still requires all required exact-head review receipts with zero evidence gaps; PR delivery and actual release remain separately authorized and externally gated.
