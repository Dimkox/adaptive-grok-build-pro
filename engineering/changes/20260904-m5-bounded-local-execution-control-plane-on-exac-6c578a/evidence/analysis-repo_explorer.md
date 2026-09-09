# M5 canonical-lineage semantic port map

## Scope and source identities

Read-only Git-object analysis for route `6c578a9933b3`; no tests, branches, commits, runtime files, or external systems were changed.

- Integration base: `67dc4ddfc8043608aa7a0ef6396c7c0e158d18f4`, tree `399c65e7c65626f3d5236cae1bce009c5d3a9714`, branch `integration/m5-m4-final-20260904`.
- Canonical M5 source endpoint: `3940267ac5754ad07a047894102015d33eb759b1`, tree `4646582a7c5ff6f08ee7e8462687da400459b08d`.
- Merge base: `9727bc30c82bb44a86db0ef5b62e507b5527207a`; the canonical endpoint is **not** a descendant of current M4.
- The ancestry path contains 23 commits. A whole-tree merge or sequential cherry-pick would reintroduce pre-final-M4 source and documentation. Port final M5 semantics onto `67dc4dd`, preserving current M4 as authority.
- Active route metadata still names `78ad2f679d38dc3244e716c586332417e610089c` as its generic routing base; implementation evidence must instead state the user-selected exact integration base `67dc4dd`.

## Canonical commit map

| Commit | Semantic contribution | Port disposition / principal files |
| --- | --- | --- |
| `8fbbcab` | Initial M5 design and plan | Use as design evidence; rewrite into the current formal change package, not the old `20260901-...-37b05f` package. |
| `acb8c36` | Immutable execution contracts | Port final `execution_contracts.py` plus `task-packet`, `execution-invocation`, and `execution-event` schemas and tests. |
| `40f7d72` | Bounded protocol and offline adapters | Port final `protocol.py`, `adapters/{base,codex,grok}.py`, two JSONL fixtures, and tests. |
| `5cbda5b` | Proposal and workspace boundaries | Port final `brokers.py`, `workspace.py`, and their tests. |
| `7311432`, `3171854` | Architecture ownership/authenticated edges | Semantically add M5 nodes, data and edges to current `architecture/{system,rules}.yaml`; regenerate diagrams. |
| `a4c9c32` | Old-head documentation binding | Do not port status/SHA text. |
| `0a3485a`, `355e78d` | Migration 014 execution lifecycle and factual workspace-result bridge | Port final SQL and integrate additions into current `models.py`, `store.py`, `service.py`, and `api.py`; add the workspace-result schema/tests. |
| `8edbbd8`, `f7f6d99` | Successor-branch documentation and merge topology | No code to port independently; do not import old delivery state. |
| `0e5f0ef` | Trusted selection, role constraints, cleanup on start failure | Preserve the final adapter registry/service/store behavior and its regressions. |
| `f9dcb4f` | Six execution-v1 API operations | Add `factory-execution.v1.json` and execution routes without replacing M4's control contract/routes. |
| `c70950d` | Canonical persistence and artifact attestor | Port final migrations 015-016, canonical proposal/result/attestation logic, disjoint DB role, and PostgreSQL tests. |
| `0537fe9` | Fail-closed runtime capability startup | Semantically merge `server.py`, `settings.py`, `admin.py`, and capability tests. |
| `8a7be8a` | Historical package-test rebinding | Do not port; it binds obsolete M4/package evidence. |
| `36ab807`, `27b0ae6` | Contract enrollment and bounded `$ref` comparison | Port contract inventory plus the bounded resolver/comparator semantics into the current architecture implementation; do not overwrite current M4 architecture fixes. |
| `3f56b6a` | Recovery, migration 017, execution-v2 | Port final `recovery.py`, migration 017, `factory-execution.v2.json`, recovery/API/store tests. |
| `3a79015`, `fc170bb` | Historical M4/M5 status refreshes | Do not port current-state claims; recreate factual current docs after implementation. |
| `5073fc0` | Additive v2 route exposure | Retain both six-operation v1 and six-operation v2 fragments; v2 terminal adds the factual result projection. |
| `3940267` | Two-real-restart recovery proof | Reapply the scenario to the current M4 disposable harness; do not replace that harness wholesale. |

## Exact port inventory and conflicts

The 13 existing migrations are safe ancestry anchors: every `001`-`013` SQL blob is byte-identical at `67dc4dd` and `3940267`. Add canonical final migrations only:

- `014_execution_plane.sql`
- `015_execution_canonical_persistence.sql`
- `016_contract_execution_canonical_persistence.sql`
- `017_execution_recovery_topology.sql`

Final-tree additions that are suitable source material are the four SQL files; six contract files (`factory-execution.v1/v2.json` and four execution/workspace schemas); `execution_contracts.py`, `protocol.py`, `brokers.py`, `workspace.py`, `recovery.py`; `adapters/`; two fixture streams; and the nine dedicated test modules for those components. Import from final `3940267`, not intermediate commit snapshots.

Existing files changed only on the canonical side since the merge base, so their patches are low-conflict but still require review: `factory/src/adaptive_factory/{admin,migrations,settings}.py`, `architecture/system.yaml`, `.grok-stack/adaptive_grok/architecture_fitness.py`, generated diagrams, `tests/test_installer.py`, and `tests/test_structure.py`.

A three-way `git merge-tree` reports 34 dual-edited paths and textual conflicts in 27. The critical manual semantic merges are:

- `models.py`: add `ExecutionStage` and `ExecutionGrant`; retain M4's versioned task/run/attempt/event/history models and aliases.
- `api.py`: add execution handlers and 12 versioned routes while retaining all 17 current `factory-control.v1` operations, including run/event history and `/v1/transitions`. Never copy canonical M5's older control API wholesale.
- `service.py` and `store.py`: layer claim/start/stage/proposal/attestation/finalization/recovery methods onto current M4 fencing, transition, accounting, history, retry, and audit logic. These are the highest-risk conflict surfaces.
- `server.py`: preserve current M4 exception/readiness behavior while adding execution feature gating and distinct runtime/attestor dependencies.
- `architecture.py`: manually integrate commits `36ab807`/`27b0ae6`; current M4 and canonical M5 independently changed the comparator. `factory-execution.v2.json` references `../schemas/workspace-result.v1.json`, so bounded declared-inventory `$ref` handling is required.
- `postgres_restart_probe.py`, `run_disposable_exit.py`, `test_api.py`, and `test_postgres_integration.py`: extend current tests; canonical replacements are based on the older M4 seam.
- Root docs, `PROJECT_STATE.json`, `factory/README.md`, `packages/README.md`, `decisions.md`, `mistakes.md`, and the old M4 change package conflict or contain stale checkpoint claims. Re-author current facts; do not resolve by taking the canonical side.
- Keep `factory/contracts/openapi/factory-control.v1.json` exactly from `67dc4dd`. Canonical M5 intentionally treated its own older control file as immutable, but it is not the final M4 contract.
- Do not import either tracked ZIP/sidecar or canonical package-state assertions during the semantic port.

Canonical provider adapters are offline translators only. At `3940267`, Codex `0.152.1` (`b8201824…06f9`) and Grok `1.0.17` (`82595e26…4568`) both remain `execution_eligible=false`; tests may inject an exact trusted eligible profile, but repository source must not add provider invocation, fallback, credentials, or network access.

## Recommended implementation order

1. Port immutable contracts, strict protocol, adapters, brokers, and workspace types with their pure tests.
2. Add migrations 014-017 and extend role validation/admin/settings without modifying 001-013.
3. Manually merge models/store/service/API/server against current M4; preserve legacy packet identity and all existing routes.
4. Add recovery and trusted attestation/finalization, then merge the disposable PostgreSQL and restart scenarios.
5. Enroll contracts and architecture semantics, regenerate diagrams, then write current formal docs. Package rebuilding and full verification belong only after tracked state is frozen.

## Minimal focused verification map

No command below was run by this analysis agent.

```bash
PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_execution_contracts \
  factory.tests.test_protocol \
  factory.tests.test_adapters \
  factory.tests.test_brokers \
  factory.tests.test_workspace -v

PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_migrations \
  factory.tests.test_execution_service \
  factory.tests.test_api \
  factory.tests.test_models \
  factory.tests.test_service \
  factory.tests.test_contracts \
  factory.tests.test_openapi_contract -v

PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_recovery \
  factory.tests.test_runtime_capability_postgres \
  factory.tests.test_server -v

python3 -m unittest \
  tests.test_architecture_model \
  tests.test_architecture_fitness \
  tests.test_structure \
  tests.test_installer -v
```

Then run the existing disposable PostgreSQL suite plus the adapted two-restart probe once on the final database-integrated tree. Preserve current M4 regression coverage; the final exact-head `python3 scripts/grok_verify.py --mode pr` and route-selected reviews remain later delivery gates, not substitutes for the focused RED/GREEN sequence.
