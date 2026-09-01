# Release review — round 5

## Verdict and binding

**PASS** for local `release_review` on the exact product head.

- Route: `b7f288f1e81e`
- Base SHA: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`
- Reviewed product HEAD: `f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Full reviewed range: `67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Round-5 delta: `9fd2a56c57f834ad39c03a2f748bdbaefc79c91c..f82134de35e531a8b3bbf235ad480254ba40f1fe`
- Exact-head verification fingerprint: `e4ac983f20ea22120e98b5eb6597fa6d47486225000a29caf1ab45cadc726b6a`
- Critical findings: 0
- Important findings: 0
- Moderate findings: 0

No release-blocking finding remains. Migration 008 removes the last obsolete direct runtime allocation-update authority, and the exact tree is internally consistent across README, migrations, installer payload, installed-copy verification, rollout/rollback guidance, UDS/readiness/metrics, and the no-external-write boundary.

This PASS is local preflight evidence only. It does not authorize PR delivery, merge, migration, deployment, tagging, publication, or activation, and it cannot replace the App-owned `adaptive-trust-ci/verified@<policy-sha12>` check and required signed scopes on the exact PR head.

## Findings

No Critical, Important, or Moderate release-readiness findings.

Non-blocking test hardening remains useful: a full authenticated HTTP-over-UDS process round trip, barrier-based simultaneous last-slot capacity races, and explicit anonymous-volume removal in the disposable exit runner. Existing database locks, exact threshold tests, UDS construction tests, and bounded randomized cleanup make these Minor observations rather than release blockers.

## Prior release-finding closure

| Prior finding | Round-5 result | Evidence |
| --- | --- | --- |
| Runtime allocation `released_at` UPDATE remained | **Closed** | Migration 008 revokes UPDATE on `factory.capacity_allocations` from `factory_runtime` (`factory/src/adaptive_factory/resources/008_allocation_release_authority.sql:1`). Effective-role tests deny both hiding and restoring allocations (`factory/tests/test_postgres_integration.py:637-658`), while ordinary release/reconciliation through `capacity_release` still passes. |
| Runtime could forge capacity policy/counters | **Closed** | Migration 007 keeps canonical 20/10/1 constraints, revokes direct counter/allocation creation, and exposes fixed-search-path capacity functions only. Migration 008 completes the least-privilege boundary. Grant validation requires a live allocation, readiness checks exact counter/allocation agreement, and reader 11/global reader 21/writer 2 are rejected. |
| README/schema parity | **Closed** | Root current state says eight checksum migrations and the exact tree contains contiguous `001..008` (`README.md:13`, `factory/src/adaptive_factory/resources/`). Product identity remains `2.0.12` (`README.md:1,7`, `VERSION`). |
| Transferable installer completeness | **Closed** | Managed payload includes `factory/uv.lock`, migration 008, the exit runner, restart probe, and every factory test (`scripts/install_into.py:24-41`, `tests/test_installer.py:155-191`). A fresh materialized copy built from its installed path and passed all 43 tests plus actual PostgreSQL restart/reconciliation. |
| Rollout/rollback numbering | **Closed** | Current schema is 008; rollout applies through exact schema 008 and every recovery document names forward migration `009+` (`release.md:3-7`, `rollback.md:3-5`, `factory/README.md:18,30-34`, `architecture.md:29-31`). |
| UDS/readiness/metrics/runbook | **Closed** | The supported server composes the store/service/authenticator and pre-binds only an owned safe mode-0660 `AF_UNIX` socket. Readiness checks effective runtime role, schema 8, canonical capacity and allocation/counter agreement; authenticated metrics expose the three bounded redacted families. Rollout/rollback specify ownership, backup restore, kill, schema/role/capacity checks, synthetic accounting flow, actual restart, two-pass reconcile and forward recovery. |
| Mandatory P0 verification | **Closed** | PR/release verification runs the disposable exit harness. The exact-head receipt passed 43 API/PostgreSQL/effective-role tests plus actual restart, reconciliation replay and stale-fence rejection. |

## README, graph, migration, packaging, and recovery assessment

- README current state matches the exact source tree: product `2.0.12`, accepted M3 base, eight migrations, effective least-privilege roles, database-owned capacity/accounting, UDS-only service, readiness/metrics, and pending external gates.
- The K17 inventory graph remains complete with all 136 pairwise `---` edges including Factory. `test_readme_stack_graph_is_complete` and `test_version_identity_matches_readme` passed (`README.md:91-263`).
- Migrations are contiguous `001..008`, packaged/checksum-bound under the factory advisory lock, and forward-only after durable intake. Migration 008 is a narrow privilege revocation and is included by installer inventory and migration tests.
- Installer behavior remains read-only for an existing target and atomic/no-replace for a new target. Its payload contains runtime source, OpenAPI, actor template, all eight SQL migrations, exact dependency lock, and complete disposable exit/restart tests; it excludes credentials, sockets, database contents, and runtime state.
- Installed-copy evidence is behavioral: a newly materialized target built its own package and ran its own exit runner, passing 43 tests and an actual PostgreSQL restart, repair `1`, replay repair `0`, higher fence, and stale-holder rejection.
- Rollout starts killed, verifies backup through restore to a distinct comparison database, migrates with the separate migrator credential through schema 008, checks mode-0660 UDS/readiness/metrics/capacity agreement, runs synthetic intake/claim/reserve/observe/release/restart/two-pass-reconcile, and clears kill only after recorded go evidence.
- Rollback is forward recovery: enable global kill, stop intake/claims/socket process, preserve rows/audit/logs/evidence, compare a separately restored backup, and use reviewed migration `009+`; never down-migrate or delete audit after durable intake.

## No-external-write guarantee

Static inspection of exact-head `factory/src/adaptive_factory` found no provider execution, subprocess/shell, repository/Git/GitHub client, connector, systemd, deployment, TCP client/listener, production mutation, or Trust CI authority/write path. The server uses only `AF_UNIX`; the CLI uses HTTP-over-UDS. The sample PostgreSQL port is loopback-only, and source delivery starts nothing.

The verifier's Docker/PostgreSQL mutations are bounded to randomized disposable local test state and cleaned by the exit runner. No shared, production, external, or Trust CI database is read or mutated. This reviewer performed no external write, push, merge, deployment, publication, tag, production migration, or Trust CI mutation.

## Commands and evidence

```text
git rev-parse HEAD
f82134de35e531a8b3bbf235ad480254ba40f1fe

git diff --check 67714a1f1b87effcfabe55d5ca2770d0a68d17c1..f82134de35e531a8b3bbf235ad480254ba40f1fe
PASS (no output)

uv run --project factory python -m unittest -v \
  factory.tests.test_contracts factory.tests.test_service factory.tests.test_api \
  factory.tests.test_server factory.tests.test_migrations factory.tests.test_state
PASS — 30/30

python3 -m unittest tests.test_installer tests.test_structure -v
PASS — 32/32

exact-head .grok-stack/runtime/receipts/b7f288f1e81e/verification.json
PASS — fingerprint e4ac983f20ea22120e98b5eb6597fa6d47486225000a29caf1ab45cadc726b6a;
485 root tests, 21 factory unit tests, 43 disposable API/PostgreSQL/effective-role tests,
actual PostgreSQL restart/reconciliation, architecture/governance/contracts/SQL safety,
Ruff, Bandit, secret scan, coverage, diff check, and source stability passed.

round-5 code review: PASS — no Critical/Important findings
round-5 test review: PASS — no Critical/Important findings; source and installed-copy exits passed
round-5 security review: PASS — 0 Critical, 0 Important, 0 Moderate

installed-copy evidence from round-5 test review
materialize-new: PASS, including migration 008, uv.lock and complete exit harness
installed factory/tests/run_disposable_exit.py: PASS — 43/43 plus actual restart/reconciliation

exact-head product external-write static search
no subprocess/shell/GitHub/external HTTP/TCP listener match under factory/src/adaptive_factory
```

The shared worktree currently contains reviewer-report rewrites, so `grok_status` correctly treats the earlier product fingerprint as stale after evidence changes and review receipts are not yet complete. Record this passing report only after the evidence set is frozen and bound through the repository review command. Any subsequent repository change invalidates the receipt and requires affected verification/review again.

## Release decision

**PASS** for the route-selected local release review of exact head `f82134de35e531a8b3bbf235ad480254ba40f1fe`. No Critical, Important, or Moderate release-readiness issue remains. Final route closure still requires all required exact-head review receipts with zero evidence gaps; PR delivery and actual release remain separately authorized and externally gated.
