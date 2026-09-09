# M6 canonical semantic-port map

## Exact source identities

- Target M5 base: `85cd4343143915ce9342634e7fe81886b6394871`, tree `779e0b99a5e489a2c91e866662cc1f31ae73b4c3`, branch `integration/m6-m5-final-20260904`.
- Canonical M6 endpoint: `2d2360cd6f2a19ad3328d468073a52927691b112`, tree `5ee89e86b7e8f03ff78c644713e449b0fb9064d8`.
- Git merge-base: `460a8a01a6394cac710b4e3f9eea3d94d4beef89`; neither endpoint contains the other. Canonical M6 was ultimately aligned to historical M5 `141e51e75b2bb337fa3bb1544639c6c46c287309`, not the target M5 tree. Therefore port the final M6 delta semantically; do not merge or cherry-pick the lineage.
- Target M5 already owns contiguous migrations `001`-`017`. Canonical `014_semantic_validation_bridge.sql` must become additive `018_semantic_validation_bridge.sql`; migrations `001`-`017` remain unchanged.

## M6 commit map

| Commit(s) | Final semantic contribution | Disposition |
| --- | --- | --- |
| `e5877f9` | Existing M6 design/plan/package | Design input only; use the active formal package, not the historical route/state. |
| `08004b6` | Closed semantic subject/finding/coverage/verdict/repair contracts and pure tests | Port from final endpoint. |
| `29c19fc` | Deterministic adjudication, including duplicate/correlation/contradiction and unsupported-pass handling | Port from final endpoint. |
| `bca8ea3` | Pure repair policy: cycles 1-3; fourth cycle and policy violations escalate | Port from final endpoint. |
| `46c3a0d`, `5c5c371` | Historical roadmap and upstream binding | Do not port checkpoint claims. |
| `c398ea0` | Merge of historical M5 `141e51e` | Do not port; target M5 `85cd434` is authoritative. |
| `cf58788` | Design reconciliation after that merge | Retain semantic decisions only. |
| `3def83e` | Exact M5 result-to-subject bridge and two additional closed schemas | Port final bridge semantics. |
| `a8ca0f3` | Durable semantic subjects, capabilities and publication/read path | Rebase SQL as migration 018 and manually integrate runtime surfaces. |
| `f3b2c0d` | Persisted assignments/evidence/verdicts and six additive semantic API operations | Manually integrate against current M5 API/OpenAPI/store. |
| `c39b9f0` | Durable bounded repair-child lifecycle and M5 broker handoff | Port final lifecycle semantics. |
| `81cc3c4`, `87897ff`, `534b667` | Quarantine, exact-lineage binding, source/claim bypass closures | Required security fixes; port as one final-state unit. |
| `fc019d4`, `2d2360c` | Preserve repair digest and claim lookup indexes | Required final migration fixes; use only the final SQL blob before renumbering. |

## Add-only final source inventory

Copy final content from `2d2360c`, except for the migration filename/version adjustment:

- Contracts: `factory/contracts/jsonschema/{repair-directive,semantic-coverage,semantic-execution-binding,semantic-finding,semantic-subject,semantic-validation-inputs,semantic-verdict}.v1.schema.json`.
- Pure/domain modules: `factory/src/adaptive_factory/semantic_contracts.py`, `semantic_adjudication.py`, `semantic_bridge.py`, and `semantic_repair.py`.
- Database: canonical `factory/src/adaptive_factory/resources/014_semantic_validation_bridge.sql` as target `018_semantic_validation_bridge.sql`, preserving the final `2d2360c` integrity/index fixes.
- Dedicated tests: `factory/tests/test_semantic_{contracts,adjudication,bridge,repair,persistence,service_api,store_runtime,repair_lifecycle}.py`.

The old M6 design files and `engineering/changes/20260901-m6-provider-independent-semantic-validation-prov-82aac8/` are historical evidence, not port payload. Do not import canonical root state, package artifacts, or M5 merge content.

## M5 overlaps requiring semantic integration

The M6 delta overlaps the target in `factory/contracts/openapi/factory-control.v1.json`; `factory/src/adaptive_factory/{admin,api,server,service,settings,store}.py`; `factory/tests/{postgres_restart_probe,run_disposable_exit,test_migrations,test_postgres_integration,test_server}.py`; and architecture/root documentation files. Text can often auto-merge, but these are semantic conflicts:

- OpenAPI/API: target M5 has a 17-operation control contract plus separate six-operation execution v1 and v2 contracts. Add only the six semantic operations (`publishSemanticSubject`, `getSemanticSubject`, `createSemanticAssignment`, `submitSemanticEvidence`, `adjudicateSemanticSubject`, `getSemanticVerdict`) to the current control surface; never replace it with canonical M6's historical 26-operation monolith.
- Service/store/server/settings/admin: layer the three disjoint semantic capabilities and scopes onto current M5. Preserve all current control/execution fencing, exact-result attestation, recovery, API middleware, readiness and route behavior. `task:execute` and writer/runtime roles must not gain semantic validation or adjudication authority.
- Persistence: extend current role validation and disposable harness for coordinator/validator/adjudicator NOLOGIN/NOINHERIT roles, append-only canonical bodies, exact replay/divergent-replay rejection, fixed `search_path`, revoked `PUBLIC`, and no direct table DML. Keep current M5 migrations and checksums immutable.
- Repair intake: retain the final source-digest, exact parent task/run/fence/packet/manifest/result/head, original-writer, fresh-context and claim-index checks from commits `81cc3c4..2d2360c`; cycles 1-3 may create at most one child, while cycle four, recurrence or stale/policy-invalid input appends `needs_human` and does not call the broker.
- Architecture/docs: add semantic ownership, contracts and authenticated edges to the current M5 model, regenerate diagrams, and write present-tense facts in the active package. Do not carry provisional SHAs, route `82aac86a3bf9`, old migration number 014, or obsolete acceptance claims.

## Minimal critical tests

No tests were run by this read-only analysis.

```bash
PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_semantic_contracts \
  factory.tests.test_semantic_adjudication \
  factory.tests.test_semantic_bridge \
  factory.tests.test_semantic_repair -v

PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_semantic_persistence \
  factory.tests.test_semantic_store_runtime \
  factory.tests.test_semantic_service_api \
  factory.tests.test_semantic_repair_lifecycle \
  factory.tests.test_migrations \
  factory.tests.test_server -v

PYTHONPATH=factory/src python3 -m unittest \
  factory.tests.test_execution_service \
  factory.tests.test_recovery \
  factory.tests.test_api \
  factory.tests.test_service -v
```

Then run the existing disposable PostgreSQL integration plus restart probe once against the final migration-018 tree. The critical assertions are role separation/direct-DML denial, canonical replay versus divergent replay, exact M5-to-subject binding, deterministic contradiction precedence, no duplicate verdict/child after restart, cycles 1-3 only, fourth-cycle `needs_human`, and preservation of all M5 control/execution regressions.
