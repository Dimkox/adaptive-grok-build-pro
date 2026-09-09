# M4 continuation acceptance and task audit

**Route/change:** `b7f288f1e81e` / `20260831-implement-a-new-m4-application-feature-on-exact-b7f288`
**Audited HEAD:** `9727bc30c82bb44a86db0ef5b62e507b5527207a`
**Accepted implementation base:** `67714a1f1b87effcfabe55d5ca2770d0a68d17c1`

## Outcome

There is no identified unfinished M4 application, migration, contract, API, or
PostgreSQL-test vertical.  The source evidence supports the substantive
decomposed requirements labelled RQ-001 through RQ-013 below. RQ-014 remains open: all
local verification and review receipts bind `571cad7` / fingerprint
`2f9b3ec2...`, not the current `9727bc3` tree.  The current `grok_status`
also reports every required evidence kind stale after repository, spec,
architecture, and governance binding changes.

`571cad7..9727bc3` changes release-packaging hardening and the resulting
tracked ZIP/sidecar only (`scripts/package_stack.py`,
`tests/test_manifest_package.py`, `decisions.md`, `mistakes.md`, and the two
package artifacts).  It has no diff under `factory/`, factory migrations,
factory tests, factory contract, or this M4 package.  That makes the gap an
exact-tree assurance/delivery gap, rather than evidence of a missing M4
functional slice; it does not make the old receipts reusable.

## Requirement acceptance mapping

| Requirement ID | Current concrete evidence | Status at `9727bc3` |
| --- | --- | --- |
| RQ-001 | `factory/src/adaptive_factory/contracts.py`; `test_contracts.py` intake, complete identity, authority and stale-M0 cases; PostgreSQL intake/authority cases at `test_postgres_integration.py:231-352`. | Implemented; current receipt absent. |
| RQ-002 | Transactional intake/store implementation; exact replay/supersession cases at `test_postgres_integration.py:231-273`; immutable intent and full frozen identity contract cases. | Implemented; current receipt absent. |
| RQ-003 | Contiguous `001`–`013` SQL resources, `migrations.py`, `test_migrations.py`, and effective-role/bootstrap checks at PostgreSQL cases `2510-2646`. | Implemented; current receipt absent. |
| RQ-004 | `FOR UPDATE SKIP LOCKED` claim/fence path in `store.py` and `002_runs_leases_capacity.sql`; two-worker/late-fence integration case at `:707`. | Implemented; current receipt absent. |
| RQ-005 | Capability-shaped capacity SQL in `007_capacity_authority.sql`; reader/writer capacity integration case at `:766` and cancellation/supersession race coverage at `:411-453`. | Implemented; current receipt absent. |
| RQ-006 | Closed state policy and accepted limits in `state.py`/`test_state.py:49-86`; release/reconciliation/persistence cases at PostgreSQL `:952-1076`, including schema-013 backfill/exhaustion. | Implemented; current receipt absent. |
| RQ-007 | Limits/closed accounting in contracts, migrations `001`, `003`, `004`, `005`, `013`; bounded reservation/settlement, completion, event/repair/deadline and prior-attempt recovery cases at PostgreSQL `:456-548`, `:811`, `:1392-1522`. | Implemented; current receipt absent. |
| RQ-008 | Kill/audit schema in `003`, audit chain implementation and role isolation tests at PostgreSQL `:2020`, `:2647-2734`; runtime audit mutation denial is directly exercised. | Implemented; current receipt absent. |
| RQ-009 | Bounded reconciliation schema/service plus orphan/expiry, repository-kill/page-timeout, lock-order and restart cases at PostgreSQL `:745`, `:2020-2122`; `postgres_restart_probe.py` proves repair then replay no-op. | Implemented; current receipt absent. |
| RQ-010 | `api.py`, `server.py`, `cli.py`, checked-in OpenAPI; API bounds/auth/no-execution tests and real UDS/no-follow/mode-0660 tests in `test_api.py` and `test_server.py`. | Implemented; current receipt absent. |
| RQ-011 | Explicit negative API endpoint test (`test_api.py:102`), UDS-only server implementation/tests, architecture separation test, and package/factory README boundaries; no Factory-to-Trust-CI/external execution edge is declared. | Implemented; current receipt absent. |
| RQ-012 | `run_disposable_exit.py` creates/removes an exact PostgreSQL 17 container, runs the full factory suite and actual restart probe.  The prior exact verifier recorded 70/70 plus restart/reconcile; that result is historical only until repeated on the current tree. | Harness implemented; current execution receipt absent. |
| RQ-013 | `architecture.md`, `test-plan.md`, `release.md`, `rollback.md`, root/factory README, architecture/structure/installer/package tests, and current 2.0.13 ZIP/sidecar. | Documentation/source present; current verification/release review absent. |
| RQ-014 | `requirements.md` and `tasks.md` intentionally leave this open.  All six local receipt JSON files and the five reports under `evidence/final-runtime-571cad7/` bind `571cad7`, not `9727bc3`; `grok_status` lists every required evidence kind stale. | **Open / no-go.** |

## Task checklist mapping

| `tasks.md` item | Evidence/status |
| --- | --- |
| Bind route/package to accepted M3 base | Active route, brief, change state and receipt metadata name base `67714a1...`; done. |
| Six-agent analysis and scope/design approval | Six original analysis reports exist; `state.json` records scoped/approved on 2026-08-31; done. |
| Disposable-only migration ruling/calendar | `brief.md`, `release.md`, `rollback.md`, and `test-plan.md` restrict mutation to fresh disposable PostgreSQL; done. |
| TDD contracts/state/migrations/intake | `implementation-ledger.md` records RED/GREEN cycles; current contract/state/migration tests and source exist; done. |
| TDD leases/capacity; retry/budgets/kills/audit/reconcile | Ledger plus the named PostgreSQL integration cases above; done. |
| TDD UDS API/CLI/OpenAPI | API/server/CLI/OpenAPI and corresponding tests; done. |
| Architecture/tooling/docs; PostgreSQL/API/effective-role/restart exit | Current architecture/docs/package and exit runner exist; historical run is not current evidence; implementation done. |
| Reproduce Bandit/readiness failures; TDD explicit fence/PID1 repairs | Current explicit fence handling and final-PID1 readiness helper/tests exist; ledger preserves reproduction/repair history; done. |
| Run final exact-head verifier | Unchecked and required on the frozen final evidence tree. |
| Hand final fingerprint to five reviewers | Unchecked and required after that verifier. |

## Contradictions and unresolved requirements

1. **Typed acceptance taxonomy ruling.** `change-spec.yaml` remains the typed
   authority with canonical `AC-001` through `AC-004`. The Markdown checklist
   is explicitly non-authoritative and uses `RQ-001` through `RQ-014`; its
   crosswalk provides traceability without creating or overriding typed IDs.
2. **Operational status differs.** The active route is `verifying`, whereas
   the change package `state.json` remains `reviewing`.  Per repository
   source-of-truth order, the live route governs the next operational phase;
   reconcile package state only in the controlled evidence update.
3. **All current receipts are stale.** They bind `571cad7` and fingerprint
   `2f9b3ec2...`; the current clean commit is `9727bc3`, and this audit/report
   is itself an untracked evidence write.  Receipt/report writes change the
   fingerprint, so a final evidence commit/freeze must precede the final
   verifier and reviews.

## Exact minimal next phase

1. The single route-selected write owner resolves the typed-criterion
   taxonomy and live-route/package-state discrepancy in one bounded
   documentation/evidence change; no factory application change is indicated.
2. Freeze/commit the resulting evidence tree, then run exactly one
   `python3 scripts/grok_verify.py --mode pr` against that exact HEAD.
3. Dispatch the five route-selected independent reviewers (code, test,
   security, data, release) against the verifier fingerprint; record their
   reports and fingerprint-bound local receipts.  If report/receipt writes
   alter the tree, perform the required final binding pass rather than
   reusing a pre-write receipt.
4. Only after zero local evidence gaps may a separately authorized PR action
   occur; delivery still requires the App-owned exact-PR-head Trust CI check
   and required human-signed scopes.  This audit authorizes none of those
   external actions.
