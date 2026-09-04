# Repository analysis — M4 control plane

## Basis inspected

- Worktree branch `milestone/m4-durable-control-plane-accepted-m3` is at `67714a1f1b87effcfabe55d5ca2770d0a68d17c1` (`Merge pull request #11`), whose M3 parent is `1e73ff9` and accepted M2 parent is `022411b`.
- The package objective names that SHA, but copied `route.json` still binds `base_commit` and `base_fingerprint` to `1c06299894279a88b881defa3f19b004fa742223`. This is a material exact-base/fingerprint inconsistency. Regenerate/transition route and package binding through workflow before implementation or receipts; do not hand-edit the route.
- The prior M4 package was read only at `/home/pall/grok-projects/adaptive-grok-build-pro/engineering/changes/20260830-implement-m4-durable-factory-task-control-plane-e50471`. Its detailed design remains useful; its statements that M2/M3 are absent and approvals remain open are historical/stale on this checkout.

## Exact M4 insertion map

| Surface | Current accepted-M3 pattern | M4 insertion |
| --- | --- | --- |
| Product boundary | No `factory/` exists; `trust-ci/` is separate Python/PostgreSQL service. | Add top-level `factory/`: isolated `pyproject.toml`, `src/adaptive_factory/{models,contracts,state,migrations,store,service,api,cli,settings}.py`, packaged SQL, OpenAPI, compose/example env, and factory-local tests. Do not import/extend `adaptive_trust_ci`. |
| Frozen input | `schemas/governance-handoff-v1.schema.json` and `GovernanceHandoffV1` in `.grok-stack/adaptive_grok/governance.py` define a frozen six-field handoff; producer rejects dirty/non-exact/forged inputs. | Factory-owned closed decoders for M2 architecture and M3 governance handoffs; require matching M2/M3 architecture digest/base/head and accepted M4 base, retaining immutable input packet/digest. Never reinterpret M3 producer contract. |
| Architecture | `architecture/system.yaml` owns nodes/contracts/paths/edges; `architecture/rules.yaml` owns risk/network/migration/separation fitness; generated Mermaid is checked. | Add Factory API/service/PostgreSQL/local client nodes, `factory/**` ownership, Factory OpenAPI, Factory data classification and local/PostgreSQL edges. Regenerate diagrams. Declare no Factory-to-Trust-CI, provider, Git/GitHub, deploy edge. |
| Drift/fitness | `architecture.py:validate_repository_drift` rejects unowned source-like files/undeclared contracts; `architecture_fitness.py` evaluates declared boundaries. | Factory Python must be architecture-owned. Add Factory-specific immutable migration policy; `FIT-TRUST-CI-SQL-HISTORY` covers only `trust-ci/sql`. Declare Factory OpenAPI consistently in its chosen inventory location. |
| Durable migration precedent | `trust-ci/.../migrations.py` has package discovery, contiguous versions, checksum drift checks, advisory lock and registry; its migration/integration tests characterize it. | Reuse pattern only: independent code/lock/registry `factory.schema_migrations`, `factory.*` tables/roles/search path. No Trust CI registry/table/data access. Forward-only checksum-locked SQL and disposable Factory PostgreSQL rehearsal. |
| API/auth precedent | `trust-ci/.../api.py` is thin FastAPI with constant-time bearer auth/typed store; dependencies isolated in `trust-ci/pyproject.toml`. | Unix-socket/local-only Factory API: health, submit/show/list/cancel plus scoped claim/heartbeat/proposal/kill/reconcile. Bound/redact requests/responses. No webhook/GitHub App/signing/human approval/provider/shell/systemd/deploy/network side effects. |
| Receipts and docs | `verification.py` runs architecture before governance; `receipts.py` binds evidence to route/base/head. M3 regression tests prove exact binding. Installer/structure ownership lives in `managed.json`, `install_into.py`, and related tests. | Bind Factory contract/architecture evidence only at exact final M4 head. Preserve spec -> architecture -> governance ordering. Decide explicitly whether Factory belongs in transferable installer inventory; update installer/structure tests, README, roadmap/package, diagrams and final receipts accordingly. |

## State and test scope

Carry forward the approved state/store scope: closed `TaskIntakeV1`; immutable accepted intent/idempotency digest; normal states `inbox` through `ready_for_human`; exceptional `retry/needs_human/dead/cancelled/superseded`; terminal M4 boundary at `ready_for_human`; `SKIP LOCKED` claims, monotonic fences, 20 global reader/10 repository reader/1 writer capacity; initial plus at most two infrastructure retries; four-hour/$25/token/output ceilings; append-only audit and bounded restart-safe reconciliation. PR/merge/deploy states must be rejected future values.

Add `factory/tests/test_contracts.py`, `test_state.py`, `test_migrations.py`, `test_service.py`, `test_api.py`, `test_postgres_integration.py`, and `postgres_restart_probe.py`. Real disposable PostgreSQL must prove duplicate/superseding intake, claim race/fence expiry-reclaim, 20/10/1 races, retry-to-dead, budgets/missing accounting, kill retention, audit privileges, restart/reconciliation. Amend/run `tests/test_architecture_model.py`, `test_architecture_fitness.py`, `test_change_receipts.py`, `test_verification_doctor.py`, `test_installer.py`, and `test_structure.py`.

## Separation and conclusion

This isolated branch can satisfy `FIT-TRUST-CI-SEPARATION` because it leaves `trust-ci/**` unchanged and creates a top-level Factory boundary. The rule alone is insufficient: add positive controls for separate package/schema/registry/roles, no Trust-CI imports/queries/secrets/keys/approvals, and no production-trust edge. The current `change-spec.yaml` is a skeleton (empty criteria, invariants, contracts and required scopes), so it cannot evidence approved M4 acceptance until completed under the refreshed route.

There is a clean insertion point at accepted M3 `67714a1`; no Factory implementation exists. The blocker is route identity: objective/head are correct but route base/fingerprint are stale at `1c0629`. Resolve that durable binding before product edits, then the table identifies the bounded implementation/test scope.
